"""Narration API endpoints for document-to-audiobook conversion."""
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Form, UploadFile, File
from fastapi.responses import JSONResponse

import aiosqlite
import config
from db.jobs import create_job, get_job, list_jobs
from db.get_db import get_db
from jobs.models import NarrateJob
from jobs.queue import get_job_runner
from jobs.tasks import _process_narrate_job

router = APIRouter()


async def verify_api_key(authorization: Optional[str] = Header(None)) -> bool:
    """Verify API key if configured."""
    if config.AUTH_DISABLED:
        return True
    if not config.API_KEY:
        return True

    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    token = authorization[7:]
    if token != config.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True


async def get_voices():
    """Get list of available voices for narration."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM voices WHERE engine IN ('kokoro', 'qwen') ORDER BY name"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


@router.post("/narrate")
async def narrate_document(
    document: UploadFile = File(...),
    voice_id: Optional[int] = Form(default=None),
    voice_key: Optional[str] = Form(default=None),
    audio_format: str = Form(default="mp3"),
    speed: float = Form(default=1.0),
    author: str = Form(default=""),
    cover_art: Optional[UploadFile] = File(default=None),
    authorization: Optional[str] = Header(None),
):
    """
    Start a document narration job.

    Accepts an EPUB or TXT file and a voice selection.
    Returns the job ID for tracking.
    """
    await verify_api_key(authorization)

    if not document:
        raise HTTPException(status_code=400, detail="Document file is required")

    # Validate file type
    allowed_extensions = {".epub", ".txt", ".text"}
    filename = document.filename or "upload"
    ext = Path(filename).suffix.lower()

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported document format: {ext}. Supported: {', '.join(allowed_extensions)}"
        )

    # Get voice
    voice = None
    voice_key_str = voice_key or "bf_isabella"
    engine = "kokoro"

    if voice_id:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM voices WHERE id = ?", (voice_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    voice = dict(row)
                    voice_key_str = voice.get("voice_key", "bf_isabella")
                    engine = voice.get("engine", "kokoro")

    # Save uploaded document
    file_id = uuid.uuid4().hex[:12]
    doc_path = config.WORK_DIR / "data" / "uploads" / f"{file_id}{ext}"
    doc_path.parent.mkdir(parents=True, exist_ok=True)

    content = await document.read()
    with open(doc_path, "wb") as f:
        f.write(content)

    # Save cover art if provided
    cover_path = None
    if cover_art:
        cover_ext = Path(cover_art.filename or "cover").suffix.lower()
        if cover_ext in {".jpg", ".jpeg", ".png"}:
            cover_path = config.WORK_DIR / "data" / "uploads" / f"{file_id}_cover{cover_ext}"
            cover_content = await cover_art.read()
            with open(cover_path, "wb") as f:
                f.write(cover_content)

    # Generate output path
    output_path = config.WORK_DIR / "data" / "output" / f"narrate_{file_id}.{audio_format}"

    # Create job in database
    job_id = await create_job(
        title=f"Narration: {filename}",
        engine=engine,
        voice_id=voice_id,
        voice_key=voice_key_str,
        status="queued",
        scope="narrate",
        source_path=str(doc_path),
        output_path=str(output_path),
        audio_format=audio_format,
        speed=speed,
        author=author,
        cover_path=str(cover_path) if cover_path else "",
    )

    # Create NarrateJob and enqueue
    narrate_job = NarrateJob(
        id=job_id,
        title=f"Narration: {filename}",
        engine=engine,
        voice_id=voice_id,
        voice_key=voice_key_str,
        source_path=str(doc_path),
        output_path=str(output_path),
        audio_format=audio_format,
        speed=speed,
        author=author,
        cover_path=str(cover_path) if cover_path else "",
    )
    from jobs.tasks import _process_narrate_job
    runner = get_job_runner()
    await runner.enqueue(_process_narrate_job, narrate_job)

    return JSONResponse({
        "job_id": job_id,
        "status": "queued",
        "message": "Narration job created and queued for processing",
        "document": filename,
        "voice": voice_key_str,
        "output_format": audio_format,
    })


@router.get("/narrate/jobs")
async def narrate_list_jobs(
    limit: int = 50,
    offset: int = 0,
    authorization: Optional[str] = Header(None),
):
    """List narration jobs."""
    await verify_api_key(authorization)

    jobs = await list_jobs(limit=limit, offset=offset, scope="narrate")
    return JSONResponse({"jobs": jobs, "count": len(jobs)})


@router.get("/narrate/jobs/{job_id}")
async def narrate_get_job(
    job_id: int,
    authorization: Optional[str] = Header(None),
):
    """Get narration job status and result."""
    await verify_api_key(authorization)

    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["scope"] != "narrate":
        raise HTTPException(status_code=404, detail="Job is not a narration job")

    return JSONResponse(job)


@router.post("/narrate/preview")
async def narrate_preview(
    document: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
):
    """Preview a document's chapters before narration."""
    await verify_api_key(authorization)

    from core.narrate.parsers import parse_document

    if not document:
        raise HTTPException(status_code=400, detail="Document file is required")

    ext = Path(document.filename or "").suffix.lower()
    if ext not in {".epub", ".txt", ".text"}:
        raise HTTPException(status_code=400, detail="Unsupported format")

    # Save temporarily for parsing
    file_id = uuid.uuid4().hex[:12]
    doc_path = config.WORK_DIR / "data" / "uploads" / f"{file_id}{ext}"
    doc_path.parent.mkdir(parents=True, exist_ok=True)

    content = await document.read()
    with open(doc_path, "wb") as f:
        f.write(content)

    try:
        chapters = parse_document(doc_path)
        chapter_data = [
            {"title": ch.title, "word_count": ch.word_count}
            for ch in chapters
        ]
    finally:
        doc_path.unlink(missing_ok=True)

    total_words = sum(ch["word_count"] for ch in chapter_data)
    return JSONResponse({
        "chapters": chapter_data,
        "total_chapters": len(chapters),
        "total_words": total_words,
    })
