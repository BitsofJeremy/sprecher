# Sprecher Debugging TODO

## Status: TTS Sync Endpoint Broken

**Goal:** Get Qwen TTS working with Pixel (primary) and fix Kokoro TTS (secondary)

---

## Findings from Mac-side Testing (2026-05-06)

### Working
- `GET /api/health` → `{"status":"ok","engines":["kokoro","qwen","whisper"]}` ✅
- `GET /api/tts/voices` → 53 Kokoro voices returned ✅
- Auth correctly validates Bearer token ✅

### Broken
- `POST /api/tts/sync` → **500 Internal Server Error** for ALL valid Kokoro voices

---

## Root Cause Hypothesis

The error occurs in `core/tts/kokoro_engine.py` in `_ensure_model()` method at line 163-169:

```python
def _ensure_model(self) -> str:
    KokoroClass = _get_kokoro()
    model_path = self.model_dir / "kokoro-v1.0.onnx"
    if not model_path.exists():
        from kokoro_onnx.utils import download_model  # <-- PROBLEM
        download_model(str(self.model_dir))
```

**Problem:** `kokoro_onnx.utils` module does not exist or `download_model` function not found.

When TTS sync is called, it triggers `get_kokoro_engine()` which calls `_get_kokoro_instance()` which calls `_ensure_model()` which tries to import from `kokoro_onnx.utils`. This raises `ModuleNotFoundError`.

---

## Server-side Investigation Steps

### 1. Check kokoro-onnx Installation

```bash
# Check version and what's available
pip show kokoro-onnx

# Test if Kokoro imports at all
python -c "from kokoro_onnx import Kokoro; print('OK')"

# Check if utils submodule exists
python -c "from kokoro_onnx import utils; print(dir(utils))"
```

### 2. Check Model Files

```bash
ls -la ~/.claude/kokoro-models/
# If files exist, _ensure_model should not try to download
```

### 3. Check Application Logs

```bash
# If running via systemd
journalctl -u sprecher-web --no-pager -n 100

# If running directly
cd ~/sprecher
source .venv/bin/activate
python -c "
import asyncio
from core.tts.kokoro_engine import get_kokoro_engine
async def test():
    engine = get_kokoro_engine()
    result = await engine.generate('Hello', 'bf_emma')
    print(f'Generated {len(result[0])} samples')
asyncio.run(test())
"
```

### 4. Try Direct Kokoro Test

```bash
python -c "
from kokoro_onnx import Kokoro
import numpy as np

# Check available
print('Kokoro class:', Kokoro)

# Model path check
from pathlib import Path
model_dir = Path('~/.claude/kokoro-models').expanduser()
model_path = model_dir / 'kokoro-v1.0.onnx'
voices_path = model_dir / 'voices.bin'
print(f'Model exists: {model_path.exists()}')
print(f'Voices exists: {voices_path.exists()}')
"
```

---

## The Fix (once root cause confirmed)

The `_ensure_model` function needs to be fixed to handle the case where:
1. Models already exist → don't try to download
2. `kokoro_onnx.utils` doesn't exist → remove download dependency

**Likely fix:** Remove the `download_model` call entirely. If model doesn't exist, raise a clear error pointing to manual download instructions.

```python
def _ensure_model(self) -> str:
    """Ensure model is available, return model path."""
    model_path = self.model_dir / "kokoro-v1.0.onnx"
    voices_path = self.model_dir / "voices.bin"

    if not model_path.exists() or not voices_path.exists():
        raise FileNotFoundError(
            f"Kokoro model not found at {self.model_dir}. "
            "Please download from https://github.com/remsky/kokoro-onnx/releases"
        )

    return str(model_path)
```

---

## Qwen TTS Status

Qwen engine (`core/tts/qwen_engine.py`) is a STUB that returns silence:
- `_available = False` (qwen3_tts not installed)
- `generate()` returns 1 second of silence

To get Qwen working:
1. Install `qwen3_tts` package
2. Download Qwen3-TTS model
3. Update `qwen_engine.py` to use real implementation

---

## Next Steps

1. SSH to server: `ssh sprecher.nexus.home.test`
2. Investigate kokoro-onnx import issue
3. Confirm model files exist or download them
4. Apply fix to `kokoro_engine.py`
5. Test TTS sync with valid request
6. Then work on Qwen integration