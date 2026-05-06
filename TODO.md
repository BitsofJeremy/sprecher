# Sprecher - Project Status

## Status: Working (2026-05-06)

Both TTS engines are operational. Service is running and accessible via web UI and API.

---

## What's Working

### TTS Engines
| Engine | Voices | Status | Notes |
|--------|--------|--------|-------|
| Kokoro | 53 | ✅ Working | Fast CPU inference |
| Qwen | 10 | ✅ Working | Requires NVIDIA GPU (~8GB VRAM) |

### API Endpoints
- `GET /api/health` - Health check
- `GET /api/tts/engines` - List engines
- `GET /api/tts/voices` - List voices
- `POST /api/tts/sync` - Synchronous TTS generation

### Web UI
- Dashboard, TTS, Voices, Jobs, Narrate pages
- HTMX-powered forms with toast notifications

---

## Configuration

### Service
```bash
sudo systemctl status sprecher-web    # Check status
sudo systemctl restart sprecher-web   # Restart
journalctl -u sprecher-web -f        # View logs
```

### Environment Variables
| Variable | Current | Description |
|----------|---------|-------------|
| `SPRECHER_WORK_DIR` | `/home/jeremy/Documents/current_projects/ai_speech/sprecher` | Data directory |
| `SPRECHER_API_KEY` | `sprecher-secret-key-2026` | API authentication |
| `SPRECHER_AUTH_DISABLED` | `true` | Web UI auth bypass (remove for production) |

### Model Locations
- **Kokoro**: `~/.claude/kokoro-models/` → symlinked from `/home/jeremy/models/`
- **Qwen**: HuggingFace cache at `~/.cache/huggingface/hub/models--Qwen--Qwen3-TTS-12Hz-1.7B-VoiceDesign`

---

## Known Issues

1. **ComfyUI GPU conflict** - Qwen and ComfyUI cannot coexist on 12GB GPU
   ```bash
   kill $(pgrep -f comfyui)  # Stop ComfyUI to free GPU memory
   ```

2. **flash-attn not installed** - Qwen is slower but functional
   ```bash
   pip install flash-attn --no-build-isolation  # Optional optimization
   ```

---

## Future Enhancements

### High Priority
1. **User Accounts & API Keys**
   - Web UI login with username/password
   - Per-user API keys for agents
   - Usage tracking per user
   - Remove `SPRECHER_AUTH_DISABLED=true` once implemented

2. **Voice Cloning** - Expose Qwen's `generate_voice_clone()` method

### Medium Priority
1. **Voice Library UI Improvements** - Real CRUD instead of static cards
2. **Job Progress Streaming** - Real-time progress for long narrations
3. **Audio Preview** - Play button on voice cards

### Low Priority
1. **Multiple Language Support** - Qwen supports: Chinese, Japanese, Korean, German, French, Russian, Portuguese, Spanish, Italian
2. **Voice Blending** - UI for Kokoro's blend feature

---

## Testing

```bash
# Test web UI
open http://localhost:8400

# Test API (with auth)
curl -X POST http://localhost:8400/api/tts/sync \
  -H "Authorization: Bearer sprecher-secret-key-2026" \
  -d "text=Hello&voice=bf_emma&engine=kokoro"

# Test API (no auth - currently works due to AUTH_DISABLED)
curl -X POST http://localhost:8400/api/tts/sync \
  -d "text=Hello&voice=bf_emma&engine=kokoro"
```
