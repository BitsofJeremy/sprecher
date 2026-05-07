"""Database operations for voices table."""

import json
from datetime import datetime
from typing import Optional

import aiosqlite

from db.get_db import get_db


async def create_voice(
    name: str,
    slug: str,
    engine: str,
    voice_type: str,
    voice_key: Optional[str] = None,
    language: Optional[str] = None,
    voice_description: Optional[str] = None,
    ref_audio_path: Optional[str] = None,
    ref_text: Optional[str] = None,
    sample_audio_path: Optional[str] = None,
    speaking_style: str = "",
    emotional_range: list = None,
    is_system: bool = False,
) -> int:
    """
    Create a new voice in the database.

    Returns the voice ID.
    """
    if emotional_range is None:
        emotional_range = []

    async with get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO voices (
                name, slug, engine, voice_type, voice_key, language,
                voice_description, ref_audio_path, ref_text, sample_audio_path,
                speaking_style, emotional_range, is_system
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name, slug, engine, voice_type, voice_key, language,
                voice_description, ref_audio_path, ref_text, sample_audio_path,
                speaking_style, json.dumps(emotional_range), is_system,
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def get_voice(voice_id: int) -> Optional[dict]:
    """Get a voice by ID."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM voices WHERE id = ?", (voice_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                result = dict(row)
                # Parse emotional_range JSON
                if result.get("emotional_range"):
                    try:
                        result["emotional_range"] = json.loads(result["emotional_range"])
                    except (json.JSONDecodeError, TypeError):
                        result["emotional_range"] = []
                return result
            return None


async def get_voice_by_key(voice_key: str) -> Optional[dict]:
    """Get a voice by voice_key or slug."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM voices WHERE voice_key = ? OR slug = ? LIMIT 1",
            (voice_key, voice_key),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                result = dict(row)
                if result.get("emotional_range"):
                    try:
                        result["emotional_range"] = json.loads(result["emotional_range"])
                    except (json.JSONDecodeError, TypeError):
                        result["emotional_range"] = []
                return result
            return None


async def get_voice_by_slug(slug: str) -> Optional[dict]:
    """Get a voice by slug."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM voices WHERE slug = ?", (slug,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                result = dict(row)
                if result.get("emotional_range"):
                    try:
                        result["emotional_range"] = json.loads(result["emotional_range"])
                    except (json.JSONDecodeError, TypeError):
                        result["emotional_range"] = []
                return result
            return None


async def list_voices(
    limit: int = 100,
    offset: int = 0,
    engine: Optional[str] = None,
    voice_type: Optional[str] = None,
    is_system: Optional[bool] = None,
) -> list[dict]:
    """List voices with optional filters."""
    query = "SELECT * FROM voices WHERE 1=1"
    params = []

    if engine:
        query += " AND engine = ?"
        params.append(engine)
    if voice_type:
        query += " AND voice_type = ?"
        params.append(voice_type)
    if is_system is not None:
        query += " AND is_system = ?"
        params.append(1 if is_system else 0)

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            results = []
            for row in rows:
                result = dict(row)
                if result.get("emotional_range"):
                    try:
                        result["emotional_range"] = json.loads(result["emotional_range"])
                    except (json.JSONDecodeError, TypeError):
                        result["emotional_range"] = []
                results.append(result)
            return results


async def update_voice(
    voice_id: int,
    name: Optional[str] = None,
    slug: Optional[str] = None,
    voice_key: Optional[str] = None,
    language: Optional[str] = None,
    voice_description: Optional[str] = None,
    ref_audio_path: Optional[str] = None,
    ref_text: Optional[str] = None,
    sample_audio_path: Optional[str] = None,
    speaking_style: Optional[str] = None,
    emotional_range: Optional[list] = None,
) -> bool:
    """Update voice fields."""
    updates = []
    params = []

    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if slug is not None:
        updates.append("slug = ?")
        params.append(slug)
    if voice_key is not None:
        updates.append("voice_key = ?")
        params.append(voice_key)
    if language is not None:
        updates.append("language = ?")
        params.append(language)
    if voice_description is not None:
        updates.append("voice_description = ?")
        params.append(voice_description)
    if ref_audio_path is not None:
        updates.append("ref_audio_path = ?")
        params.append(ref_audio_path)
    if ref_text is not None:
        updates.append("ref_text = ?")
        params.append(ref_text)
    if sample_audio_path is not None:
        updates.append("sample_audio_path = ?")
        params.append(sample_audio_path)
    if speaking_style is not None:
        updates.append("speaking_style = ?")
        params.append(speaking_style)
    if emotional_range is not None:
        updates.append("emotional_range = ?")
        params.append(json.dumps(emotional_range))

    if not updates:
        return False

    params.append(voice_id)
    query = f"UPDATE voices SET {', '.join(updates)} WHERE id = ?"

    async with get_db() as db:
        cursor = await db.execute(query, params)
        await db.commit()
        return cursor.rowcount > 0


async def delete_voice(voice_id: int) -> bool:
    """Delete a voice by ID."""
    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM voices WHERE id = ? AND is_system = 0",
            (voice_id,),
        )
        await db.commit()
        return cursor.rowcount > 0
