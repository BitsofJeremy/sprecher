"""TTS API endpoints."""

import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Form, UploadFile, File
from fastapi.responses import JSONResponse

import config
from core.tts.kokoro_engine import get_kokoro_engine

router = APIRouter()


async def verify_api_key(authorization: Optional[str] = Header(None)) -> bool:
    """Verify API key if configured."""
    if not config.API_KEY:
        return True  # No auth configured

    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    token = authorization[7:]  # Strip "Bearer "
    if token != config.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True


@router.post("/tts/sync")
async def tts_sync(
    text: str = Form(...),
    voice: str = Form(default="bf_isabella"),
    engine: str = Form(default="kokoro"),
    speed: float = Form(default=1.0),
    audio_format: str = Form(default="wav"),
    authorization: Optional[str] = Header(None),
):
    """
    Synchronous TTS generation.

    Returns audio file URL and metadata.
    """
    await verify_api_key(authorization)

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    if engine != "kokoro":
        raise HTTPException(status_code=400, detail=f"Engine '{engine}' not supported in Phase 1a. Use 'kokoro'.")

    # Generate unique filename
    file_id = uuid.uuid4().hex[:12]
    output_filename = f"{file_id}.{audio_format}"
    output_path = config.WORK_DIR / "data" / "output" / output_filename

    # Get Kokoro engine and generate
    kokoro = get_kokoro_engine()

    # Validate voice
    if not kokoro.validate_voice(voice):
        raise HTTPException(status_code=400, detail=f"Invalid voice: '{voice}'. Use /api/tts/voices to list available voices.")

    # Generate audio
    await kokoro.generate_to_file(
        text=text,
        voice=voice,
        output_path=output_path,
        speed=speed,
        audio_format=audio_format,
    )

    # Calculate duration (approximate for short texts)
    duration = len(text) / (150 * speed)  # ~150 words per minute

    return JSONResponse({
        "audio_url": f"/audio/output/{output_filename}",
        "duration_seconds": round(duration, 2),
        "engine": engine,
        "voice": voice,
        "format": audio_format,
    })


@router.get("/tts/voices")
async def tts_voices(authorization: Optional[str] = Header(None)):
    """List available Kokoro voices."""
    await verify_api_key(authorization)

    kokoro = get_kokoro_engine()
    voices = kokoro.list_voices()

    return JSONResponse({"voices": voices})


@router.get("/tts/engines")
async def tts_engines(authorization: Optional[str] = Header(None)):
    """List available TTS engines and their capabilities."""
    await verify_api_key(authorization)

    from core.engine_router import get_engine_router

    router_instance = get_engine_router()
    engines = router_instance.list_engines()

    return JSONResponse({"engines": engines})