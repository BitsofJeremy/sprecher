"""API Router aggregator."""

from fastapi import APIRouter

from api.health import router as health_router
from api.tts import router as tts_router
from api.stt import router as stt_router

api_router = APIRouter(prefix="/api")

# Include all API sub-routers
api_router.include_router(health_router)
api_router.include_router(tts_router)
api_router.include_router(stt_router)