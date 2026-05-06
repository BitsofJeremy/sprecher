# Sprecher Debugging TODO

## Status: COMPLETED (2026-05-06)

Both Kokoro and Qwen TTS are now working.

---

## Completed Fixes

### Kokoro TTS - Fixed
**Problem:** `kokoro_onnx.utils.download_model` doesn't exist in kokoro-onnx v0.5.0
**Fix:** Updated `_ensure_model()` in `core/tts/kokoro_engine.py` to raise clear `FileNotFoundError` if models missing instead of trying to download.

### Service Configuration - Fixed
**Problem:** Service ran as `User=root` with `SPRECHER_WORK_DIR=/root/sprecher`
**Fix:** Changed to `User=jeremy` and `SPRECHER_WORK_DIR=/home/jeremy/Documents/current_projects/ai_speech/sprecher`

### Qwen TTS - Implemented
**Problem:** Qwen was a stub returning silence
**Fix:** Installed `qwen-tts` package, updated `qwen_engine.py` to use real Qwen3-TTS-12Hz-1.7B-VoiceDesign model

---

## Current State

### Working Engines
- **Kokoro**: 53 voices, fast CPU inference
- **Qwen**: 10 voice design presets, requires NVIDIA GPU

### Model Locations
- Kokoro models: `/home/jeremy/.claude/kokoro-models/` (symlinked from `/home/jeremy/models/`)
- Qwen model: HuggingFace cache at `~/.cache/huggingface/hub/models--Qwen--Qwen3-TTS-12Hz-1.7B-VoiceDesign`

### GPU Memory Note
Qwen requires ~8GB GPU memory. ComfyUI was using 8.6GB on the RTX 3060.
If Qwen fails with OOM, stop ComfyUI first: `kill $(pgrep -f comfyui)`

### Available Qwen Voice Designs
```
qwen_warm      - warm and friendly female voice
qwen_pro       - professional business tone
qwen_narrator  - deep narrative voice for storytelling
qwen_young     - young energetic person
qwen_calm      - calm and soothing voice
qwen_british   - British accent formal
qwen_american  - casual American accent
qwen_robot     - robotic synthetic voice
qwen_whisper   - soft whisper
qwen_excited   - very excited and enthusiastic
```

---

## Testing Commands

```bash
# Health check
curl http://localhost:8400/api/health

# List engines
curl http://localhost:8400/api/tts/engines -H "Authorization: Bearer sprecher-secret-key-2026"

# Test Kokoro
curl -X POST http://localhost:8400/api/tts/sync \
  -H "Authorization: Bearer sprecher-secret-key-2026" \
  -d "text=Hello from Kokoro&voice=bf_emma&engine=kokoro"

# Test Qwen
curl -X POST http://localhost:8400/api/tts/sync \
  -H "Authorization: Bearer sprecher-secret-key-2026" \
  -d "text=Hello from Qwen voice design&voice=qwen_warm&engine=qwen"
```

---

## Known Issues

1. **flash-attn not installed** - Qwen works but is slower. Install with:
   ```bash
   pip install flash-attn --no-build-isolation
   ```

2. **Voice cloning not implemented** - Qwen supports voice cloning via `generate_voice_clone()` but we only exposed voice design. Could add if needed.

3. **ComfyUI GPU conflict** - Qwen and ComfyUI cannot coexist on 12GB GPU. Stop one to use the other.
