"""Qwen3-TTS Engine implementation (stub/lightweight CPU version).

This is a placeholder implementation for the Qwen3-TTS engine.
The actual Qwen3-TTS model requires GPU and will be integrated when
the full model is available.
"""

import os
from pathlib import Path
from typing import Optional

import numpy as np

import config
from core.tts.base import TTSEngine

# Lazy import for qwen3_tts
_Qwen3TTS = None


def _get_qwen3_tts():
    """Lazy load qwen3_tts to handle optional dependency."""
    global _Qwen3TTS
    if _Qwen3TTS is None:
        try:
            from qwen3_tts import Qwen3TTS
            _Qwen3TTS = Qwen3TTS
        except ImportError:
            return None
    return _Qwen3TTS


class QwenEngine(TTSEngine):
    """
    Qwen3-TTS Engine for voice cloning and design.

    This stub provides a lightweight CPU implementation that returns
    silence as a placeholder until the full GPU model is integrated.
    """

    _instance: Optional["QwenEngine"] = None
    _qwen: Optional[object] = None

    def __init__(self, model_dir: Path | None = None):
        """Initialize Qwen engine."""
        self.model_dir = model_dir or Path(
            os.environ.get("SPRECHER_QWEN_MODEL_DIR", "~/.claude/qwen-models")
        ).expanduser()
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self._available = False
        self._check_availability()

    def _check_availability(self) -> None:
        """Check if Qwen3-TTS is available."""
        QwenClass = _get_qwen3_tts()
        self._available = QwenClass is not None

    @classmethod
    def get_engine(cls) -> "QwenEngine":
        """Get singleton Qwen engine instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def is_available(self) -> bool:
        """Check if the engine is available."""
        return self._available

    async def generate(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        lang: str = "en-us",
    ) -> tuple[np.ndarray, int]:
        """
        Generate audio from text using Qwen3-TTS.

        For the stub implementation, returns silence.
        """
        if not self._available:
            # Return 1 second of silence as placeholder
            sample_rate = 24000
            return np.zeros(int(sample_rate * speed), dtype=np.float32), sample_rate

        qwen = self._get_qwen_instance()
        if qwen is None:
            sample_rate = 24000
            return np.zeros(int(sample_rate * speed), dtype=np.float32), sample_rate

        # Generate using Qwen3-TTS
        audio = qwen.generate(text, voice=voice, speed=speed, language=lang)
        return audio, 24000

    async def generate_to_file(
        self,
        text: str,
        voice: str,
        output_path: Path,
        speed: float = 1.0,
        lang: str = "en-us",
        audio_format: str = "wav",
    ) -> Path:
        """Generate audio and save to file."""
        import soundfile as sf

        samples, sample_rate = await self.generate(text, voice, speed, lang)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        sf.write(str(output_path), samples, sample_rate)
        return output_path

    def _get_qwen_instance(self):
        """Lazy load and cache Qwen instance."""
        if self._qwen is None:
            QwenClass = _get_qwen3_tts()
            if QwenClass is None:
                return None
            self._qwen = QwenClass(model_dir=str(self.model_dir))
        return self._qwen

    def list_voices(self) -> list[dict]:
        """
        List available Qwen voices.

        For the stub, returns placeholder voices for cloning/design.
        """
        return [
            {
                "key": "qwen_clone_default",
                "name": "Default Clone",
                "gender": "neutral",
                "lang": "en-us",
                "description": "Default voice for cloning from reference audio",
                "engine": "qwen",
                "voice_type": "clone",
            },
            {
                "key": "qwen_design_default",
                "name": "Default Design",
                "gender": "neutral",
                "lang": "en-us",
                "description": "Default voice for voice design",
                "engine": "qwen",
                "voice_type": "designed",
            },
        ]

    def validate_voice(self, voice: str) -> bool:
        """Check if voice key is valid."""
        valid_voices = [v["key"] for v in self.list_voices()]
        return voice in valid_voices


# Singleton accessor
def get_qwen_engine() -> QwenEngine:
    """Get the singleton Qwen engine instance."""
    return QwenEngine.get_engine()
