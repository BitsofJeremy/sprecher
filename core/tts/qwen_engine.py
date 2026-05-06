"""Qwen3-TTS Engine implementation using qwen-tts package.

Voice design with instruct-based voice characteristics.
Requires NVIDIA GPU with CUDA support.
"""

import os
import asyncio
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf
import torch

import config
from core.tts.base import TTSEngine

# Lazy import for qwen_tts
_Qwen3TTSModel = None


def _get_qwen_model():
    """Lazy load qwen_tts to handle optional dependency."""
    global _Qwen3TTSModel
    if _Qwen3TTSModel is None:
        try:
            from qwen_tts import Qwen3TTSModel
            _Qwen3TTSModel = Qwen3TTSModel
        except ImportError:
            return None
    return _Qwen3TTSModel


# Voice design presets - maps voice keys to instruct strings
VOICE_DESIGNS = {
    "qwen_warm": "warm and friendly female voice",
    "qwen_pro": "professional business tone",
    "qwen_narrator": "deep narrative voice for storytelling",
    "qwen_young": "young energetic person",
    "qwen_calm": "calm and soothing voice",
    "qwen_british": "British accent formal",
    "qwen_american": "casual American accent",
    "qwen_robot": "robotic synthetic voice",
    "qwen_whisper": "soft whisper",
    "qwen_excited": "very excited and enthusiastic",
}


class QwenEngine(TTSEngine):
    """
    Qwen3-TTS Engine for voice design and cloning.

    Uses Qwen3-TTS-12Hz-1.7B-VoiceDesign model with instruct-based
    voice characteristics.
    """

    _instance: Optional["QwenEngine"] = None
    _model: Optional[object] = None

    def __init__(self, model_dir: Path | None = None):
        """Initialize Qwen engine."""
        self.model_dir = model_dir or Path(
            os.environ.get("SPRECHER_QWEN_MODEL_DIR", "~/.cache/huggingface/hub/models--Qwen--Qwen3-TTS-12Hz-1.7B-VoiceDesign")
        ).expanduser()
        self.model_name = os.environ.get("SPRECHER_QWEN_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign")
        self._available = False
        self._load_model()

    def _load_model(self) -> None:
        """Load Qwen model if available."""
        QwenClass = _get_qwen_model()
        if QwenClass is None:
            self._available = False
            return

        try:
            # Check CUDA availability
            if not torch.cuda.is_available():
                print("QwenEngine: CUDA not available, marking as unavailable")
                self._available = False
                return

            # Load model to GPU
            self._model = QwenClass.from_pretrained(
                self.model_name,
                device_map="cuda:0",
                dtype=torch.bfloat16,
            )
            self._available = True
            print(f"QwenEngine: Model loaded successfully")
        except Exception as e:
            print(f"QwenEngine: Failed to load model: {e}")
            self._available = False

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
        Generate audio from text using Qwen voice design.
        """
        if not self._available or self._model is None:
            # Return 1 second of silence as placeholder
            sample_rate = 24000
            return np.zeros(int(sample_rate * speed), dtype=np.float32), sample_rate

        # Map voice key to instruct string
        instruct = self._get_instruct_for_voice(voice)

        # Map lang to Qwen format
        qwen_lang = self._map_language(lang)

        # Run inference in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        wavs, sr = await loop.run_in_executor(
            None,
            lambda: self._model.generate_voice_design(
                text=text,
                language=qwen_lang,
                instruct=instruct,
            )
        )

        # Resample if needed for speed adjustment
        audio = wavs[0]
        if speed != 1.0:
            # Simple speed adjustment via resampling
            target_length = int(len(audio) / speed)
            import scipy.signal
            audio = scipy.signal.resample(audio, target_length)

        return audio, sr

    def _get_instruct_for_voice(self, voice: str) -> str:
        """Map voice key to instruct string."""
        if voice in VOICE_DESIGNS:
            return VOICE_DESIGNS[voice]
        # Default instruct
        return "natural clear voice"

    def _map_language(self, lang: str) -> str:
        """Map lang code to Qwen language name."""
        lang_map = {
            "en-us": "English",
            "en": "English",
            "zh-cn": "Chinese",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "de": "German",
            "fr": "French",
            "ru": "Russian",
            "pt": "Portuguese",
            "es": "Spanish",
            "it": "Italian",
        }
        return lang_map.get(lang.lower(), "English")

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
        samples, sample_rate = await self.generate(text, voice, speed, lang)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if audio_format == "mp3":
            import tempfile
            import subprocess
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            sf.write(tmp_path, samples, sample_rate)
            try:
                subprocess.run([
                    "ffmpeg", "-y", "-i", tmp_path,
                    "-codec:a", "libmp3lame", "-b:a", config.AUDIO_BITRATE,
                    str(output_path)
                ], check=True, capture_output=True)
            finally:
                os.unlink(tmp_path)
        else:
            sf.write(str(output_path), samples, sample_rate)

        return output_path

    def list_voices(self) -> list[dict]:
        """List available Qwen voice designs."""
        voices = []
        for key, instruct in VOICE_DESIGNS.items():
            voices.append({
                "key": key,
                "name": key.replace("qwen_", "").title(),
                "gender": "neutral",
                "lang": "en-us",
                "description": instruct,
                "engine": "qwen",
                "voice_type": "designed",
            })
        return voices

    def validate_voice(self, voice: str) -> bool:
        """Check if voice key is valid."""
        return voice in VOICE_DESIGNS


# Singleton accessor
def get_qwen_engine() -> QwenEngine:
    """Get the singleton Qwen engine instance."""
    return QwenEngine.get_engine()
