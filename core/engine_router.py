"""TTS Engine Router - routes requests to appropriate TTS engine."""

from typing import Optional

from core.tts.base import TTSEngine
from core.tts.kokoro_engine import KokoroEngine, get_kokoro_engine
from core.tts.qwen_engine import QwenEngine, get_qwen_engine
from core.tts.minimax_engine import MiniMaxEngine, get_minimax_engine

# Available TTS engines
AVAILABLE_ENGINES = {
    "kokoro": KokoroEngine,
    "qwen": QwenEngine,
    "minimax": MiniMaxEngine,
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
            # Engine capabilities
            if name == "kokoro":
                capabilities = {"cloning": False, "design": False}
            elif name == "qwen":
                capabilities = {"cloning": False, "design": True}
            elif name == "minimax":
                capabilities = {"cloning": True, "design": False}
            else:
                capabilities = {"cloning": False, "design": False}
            engines.append({
                "id": name,
                "name": name.replace("_", " ").title(),
                "cloning": capabilities["cloning"],
                "design": capabilities["design"],
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