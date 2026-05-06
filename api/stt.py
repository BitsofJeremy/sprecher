"""STT API endpoints."""
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Form, UploadFile, File
from fastapi.responses import JSONResponse

import config
from core.stt.whisper_engine import get_whisper_engine
from db.jobs import create_job, get_job, list_jobs, update_job
from jobs.models import STTJob

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


@router.post("/stt/async")
async def stt_async(
    audio_file: UploadFile = File(...),
    language: Optional[str] = Form(default=None),
    authorization: Optional[str] = Header(None),
):
    """
    Asynchronous STT transcription.

    Accepts audio file, creates a background job, and returns job ID.
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

    # Save uploaded file
    file_id = uuid.uuid4().hex[:12]
    upload_path = config.WORK_DIR / "data" / "uploads" / f"{file_id}{ext}"
    upload_path.parent.mkdir(parents=True, exist_ok=True)

    content = await audio_file.read()
    with open(upload_path, "wb") as f:
        f.write(content)

    # Create job in database
    job_id = await create_job(
        title=f"STT Transcription {filename}",
        engine="whisper",
        status="queued",
        scope="stt",
        source_path=str(upload_path),
        language=language or "",
    )

    # Enqueue job for background processing
    from jobs.queue import get_job_runner
    from jobs.models import STTJob

    runner = get_job_runner()
    job = STTJob(
        id=job_id,
        title=f"STT Transcription {filename}",
        source_path=str(upload_path),
        language=language,
    )
    from jobs.tasks import _process_stt_job
    await runner.enqueue(_process_stt_job, job)

    return JSONResponse({
        "job_id": job_id,
        "status": "queued",
        "message": "STT job created and queued for processing",
    })


@router.get("/stt/jobs")
async def stt_list_jobs(
    limit: int = 50,
    offset: int = 0,
    authorization: Optional[str] = Header(None),
):
    """List STT jobs."""
    await verify_api_key(authorization)

    jobs = await list_jobs(limit=limit, offset=offset, scope="stt")
    return JSONResponse({"jobs": jobs, "count": len(jobs)})


@router.get("/stt/jobs/{job_id}")
async def stt_get_job(
    job_id: int,
    authorization: Optional[str] = Header(None),
):
    """Get STT job status and result."""
    await verify_api_key(authorization)

    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["scope"] != "stt":
        raise HTTPException(status_code=404, detail="Job is not an STT job")

    return JSONResponse(job)
