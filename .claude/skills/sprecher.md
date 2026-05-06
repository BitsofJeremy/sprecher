# Sprecher Agent Skill

## Overview

**Sprecher** is a unified TTS/STT service that AI agents use for voice synthesis and transcription. It combines:
- **Kokoro ONNX** — Fast, high-quality TTS with 54 voices and voice blending
- **Qwen3-TTS** — Voice cloning and voice design (GPU)
- **Whisper** — Speech-to-text transcription

## Quick Start

```bash
# Health check
curl http://localhost:8400/api/health

# List voices
curl http://localhost:8400/api/tts/voices

# Generate speech
curl -X POST http://localhost:8400/api/tts/sync \
  -d "text=Hello, I'm an AI agent.&voice=bf_isabella"
```

## Configuration

Set in your agent's environment:

```bash
export SPRECHER_BASE_URL="http://localhost:8400"
export SPRECHER_API_KEY="your-api-key"  # If configured
```

## TTS Usage

### Synchronous TTS

```bash
curl -X POST $SPRECHER_BASE_URL/api/tts/sync \
  -H "Authorization: Bearer $SPRECHER_API_KEY" \
  -d "text=Hello world&voice=bf_isabella&speed=1.0&audio_format=wav"
```

Response:
```json
{
  "audio_url": "/audio/output/abc123.wav",
  "duration_seconds": 1.5,
  "engine": "kokoro",
  "voice": "bf_isabella",
  "format": "wav"
}
```

### Voice Blending

Kokoro supports voice blending for unique sounds:

```
bf_emma(0.7)+af_sarah(0.3)  # 70% Emma, 30% Sarah
bm_george(0.8)+bf_alice(0.2)  # 80% George, 20% Alice
```

### Available Voices

| Prefix | Gender | Example |
|--------|--------|---------|
| `bf_` | British Female | bf_isabella, bf_emma, bf_sarah |
| `af_` | American Female | af_bella, af_nicole, af_sarah |
| `am_` | American Male | am_adam, am_michael, am_eric |
| `bm_` | British Male | bm_lewis, bm_george |

## STT Usage

```bash
curl -X POST $SPRECHER_BASE_URL/api/stt/sync \
  -H "Authorization: Bearer $SPRECHER_API_KEY" \
  -F "audio_file=@recording.wav"
```

Response:
```json
{
  "text": "Transcribed text here",
  "language": "en",
  "duration_seconds": 5.2
}
```

## Engine Selection

- **Kokoro** (default) — Fast, 54 voices, supports blending. Use for: general TTS needs
- **Qwen** — Voice cloning and design. Use for: custom voices from reference audio

## MCP Tools

When connected via MCP server:

| Tool | Description |
|------|-------------|
| `sprecher_speak` | Generate speech |
| `sprecher_list_voices` | List available voices |
| `sprecher_transcribe` | Transcribe audio to text |
| `sprecher_health` | Check service health |
| `sprecher_get_job` | Get async job status |

## Common Use Cases

### Agent Notification

```python
# Agent notification with custom voice
text = "Task completed successfully"
voice = "gentle_blend"  # or "bf_emma(0.7)+af_sarah(0.3)"
# Use sprecher_speak MCP tool
```

### Voice Cloning (Qwen)

For custom voices, the web UI at http://localhost:8400/voices provides:
- Voice cloning: upload reference audio + transcript
- Voice design: describe the voice in text

### Document Narration

Upload EPUB/TXT at http://localhost:8400/narrate for full audiobook synthesis.

## Troubleshooting

### "Invalid voice"

Check `/api/tts/voices` for valid voice keys.

### "Engine not available"

Qwen requires GPU. Kokoro works on CPU.

### "API key required"

Set `SPRECHER_API_KEY` or disable auth by unsetting it.
