"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint - no auth required."""
    return {
        "status": "ok",
        "engines": ["kokoro", "qwen", "whisper"]
    }