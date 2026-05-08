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


async def _resolve_voice(voice_key: str) -> dict | None:
    """Look up a voice in the DB by voice_key or slug.

    Returns the voice record dict or None if not found.
    """
    from db.voices import get_voice_by_key
    return await get_voice_by_key(voice_key)


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

    For clone/ephergent voices, the voice record is looked up in the DB
    and ref_audio_path + ref_text are passed to the Qwen clone engine.
    """
    await verify_api_key(authorization)

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    file_id = uuid.uuid4().hex[:12]
    output_filename = f"{file_id}.{audio_format}"
    output_path = config.WORK_DIR / "data" / "output" / output_filename

    # Look up voice in DB (clone/ephergent voices have DB records)
    voice_record = await _resolve_voice(voice)
    ref_audio_path = None
    ref_text = None
    effective_engine = engine

    if voice_record:
        vt = voice_record.get("voice_type", "")
        # Route clone/ephergent voices to Qwen with reference audio
        if vt in ("clone", "ephergent"):
            ref_audio_path = voice_record.get("ref_audio_path")
            ref_text = voice_record.get("ref_text")
            effective_engine = "qwen"  # Qwen handles voice cloning
        elif voice_record.get("engine"):
            effective_engine = voice_record["engine"]

    # --- Kokoro ---
    if effective_engine == "kokoro":
        tts_engine = get_kokoro_engine()
        if not tts_engine.validate_voice(voice):
            raise HTTPException(status_code=400, detail=f"Invalid voice: '{voice}'. Use /api/tts/voices to list available voices.")
        await tts_engine.generate_to_file(
            text=text,
            voice=voice,
            output_path=output_path,
            speed=speed,
            audio_format=audio_format,
        )

    # --- Qwen (design or clone) ---
    elif effective_engine == "qwen":
        from core.tts.qwen_engine import get_qwen_engine
        qwen_engine = get_qwen_engine()
        if not qwen_engine.is_available:
            raise HTTPException(status_code=503, detail="Qwen engine not available (GPU required)")
        if not qwen_engine.validate_voice(voice) and not ref_audio_path:
            raise HTTPException(status_code=400, detail=f"Invalid voice: '{voice}'. Use /api/tts/voices to list available voices.")
        await qwen_engine.generate_to_file(
            text=text,
            voice=voice,
            output_path=output_path,
            speed=speed,
            audio_format=audio_format,
            ref_audio_path=ref_audio_path,
            ref_text=ref_text,
        )

    else:
        raise HTTPException(status_code=400, detail=f"Engine '{effective_engine}' not supported. Use 'kokoro' or 'qwen'.")

    duration = len(text) / (150 * speed)

    return JSONResponse({
        "audio_url": f"/audio/output/{output_filename}",
        "duration_seconds": round(duration, 2),
        "engine": effective_engine,
        "voice": voice,
        "format": audio_format,
    })


@router.get("/tts/voices")
async def tts_voices(authorization: Optional[str] = Header(None)):
    """List available Kokoro voices, plus any custom voices from the DB."""
    await verify_api_key(authorization)

    kokoro = get_kokoro_engine()
    kokoro_voices = kokoro.list_voices()

    # Also fetch custom voices from DB (Ephergent voices, etc.)
    from db.voices import list_voices as db_list_voices
    db_voices = await db_list_voices(limit=100)

    # Get valid Kokoro voice keys from actual voices.bin
    valid_kokoro_keys = {v["key"] for v in kokoro_voices}

    custom_voices = []
    for v in db_voices:
        voice_key = v.get("voice_key") or v.get("slug") or str(v["id"])

        # Skip ALL Kokoro preset voices (they come from list_voices)
        # Only add blends and custom voices from DB
        if v.get("engine") == "kokoro" and v.get("voice_type") == "preset":
            continue

        custom_voices.append({
            "key": voice_key,
            "name": v["name"],
            "gender": v.get("speaking_style", "").lower() or "neutral",
            "lang": v.get("language", "en-us"),
            "description": v.get("voice_description", ""),
            "engine": v["engine"],
            "voice_type": v.get("voice_type"),
            "slug": v.get("slug"),
            "voice_key": v.get("voice_key"),
            "ref_audio_path": v.get("ref_audio_path"),
            "ref_text": v.get("ref_text"),
        })


    all_voices = kokoro_voices + custom_voices
    return JSONResponse({"voices": all_voices})


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
    """Submit an async TTS job for processing."""
    await verify_api_key(authorization)

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    # Look up voice in DB
    voice_record = await _resolve_voice(voice)
    ref_audio_path = None
    ref_text = None
    effective_engine = engine

    if voice_record:
        vt = voice_record.get("voice_type", "")
        if vt in ("clone", "ephergent"):
            ref_audio_path = voice_record.get("ref_audio_path")
            ref_text = voice_record.get("ref_text")
            effective_engine = "qwen"
        elif voice_record.get("engine"):
            effective_engine = voice_record["engine"]

    # Validate
    if effective_engine == "kokoro":
        kokoro = get_kokoro_engine()
        if not kokoro.validate_voice(voice):
            raise HTTPException(status_code=400, detail=f"Invalid voice: '{voice}'. Use /api/tts/voices to list available voices.")
    elif effective_engine == "qwen":
        from core.tts.qwen_engine import get_qwen_engine
        qwen = get_qwen_engine()
        if not qwen.is_available:
            raise HTTPException(status_code=503, detail="Qwen engine not available (GPU required)")
    else:
        raise HTTPException(status_code=400, detail=f"Engine '{effective_engine}' not supported.")

    # Create job in database
    from db.jobs import create_job
    job_id = await create_job(
        title=title,
        engine=effective_engine,
        voice_key=voice,
        status="queued",
        scope="tts",
        source_path=text,
        audio_format=audio_format,
        speed=speed,
        author=author,
    )

    # Queue the job
    from jobs.queue import get_job_runner
    runner = get_job_runner()
    from jobs.models import TTSJob, JobStatus
    job = TTSJob(
        id=job_id,
        title=title,
        engine=effective_engine,
        voice_key=voice,
        status=JobStatus.QUEUED,
        source_path=text,
        audio_format=audio_format,
        speed=speed,
        author=author,
    )

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
    import logging
    logger = logging.getLogger(__name__)

    try:
        await update_job(job.id, status="running", progress=0)
        output_path = await run_tts_task(job)
        await complete_job(job.id, str(output_path))
        return str(output_path)
    except Exception as e:
        logger.error(f"TTS job {job.id} failed: {e}", exc_info=True)
        await fail_job(job.id, str(e))
        raise


# ─── Legacy / backward-compatible paths (handled by web router) ───────────────

@router.get("/tts/jobs/{job_id}")
async def tts_get_job(job_id: int, authorization: Optional[str] = Header(None)):
    """Get TTS job status and result."""
    await verify_api_key(authorization)
    from db.jobs import get_job
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(dict(job))


@router.get("/tts/jobs/{job_id}/cancel")
async def tts_cancel_job(job_id: int, authorization: Optional[str] = Header(None)):
    """Cancel a queued TTS job."""
    await verify_api_key(authorization)
    from db.jobs import cancel_job
    ok = await cancel_job(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
    return JSONResponse({"status": "cancelled", "job_id": job_id})
