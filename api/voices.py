"""Voice CRUD API endpoints."""

import json
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Form

import config
from db.voices import (
    create_voice,
    get_voice,
    get_voice_by_slug,
    list_voices,
    update_voice,
    delete_voice,
)

router = APIRouter()


def make_slug(name: str) -> str:
    """Generate a URL-safe slug from a name."""
    slug = name.lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    return slug


async def verify_api_key(authorization: Optional[str] = Header(None)) -> bool:
    """Verify API key if configured."""
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


@router.post("/voices")
async def create_voice_endpoint(
    name: str = Form(...),
    engine: str = Form(...),
    voice_type: str = Form(...),
    slug: Optional[str] = Form(None),
    voice_key: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    voice_description: Optional[str] = Form(None),
    ref_audio_path: Optional[str] = Form(None),
    ref_text: Optional[str] = Form(None),
    speaking_style: str = Form(""),
    emotional_range: str = Form("[]"),
    authorization: Optional[str] = Header(None),
):
    """
    Create a new custom voice.

    - **name**: Display name for the voice
    - **engine**: TTS engine ('kokoro' or 'qwen')
    - **voice_type**: Type of voice ('clone', 'designed', 'preset', 'blend')
    - **slug**: URL-safe identifier (auto-generated if not provided)
    - **voice_key**: Engine-specific voice key to use
    - **language**: Language code (e.g., 'en-us')
    - **voice_description**: Human-readable description
    - **ref_audio_path**: Path to reference audio for cloning
    - **ref_text**: Transcript of reference audio
    - **speaking_style**: Speaking style description
    - **emotional_range**: JSON list of emotional ranges
    """
    await verify_api_key(authorization)

    if engine not in ("kokoro", "qwen"):
        raise HTTPException(
            status_code=400,
            detail=f"Engine must be 'kokoro' or 'qwen', got '{engine}'"
        )

    if voice_type not in ("clone", "designed", "preset", "blend"):
        raise HTTPException(
            status_code=400,
            detail="voice_type must be 'clone', 'designed', 'preset', or 'blend'"
        )

    # Generate slug if not provided
    if not slug:
        slug = make_slug(name)

    # Parse emotional_range JSON
    try:
        emotional_range_list = json.loads(emotional_range)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="emotional_range must be valid JSON")

    voice_id = await create_voice(
        name=name,
        slug=slug,
        engine=engine,
        voice_type=voice_type,
        voice_key=voice_key,
        language=language,
        voice_description=voice_description,
        ref_audio_path=ref_audio_path,
        ref_text=ref_text,
        speaking_style=speaking_style,
        emotional_range=emotional_range_list,
    )

    return {"id": voice_id, "slug": slug}


@router.get("/voices")
async def list_voices_endpoint(
    engine: Optional[str] = None,
    voice_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    authorization: Optional[str] = Header(None),
):
    """
    List voices with optional filters.

    - **engine**: Filter by engine ('kokoro' or 'qwen')
    - **voice_type**: Filter by type ('clone', 'designed', 'preset', 'blend')
    - **limit**: Maximum number of results (default 100)
    - **offset**: Pagination offset
    """
    await verify_api_key(authorization)

    voices = await list_voices(
        limit=limit,
        offset=offset,
        engine=engine,
        voice_type=voice_type,
    )

    return {"voices": voices}


@router.get("/voices/{voice_id}")
async def get_voice_endpoint(
    voice_id: int,
    authorization: Optional[str] = Header(None),
):
    """Get a voice by ID."""
    await verify_api_key(authorization)

    voice = await get_voice(voice_id)
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")

    return voice


@router.put("/voices/{voice_id}")
async def update_voice_endpoint(
    voice_id: int,
    name: Optional[str] = Form(None),
    slug: Optional[str] = Form(None),
    voice_key: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    voice_description: Optional[str] = Form(None),
    ref_audio_path: Optional[str] = Form(None),
    ref_text: Optional[str] = Form(None),
    sample_audio_path: Optional[str] = Form(None),
    speaking_style: Optional[str] = Form(None),
    emotional_range: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
):
    """Update a voice by ID."""
    await verify_api_key(authorization)

    # Check voice exists
    voice = await get_voice(voice_id)
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")

    if voice.get("is_system"):
        raise HTTPException(status_code=403, detail="Cannot modify system voices")

    # Parse emotional_range JSON if provided
    emotional_range_list = None
    if emotional_range is not None:
        try:
            emotional_range_list = json.loads(emotional_range)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="emotional_range must be valid JSON")

    success = await update_voice(
        voice_id,
        name=name,
        slug=slug,
        voice_key=voice_key,
        language=language,
        voice_description=voice_description,
        ref_audio_path=ref_audio_path,
        ref_text=ref_text,
        sample_audio_path=sample_audio_path,
        speaking_style=speaking_style,
        emotional_range=emotional_range_list,
    )

    if not success:
        raise HTTPException(status_code=400, detail="No fields to update")

    return {"success": True}


@router.delete("/voices/{voice_id}")
async def delete_voice_endpoint(
    voice_id: int,
    authorization: Optional[str] = Header(None),
):
    """Delete a voice by ID. System voices cannot be deleted."""
    await verify_api_key(authorization)

    # Check voice exists
    voice = await get_voice(voice_id)
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")

    if voice.get("is_system"):
        raise HTTPException(status_code=403, detail="Cannot delete system voices")

    success = await delete_voice(voice_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete voice")

    return {"success": True}
