"""Jobs API endpoints (cancel, retry, progress)."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import JSONResponse

import config
from db.jobs import get_job, update_job, list_jobs
from jobs.queue import get_job_runner
from jobs.models import JobStatus, TTSJob, NarrateJob, STTJob

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


@router.get("/jobs/{job_id}/progress")
async def job_progress(
    job_id: int,
    authorization: Optional[str] = Header(None),
):
    """Get job progress for polling."""
    await verify_api_key(authorization)

    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JSONResponse({
        "job_id": job_id,
        "status": job["status"],
        "progress": job.get("progress", 0),
        "total_chunks": job.get("total_chunks"),
        "completed_chunks": job.get("completed_chunks"),
        "output_path": job.get("output_path"),
        "error_message": job.get("error_message"),
    })


@router.get("/jobs/{job_id}/cancel")
async def job_cancel(
    job_id: int,
    authorization: Optional[str] = Header(None),
):
    """Cancel a running or queued job."""
    await verify_api_key(authorization)

    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status '{job['status']}'")

    await update_job(job_id, status="cancelled")
    return JSONResponse({"job_id": job_id, "status": "cancelled", "message": "Job cancelled"})


@router.get("/jobs/{job_id}/retry")
async def job_retry(
    job_id: int,
    authorization: Optional[str] = Header(None),
):
    """Retry a failed or cancelled job."""
    await verify_api_key(authorization)

    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] not in ("failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot retry job with status '{job['status']}'")

    await update_job(job_id, status="queued", progress=0, error_message="")

    runner = get_job_runner()

    if job["scope"] == "tts":
        from jobs.tasks import _process_tts_job
        tts_job = TTSJob(
            id=job_id,
            title=job["title"],
            engine=job["engine"],
            voice_key=job.get("voice_key", "bf_isabella"),
            status=JobStatus.QUEUED,
            source_path=job.get("source_path", ""),
            audio_format=job.get("audio_format", "mp3"),
            speed=job.get("speed", 1.0),
            author=job.get("author", ""),
        )
        await runner.enqueue(_process_tts_job, tts_job)
    elif job["scope"] == "narrate":
        from jobs.tasks import _process_narrate_job
        narrate_job = NarrateJob(
            id=job_id,
            title=job["title"],
            engine=job["engine"],
            voice_id=job.get("voice_id"),
            voice_key=job.get("voice_key", "bf_isabella"),
            source_path=job.get("source_path", ""),
            output_path=job.get("output_path", ""),
            audio_format=job.get("audio_format", "mp3"),
            speed=job.get("speed", 1.0),
            author=job.get("author", ""),
            cover_path=job.get("cover_path", ""),
        )
        await runner.enqueue(_process_narrate_job, narrate_job)
    elif job["scope"] == "stt":
        from jobs.tasks import _process_stt_job
        stt_job = STTJob(
            id=job_id,
            title=job["title"],
            source_path=job.get("source_path", ""),
            language=job.get("language"),
        )
        await runner.enqueue(_process_stt_job, stt_job)

    return JSONResponse({"job_id": job_id, "status": "queued", "message": "Job re-queued for processing"})


@router.get("/jobs")
async def list_all_jobs(
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None,
    authorization: Optional[str] = Header(None),
):
    """List all jobs (TTS, STT, narrate) with optional filters."""
    await verify_api_key(authorization)

    jobs = await list_jobs(
        limit=limit,
        offset=offset,
        status=status_filter,
    )
    return JSONResponse({"jobs": jobs, "count": len(jobs)})


@router.get("/jobs/{job_id}")
async def get_job_by_id(
    job_id: int,
    authorization: Optional[str] = Header(None),
):
    """Get any job by ID regardless of scope."""
    await verify_api_key(authorization)

    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JSONResponse(job)
