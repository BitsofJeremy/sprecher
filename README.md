# Sprecher

**Unified TTS/STT service for AI agents and humans.**

Sprecher combines Kokoro ONNX (fast 54-voice synthesis), Qwen3-TTS (voice cloning & design), and Whisper (transcription) into one service.

## Quick Start

```bash
uv sync
uv run app
```

Open http://localhost:8400

## API

```bash
# TTS
curl -X POST http://localhost:8400/api/tts/sync \
  -d "text=Hello&voice=bf_emma"

# STT
curl -X POST http://localhost:8400/api/stt/sync \
  -F "audio_file=@recording.wav"
```

## Install (Linux server)

```bash
sudo ./scripts/install.sh
sudo systemctl start sprecher-web
```

## Build for Bots

AI agents: use the REST API for seamless voice interaction.

Humans: beautiful dark-theme web UI at http://localhost:8400
