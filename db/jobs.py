"""Database operations for jobs table."""

from datetime import datetime
from typing import Optional

import aiosqlite

from db.get_db import get_db


async def create_job(
    title: str,
    engine: str,
    voice_id: Optional[int] = None,
    voice_key: str = "",
    status: str = "queued",
    scope: str = "tts",
    source_path: str = "",
    output_path: Optional[str] = None,
    audio_format: str = "wav",
    speed: float = 1.0,
    author: str = "",
    cover_path: str = "",
    language: str = "",
) -> int:
    """
    Create a new job in the database.

    Returns the job ID.
    """
    async with get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO jobs (
                title, engine, voice_id, voice_key, status, scope,
                source_path, output_path, audio_format, speed, author, cover_path, language
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (title, engine, voice_id, voice_key, status, scope,
             source_path, output_path, audio_format, speed, author, cover_path, language),
        )
        await db.commit()
        return cursor.lastrowid


async def get_job(job_id: int) -> Optional[dict]:
    """Get a job by ID."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM jobs WHERE id = ?", (job_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None


async def list_jobs(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    engine: Optional[str] = None,
    scope: Optional[str] = None,
) -> list[dict]:
    """List jobs with optional filters."""
    query = "SELECT * FROM jobs WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if engine:
        query += " AND engine = ?"
        params.append(engine)
    if scope:
        query += " AND scope = ?"
        params.append(scope)

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def update_job(
    job_id: int,
    status: Optional[str] = None,
    progress: Optional[int] = None,
    total_chunks: Optional[int] = None,
    completed_chunks: Optional[int] = None,
    output_path: Optional[str] = None,
    error_message: Optional[str] = None,
) -> bool:
    """Update job fields."""
    updates = []
    params = []

    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if progress is not None:
        updates.append("progress = ?")
        params.append(progress)
    if total_chunks is not None:
        updates.append("total_chunks = ?")
        params.append(total_chunks)
    if completed_chunks is not None:
        updates.append("completed_chunks = ?")
        params.append(completed_chunks)
    if output_path is not None:
        updates.append("output_path = ?")
        params.append(output_path)
    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)

    if not updates:
        return False

    if status in ("completed", "failed"):
        updates.append("completed_at = ?")
        params.append(datetime.utcnow().isoformat())

    params.append(job_id)
    query = f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?"

    async with get_db() as db:
        cursor = await db.execute(query, params)
        await db.commit()
        return cursor.rowcount > 0


async def complete_job(job_id: int, output_path: str) -> bool:
    """Mark a job as completed with output path."""
    return await update_job(
        job_id,
        status="completed",
        progress=100,
        output_path=output_path,
    )


async def fail_job(job_id: int, error_message: str) -> bool:
    """Mark a job as failed with error message."""
    return await update_job(
        job_id,
        status="failed",
        error_message=error_message,
    )
