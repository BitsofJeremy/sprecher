"""TTS Engine Router - routes requests to appropriate TTS engine."""

from typing import Optional

from core.tts.base import TTSEngine
from core.tts.kokoro_engine import KokoroEngine, get_kokoro_engine

# For now, only Kokoro is implemented. Qwen will be added later.
AVAILABLE_ENGINES = {
    "kokoro": KokoroEngine,
}


class EngineRouter:
    """Routes TTS requests to appropriate engine."""

    _instances: dict[str, TTSEngine] = {}

    @classmethod
    def get_engine(cls, engine_name: str = "kokoro") -> TTSEngine:
        """Get engine instance by name."""
        if engine_name not in AVAILABLE_ENGINES:
            raise ValueError(f"Unknown engine: {engine_name}. Available: {list(AVAILABLE_ENGINES.keys())}")

        if engine_name not in cls._instances:
            engine_cls = AVAILABLE_ENGINES[engine_name]
            cls._instances[engine_name] = engine_cls.get_engine()

        return cls._instances[engine_name]

    @classmethod
    def list_engines(cls) -> list[dict]:
        """List available engines with capabilities."""
        engines = []
        for name, engine_cls in AVAILABLE_ENGINES.items():
            engine = engine_cls.get_engine()
            voices = engine.list_voices()
            engines.append({
                "id": name,
                "name": name.replace("_", " ").title(),
                "cloning": False,
                "design": False,
                "voices": len(voices),
            })
        return engines

    @classmethod
    def get_default_engine(cls) -> str:
        """Get default engine name from config."""
        from config import DEFAULT_ENGINE
        return DEFAULT_ENGINE


def get_engine_router() -> EngineRouter:
    """Get the engine router singleton."""
    return EngineRouter()