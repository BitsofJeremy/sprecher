"""Qwen3-TTS Engine implementation using qwen-tts package.

Supports both voice design (instruct strings) and voice cloning (reference audio).
Voice cloning uses Qwen3-TTS Base model + create_voice_clone_prompt API.
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
_QwenCloneModel = None  # Separate Base model for cloning


def _get_qwen_model(for_clone: bool = False):
    """Lazy load qwen_tts to handle optional dependency.

    Args:
        for_clone: If True, load the Base model (for cloning).
                   If False, load the VoiceDesign model (for design).
    """
    global _Qwen3TTSModel, _QwenCloneModel
    if for_clone:
        if _QwenCloneModel is None:
            try:
                from qwen_tts import Qwen3TTSModel
                _QwenCloneModel = Qwen3TTSModel
            except ImportError:
                return None
        return _QwenCloneModel
    else:
        if _Qwen3TTSModel is None:
            try:
                from qwen_tts import Qwen3TTSModel
                _Qwen3TTSModel = Qwen3TTSModel
            except ImportError:
                return None
        return _Qwen3TTSModel
    return None


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

    Voice design uses Qwen3-TTS-12Hz-1.7B-VoiceDesign model with instruct-based
    voice characteristics.

    Voice cloning uses Qwen3-TTS-12Hz-1.7B-Base model with reference audio
    via create_voice_clone_prompt() + generate_voice_clone().
    """

    _instance: Optional["QwenEngine"] = None
    _design_model: Optional[object] = None
    _clone_model: Optional[object] = None

    def __init__(self, model_dir: Path | None = None):
        """Initialize Qwen engine."""
        self.model_name_design = os.environ.get(
            "SPRECHER_QWEN_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
        )
        self.model_name_clone = os.environ.get(
            "SPRECHER_QWEN_CLONE_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
        )
        self._available = False
        self._clone_available = False
        self._load_models()

    def _load_models(self) -> None:
        """Load both design and clone models if available."""
        # Check CUDA availability once
        if not torch.cuda.is_available():
            print("QwenEngine: CUDA not available, marking as unavailable")
            self._available = False
            self._clone_available = False
            return

        # Load design model
        DesignModel = _get_qwen_model(for_clone=False)
        if DesignModel is None:
            print("QwenEngine: qwen_tts not installed")
            self._available = False
        else:
            try:
                self._design_model = DesignModel.from_pretrained(
                    self.model_name_design,
                    device_map="cuda:0",
                    dtype=torch.bfloat16,
                )
                self._available = True
                print("QwenEngine: Design model loaded successfully")
            except Exception as e:
                print(f"QwenEngine: Failed to load design model: {e}")
                self._available = False

        # Load clone model (Base model)
        CloneModel = _get_qwen_model(for_clone=True)
        if CloneModel is None:
            print("QwenEngine: qwen_tts not installed for clone model")
            self._clone_available = False
        else:
            try:
                self._clone_model = CloneModel.from_pretrained(
                    self.model_name_clone,
                    device_map="cuda:0",
                    dtype=torch.bfloat16,
                )
                self._clone_available = True
                print("QwenEngine: Clone model loaded successfully")
            except Exception as e:
                print(f"QwenEngine: Failed to load clone model: {e}")
                self._clone_available = False

    @classmethod
    def get_engine(cls) -> "QwenEngine":
        """Get singleton Qwen engine instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def is_available(self) -> bool:
        """Check if the engine is available (design OR clone)."""
        return self._available or self._clone_available

    def is_clone_available(self) -> bool:
        """Check if voice cloning is available."""
        return self._clone_available

    async def generate(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        lang: str = "en-us",
    ) -> tuple[np.ndarray, int]:
        """Generate audio from text using Qwen voice design."""
        if not self._available or self._design_model is None:
            sample_rate = 24000
            return np.zeros(int(sample_rate), dtype=np.float32), sample_rate

        instruct = self._get_instruct_for_voice(voice)
        qwen_lang = self._map_language(lang)

        loop = asyncio.get_event_loop()
        wavs, sr = await loop.run_in_executor(
            None,
            lambda: self._design_model.generate_voice_design(
                text=text,
                language=qwen_lang,
                instruct=instruct,
            )
        )

        audio = wavs[0]
        if speed != 1.0:
            import scipy.signal
            target_length = int(len(audio) / speed)
            audio = scipy.signal.resample(audio, target_length)

        return audio, sr

    async def generate_clone(
        self,
        text: str,
        ref_audio_path: str | Path,
        ref_text: str,
        language: str = "English",
    ) -> tuple[np.ndarray, int]:
        """Generate speech by cloning a reference voice.

        Args:
            text: The text to synthesise.
            ref_audio_path: Path to the reference WAV file.
            ref_text: Transcript of the reference audio.
            language: Language tag.

        Returns:
            Tuple of (wav_array, sample_rate).
        """
        if not self._clone_available or self._clone_model is None:
            sample_rate = 24000
            return np.zeros(int(sample_rate), dtype=np.float32), sample_rate

        loop = asyncio.get_event_loop()
        wavs, sr = await loop.run_in_executor(
            None,
            lambda: self._do_clone(text, str(ref_audio_path), ref_text, language),
        )
        return wavs[0], sr

    def _do_clone(
        self,
        text: str,
        ref_audio_path: str,
        ref_text: str,
        language: str,
    ) -> tuple:
        """Synchronous clone implementation (runs in thread pool)."""
        voice_clone_prompt = self._clone_model.create_voice_clone_prompt(
            ref_audio=ref_audio_path,
            ref_text=ref_text,
        )
        wavs, sr = self._clone_model.generate_voice_clone(
            text=text,
            language=language,
            voice_clone_prompt=voice_clone_prompt,
        )
        return wavs, sr

    async def generate_to_file(
        self,
        text: str,
        voice: str,
        output_path: Path,
        speed: float = 1.0,
        lang: str = "en-us",
        audio_format: str = "wav",
        ref_audio_path: str | None = None,
        ref_text: str | None = None,
    ) -> Path:
        """Generate audio and save to file.

        If ref_audio_path and ref_text are provided, uses voice cloning.
        Otherwise uses voice design with the voice key as instruct reference.
        """
        # Determine mode: clone if ref_audio_path provided, else design
        if ref_audio_path and ref_text and self._clone_available:
            samples, sample_rate = await self.generate_clone(
                text, ref_audio_path, ref_text,
                language=self._map_language(lang),
            )
        elif self._available:
            samples, sample_rate = await self.generate(text, voice, speed, lang)
        else:
            sample_rate = 24000
            samples = np.zeros(int(sample_rate), dtype=np.float32)

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
                    str(output_path),
                ], check=True, capture_output=True)
            finally:
                os.unlink(tmp_path)
        else:
            sf.write(str(output_path), samples, sample_rate)

        return output_path

    def _get_instruct_for_voice(self, voice: str) -> str:
        """Map voice key to instruct string."""
        if voice in VOICE_DESIGNS:
            return VOICE_DESIGNS[voice]
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
        """Check if voice key is valid (design or clone)."""
        if voice in VOICE_DESIGNS:
            return True
        # Clone voices start with qwen_clone_ or just accept any non-design key
        # (DB voices are validated separately in the TTS endpoint)
        return False


# Singleton accessor
def get_qwen_engine() -> QwenEngine:
    """Get the singleton Qwen engine instance."""
    return QwenEngine.get_engine()
