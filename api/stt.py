"""STT API endpoints."""

import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Form, UploadFile, File
from fastapi.responses import JSONResponse

import config
from core.stt.whisper_engine import get_whisper_engine

router = APIRouter()


async def verify_api_key(authorization: Optional[str] = Header(None)) -> bool:
    """Verify API key if configured."""
    if not config.API_KEY:
        return True  # No auth configured

    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    token = authorization[7:]
    if token != config.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True


@router.post("/stt/sync")
async def stt_sync(
    audio_file: UploadFile = File(...),
    language: Optional[str] = Form(default=None),
    authorization: Optional[str] = Header(None),
):
    """
    Synchronous STT transcription.

    Accepts audio file and returns transcribed text.
    """
    await verify_api_key(authorization)

    if not audio_file:
        raise HTTPException(status_code=400, detail="Audio file is required")

    # Validate file type
    allowed_extensions = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm"}
    filename = audio_file.filename or "upload"
    ext = Path(filename).suffix.lower()

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {ext}. Supported: {', '.join(allowed_extensions)}"
        )

    # Save uploaded file temporarily
    file_id = uuid.uuid4().hex[:12]
    upload_path = config.WORK_DIR / "data" / "uploads" / f"{file_id}{ext}"

    # Ensure directory exists
    upload_path.parent.mkdir(parents=True, exist_ok=True)

    # Write uploaded content
    content = await audio_file.read()
    with open(upload_path, "wb") as f:
        f.write(content)

    # Transcribe with Whisper
    whisper = get_whisper_engine()
    result = await whisper.transcribe(upload_path, language=language)

    # Clean up temp file
    upload_path.unlink(missing_ok=True)

    return JSONResponse({
        "text": result["text"],
        "language": result["language"],
        "duration_seconds": round(result["duration"], 2),
    })