# CLAUDE.md

Sprecher is a unified TTS/STT web service combining Qwen3-TTS (voice cloning/design) + Kokoro ONNX (54 fast voices) + Whisper STT. AI agents interact via REST API; humans use the web UI.

## Running the App

```bash
# Start the web server
uv sync
uv run app

# Or with systemd (after install.sh):
sudo systemctl start sprecher-web
sudo systemctl enable sprecher-web
```

## Tech Stack

- **Backend:** FastAPI + asyncio + aiosqlite (WAL mode)
- **TTS Engines:** Kokoro ONNX (fast, 54 voices), Qwen3-TTS (clone + design, GPU)
- **STT:** Whisper (openai-whisper)
- **Frontend:** Jinja2 + HTMX + Tailwind CDN (no JS framework)
- **Package management:** uv exclusively

## Architecture

```
Browser (HTMX) ──> FastAPI (async, aiosqlite) ──> SQLite
                        │
                   asyncio.to_thread() ──> TTS/STT Engines (GPU/CPU)
                                             │
                                        Kokoro ONNX (singleton)
                                        Qwen3-TTS (singleton)
                                        Whisper (singleton)
                        │
                        └── StaticFiles mounts: /static, /audio/output
```

**Two database access patterns.** FastAPI routes use async `aiosqlite` via `get_db()` with `try/finally` close. Job runners use synchronous context where needed.

**GPU singleton.** TTS engines are global singletons loaded on first use. Jobs may run sequentially depending on engine capability.

**Audio paths.** Generated audio files are stored in the `data/audio/` directory with absolute paths stored in SQLite. Templates use the `| basename` Jinja2 filter for StaticFiles mounting.

## API

| Endpoint | Method | Description |
|---|---|---|
| `/api/tts/sync` | POST | Synchronous TTS generation |
| `/api/tts/async` | POST | Async TTS job submission |
| `/api/tts/voices` | GET | List Kokoro voices |
| `/api/tts/engines` | GET | Engine capabilities |
| `/api/tts/jobs` | GET | List TTS jobs |
| `/api/tts/jobs/{id}` | GET | Get job status |
| `/api/stt/sync` | POST | Synchronous STT transcription |
| `/api/stt/async` | POST | Async STT job submission |
| `/api/health` | GET | Health check (no auth required) |

## Auth

Set `SPRECHER_API_KEY` env var. If set, API routes require `Authorization: Bearer <key>`.

```
# Example authenticated request
curl -X POST http://localhost:8400/api/tts/sync \
  -H "Authorization: Bearer your-api-key" \
  -d "text=Hello world&voice=bf_emma"
```

## Configuration

All env vars use the `SPRECHER_` prefix:

| Variable | Default | Notes |
|---|---|---|
| `SPRECHER_WORK_DIR` | `~/sprecher` | Runtime data root (uploads, output, voices, DB) |
| `SPRECHER_PORT` | `8400` | Web server port |
| `SPRECHER_API_KEY` | (none) | API key for auth (optional) |
| `SPRECHER_KOKORO_MODEL` | `auto` | Kokoro model path (auto = default) |
| `SPRECHER_QWEN_MODEL` | `auto` | Qwen3-TTS model path (auto = default) |
| `SPRECHER_WHISPER_MODEL` | `base` | Whisper model size (tiny/base/small/medium/large) |
| `SPRECHER_DEFAULT_VOICE` | `bf_emma` | Default Kokoro voice |

## File Layout

```
sprecher/
├── app/
│   ├── main.py              # FastAPI entry point
│   └── lifespan.py          # startup/shutdown events
├── app.py                  # Entry point script
├── config.py               # Settings via SPRECHER_ env vars
├── pyproject.toml          # All dependencies
├── CLAUDE.md               # This file
├── mcp/
│   └── server.py           # MCP server for Claude Code agents
├── scripts/
│   └── install.sh          # Systemd + Nginx installer
├── .claude/
│   ├── settings.json       # MCP server config
│   └── skills/
│       └── sprecher.md     # Agent skill for AI agents
├── core/
│   ├── engine_router.py    # TTS engine selection
│   ├── tts/
│   │   ├── base.py         # Abstract TTS engine interface
│   │   └── kokoro_engine.py  # Kokoro ONNX TTS
│   └── stt/
│       └── whisper_engine.py  # Whisper STT
├── db/
│   ├── schema.py           # SQLite schema
│   ├── get_db.py           # aiosqlite context manager
│   └── seed_data.py        # Seed voices + system presets
├── jobs/
│   ├── models.py           # Job data classes
│   ├── queue.py            # In-process job runner
│   └── tasks.py            # Sync job handlers
├── api/
│   ├── router.py           # Route aggregator
│   ├── tts.py              # TTS endpoints
│   ├── stt.py              # STT endpoints
│   └── health.py           # Health check
├── web/
│   ├── router.py           # Web route aggregator
│   ├── templates/          # Jinja2 templates
│   │   ├── base.html      # Layout with sidebar nav
│   │   ├── dashboard.html # Home dashboard
│   │   ├── tts.html       # Quick TTS form
│   │   ├── stt.html       # Speech-to-text form
│   │   ├── voices.html    # Voice library
│   │   ├── jobs.html      # Job list
│   │   └── job_detail.html # Job detail + progress
│   └── static/
│       ├── css/style.css   # Dark theme CSS
│       └── js/toast.js     # Toast notifications
├── data/                   # Runtime data (gitignored)
│   ├── uploads/           # Uploaded audio/files
│   ├── chunks/            # Processing chunks
│   ├── output/           # Generated audio
│   └── voices/           # Voice reference audio
└── static/
    └── css/style.css      # App CSS (legacy)
```

## Kokoro Voice Blending

Kokoro supports voice blending by combining multiple voices with weights:

```
# Format: voice_name(weight)+voice_name(weight)
bf_emma(0.7)+af_sarah(0.3)    # 70% Emma, 30% Sarah
zm_alex(0.5)+af_bella(0.5)    # 50/50 blend
bf_isabella(0.8)+zm_david(0.2) # Heavy Isabella with hint of David
```

Available voice prefixes:
- `bf_` = British Female
- `af_` = American Female
- `zm_` = Male
- `zf_` = Other

## Agent Usage

AI agents should use the REST API for seamless voice interaction.

```bash
# Set env vars in your agent config
export SPRECHER_API_KEY="your-key"
export SPRECHER_BASE_URL="http://localhost:8400"

# TTS example
curl -X POST $SPRECHER_BASE_URL/api/tts/sync \
  -H "Authorization: Bearer $SPRECHER_API_KEY" \
  -d "text=Hello, I'm Pixel Paradox reporting from The Edge.&voice=bf_emma"

# STT example
curl -X POST $SPRECHER_BASE_URL/api/stt/sync \
  -H "Authorization: Bearer $SPRECHER_API_KEY" \
  -F "audio_file=@recording.wav"
```

## Testing

```bash
# Health check
curl http://localhost:8400/api/health

# List available voices
curl http://localhost:8400/api/tts/voices

# Synchronous TTS test
curl -X POST http://localhost:8400/api/tts/sync \
  -d "text=Testing TTS&voice=bf_emma" \
  --output test.wav

# Synchronous STT test
curl -X POST http://localhost:8400/api/stt/sync \
  -F "audio_file=@test.wav"
```

## Known Issues

- No CSRF protection (acceptable for single-user local app)
- Whisper model download on first use (large file, ~140MB for base model)