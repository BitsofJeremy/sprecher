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
    # Check if auth is disabled via config
    if config.AUTH_DISABLED:
        return True

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

    # Generate unique filename
    file_id = uuid.uuid4().hex[:12]
    output_filename = f"{file_id}.{audio_format}"
    output_path = config.WORK_DIR / "data" / "output" / output_filename

    # Get engine and generate
    if engine == "kokoro":
        tts_engine = get_kokoro_engine()
        # Validate voice
        if not tts_engine.validate_voice(voice):
            raise HTTPException(status_code=400, detail=f"Invalid voice: '{voice}'. Use /api/tts/voices to list available voices.")
        # Generate audio
        await tts_engine.generate_to_file(
            text=text,
            voice=voice,
            output_path=output_path,
            speed=speed,
            audio_format=audio_format,
        )
    elif engine == "qwen":
        from core.tts.qwen_engine import get_qwen_engine
        qwen_engine = get_qwen_engine()
        if not qwen_engine.is_available:
            raise HTTPException(status_code=503, detail="Qwen engine not available (GPU required)")
        if not qwen_engine.validate_voice(voice):
            raise HTTPException(status_code=400, detail=f"Invalid voice: '{voice}'. Use /api/tts/voices to list available voices.")
        await qwen_engine.generate_to_file(
            text=text,
            voice=voice,
            output_path=output_path,
            speed=speed,
            audio_format=audio_format,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Engine '{engine}' not supported. Use 'kokoro' or 'qwen'.")

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


@router.post("/tts")
async def tts_async(
    text: str = Form(...),
    voice: str = Form(default="bf_isabella"),
    engine: str = Form(default="kokoro"),
    speed: float = Form(default=1.0),
    audio_format: str = Form(default="wav"),
    title: str = Form(default="TTS Job"),
    author: str = Form(default=""),
    authorization: Optional[str] = Header(None),
):
    """
    Submit an async TTS job for processing.

    Returns job ID for tracking via GET /api/tts/jobs/{id}.
    """
    await verify_api_key(authorization)

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    # Get engine and validate voice
    if engine == "kokoro":
        kokoro = get_kokoro_engine()
        if not kokoro.validate_voice(voice):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid voice: '{voice}'. Use /api/tts/voices to list available voices."
            )
    elif engine == "qwen":
        from core.tts.qwen_engine import get_qwen_engine
        qwen = get_qwen_engine()
        if not qwen.validate_voice(voice):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid voice: '{voice}'. Use /api/tts/voices to list available voices."
            )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Engine '{engine}' not supported. Use 'kokoro' or 'qwen'."
        )

    # Create job in database
    from db.jobs import create_job
    job_id = await create_job(
        title=title,
        engine=engine,
        voice_key=voice,
        status="queued",
        scope="tts",
        source_path=text,
        audio_format=audio_format,
        speed=speed,
        author=author,
    )

    # Queue the job for async processing
    from jobs.queue import get_job_runner
    runner = get_job_runner()

    # Prepare job data
    from jobs.models import TTSJob, JobStatus
    job = TTSJob(
        id=job_id,
        title=title,
        engine=engine,
        voice_key=voice,
        status=JobStatus.QUEUED,
        source_path=text,
        audio_format=audio_format,
        speed=speed,
        author=author,
    )

    # Enqueue for async processing
    await runner.enqueue(_process_tts_job, job)

    return JSONResponse({
        "job_id": job_id,
        "status": "queued",
        "message": "TTS job submitted successfully",
    })


async def _process_tts_job(job: "TTSJob") -> str:
    """Internal function to process a TTS job."""
    from jobs.tasks import run_tts_task
    from db.jobs import complete_job, fail_job, update_job
    import uuid

    try:
        # Update job status to running
        await update_job(job.id, status="running", progress=0)

        # Get engine and generate
        if job.engine == "kokoro":
            from core.tts.kokoro_engine import get_kokoro_engine
            engine = get_kokoro_engine()
        else:
            from core.tts.qwen_engine import get_qwen_engine
            engine = get_qwen_engine()

        # Generate output path if not set
        output_path = job.output_path
        if not output_path:
            output_path = str(config.WORK_DIR / "data" / "output" / f"{uuid.uuid4().hex[:12]}.{job.audio_format}")

        await engine.generate_to_file(
            text=job.source_path,
            voice=job.voice_key,
            output_path=Path(output_path),
            speed=job.speed,
            audio_format=job.audio_format,
        )

        # Mark complete
        await complete_job(job.id, output_path)
        return output_path

    except Exception as e:
        await fail_job(job.id, str(e))
        raise


@router.get("/tts/jobs")
async def tts_list_jobs(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    engine: Optional[str] = None,
    authorization: Optional[str] = Header(None),
):
    """
    List TTS jobs with optional filters.

    - **limit**: Maximum number of results (default 50)
    - **offset**: Pagination offset
    - **status**: Filter by status (queued, running, completed, failed)
    - **engine**: Filter by engine (kokoro, qwen)
    """
    await verify_api_key(authorization)

    from db.jobs import list_jobs
    jobs = await list_jobs(
        limit=limit,
        offset=offset,
        status=status,
        engine=engine,
        scope="tts",
    )

    return JSONResponse({"jobs": jobs})


@router.get("/tts/jobs/{job_id}")
async def tts_get_job(
    job_id: int,
    authorization: Optional[str] = Header(None),
):
    """
    Get TTS job status and details.

    Returns job info including status, progress, and output path if completed.
    """
    await verify_api_key(authorization)

    from db.jobs import get_job
    job = await get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("scope") != "tts":
        raise HTTPException(status_code=404, detail="Job is not a TTS job")

    return JSONResponse(job)