"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

import config


def get_lifespan():
    """Factory for lifespan context manager."""
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        config.ensure_dirs()

        # Import here to avoid circular deps
        from db import init_db_schema_async, get_db, seed_voices, seed_system_voices
        from jobs import get_job_runner

        async with get_db() as db:
            await init_db_schema_async(db)
            await seed_voices(db)
            await seed_system_voices(db)

        runner = get_job_runner()

        yield

        runner.stop()

    return lifespan


app = FastAPI(
    title="Sprecher",
    description="Unified TTS/STT Service - Kokoro ONNX + Qwen3-TTS + Whisper",
    version="0.1.0",
    lifespan=get_lifespan(),
)

# Mount static files
static_path = config.WORK_DIR / "static"
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Mount audio output directory
audio_output_path = config.WORK_DIR / "data" / "output"
audio_output_path.mkdir(parents=True, exist_ok=True)
app.mount("/audio/output", StaticFiles(directory=str(audio_output_path)), name="audio_output")

# Mount audio voices directory
audio_voices_path = config.WORK_DIR / "data" / "voices"
audio_voices_path.mkdir(parents=True, exist_ok=True)
app.mount("/audio/voices", StaticFiles(directory=str(audio_voices_path)), name="audio_voices")

# Mount web static files
web_static_path = config.WORK_DIR / "web" / "static"
web_static_path.mkdir(parents=True, exist_ok=True)
app.mount("/web-static", StaticFiles(directory=str(web_static_path)), name="web_static")

# Include API router
from api.router import api_router
app.include_router(api_router)

# Include web router
from web.router import web_router
app.include_router(web_router)


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "name": "Sprecher API",
        "version": "0.1.0",
        "endpoints": {
            "health": "GET /api/health",
            "tts_sync": "POST /api/tts/sync",
            "tts_voices": "GET /api/tts/voices",
            "tts_engines": "GET /api/tts/engines",
            "stt_sync": "POST /api/stt/sync",
        }
    }


@app.get("/")
async def root():
    """Root redirect to dashboard."""
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/dashboard")
async def dashboard():
    """Dashboard redirect."""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content="<html><body><h1>Sprecher Dashboard</h1><p>Web UI coming soon...</p><p><a href='/tts'>Go to TTS</a></p><p><a href='/stt'>Go to STT</a></p></body></html>")