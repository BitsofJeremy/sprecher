"""Kokoro ONNX TTS Engine implementation."""

import re
import hashlib
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf

import config
from core.tts.base import TTSEngine

# Lazy import to handle optional dependency
_Kokoro = None


def _get_kokoro():
    """Lazy load kokoro_onnx to handle optional dependency."""
    global _Kokoro
    if _Kokoro is None:
        from kokoro_onnx import Kokoro
        _Kokoro = Kokoro
    return _Kokoro


# Kokoro voice keys (54 voices from kokoro-hook)
KOKORO_VOICE_KEYS = {
    # Female voices (bf_*)
    "bf_isabella", "bf_emma", "bf_sarah", "bf_nicole", "bf_mia", "bf_rebecca",
    "bf_zoey", "bf_luna", "bf_ashley", "bf_ava", "bf_olivia", "bf_natasha",
    "bf_victoria", "bf_chloe", "bf_fem_v2", "bf_alto_v2", "bf_bella_v2",
    "bf_heatmap_v2", "bf_sarah_v2", "bf_heat_emma", "bf_heat_alto",
    "bf_heat_emma_v2", "bf_heat_alto_v2", "bf_heat_v2", "bf_heat_v3",
    # Female voices (af_*)
    "af_bella", "af_nicole", "af_sarah", "af_sky", "af_bridge",
    "af_heat_nicole", "af_heat_sarah", "af_heat_v2", "af_heat_v3",
    "af_heat_alto", "af_heat_andy", "af_sarah_v2", "af_bella_v2",
    "af_nicole_v2",
    # Male voices (am_*)
    "am_adam", "am_michael", "am_eric", "am_andrew", "am_robert",
    "am_david", "am_alex", "am_arthur", "am_liam", "am_peter",
    "am_william", "am_bridge", "am_heat_eric", "am_heat_andy",
}

# Voice metadata for API responses
VOICE_METADATA = {
    "bf_isabella": {"name": "Isabella", "gender": "female", "lang": "en-us", "description": "Warm, versatile female voice"},
    "bf_emma": {"name": "Emma", "gender": "female", "lang": "en-us", "description": "Bright, friendly female voice"},
    "bf_sarah": {"name": "Sarah", "gender": "female", "lang": "en-us", "description": "Professional female voice"},
    "bf_nicole": {"name": "Nicole", "gender": "female", "lang": "en-us", "description": "Calm, reassuring female voice"},
    "bf_mia": {"name": "Mia", "gender": "female", "lang": "en-us", "description": "Young, energetic female voice"},
    "bf_rebecca": {"name": "Rebecca", "gender": "female", "lang": "en-us", "description": "British female voice"},
    "bf_zoey": {"name": "Zoey", "gender": "female", "lang": "en-us", "description": "Casual American female"},
    "bf_luna": {"name": "Luna", "gender": "female", "lang": "en-us", "description": "Soft, gentle female voice"},
    "bf_ashley": {"name": "Ashley", "gender": "female", "lang": "en-us", "description": "Professional business female"},
    "bf_ava": {"name": "Ava", "gender": "female", "lang": "en-us", "description": "Expressive female voice"},
    "bf_olivia": {"name": "Olivia", "gender": "female", "lang": "en-us", "description": "Authoritative female voice"},
    "bf_natasha": {"name": "Natasha", "gender": "female", "lang": "en-us", "description": "Russian-influenced female"},
    "bf_victoria": {"name": "Victoria", "gender": "female", "lang": "en-us", "description": "Elegant female voice"},
    "bf_chloe": {"name": "Chloe", "gender": "female", "lang": "en-us", "description": "Youthful female voice"},
    "bf_fem_v2": {"name": "Female v2", "gender": "female", "lang": "en-us", "description": "Enhanced female voice"},
    "bf_alto_v2": {"name": "Alto v2", "gender": "female", "lang": "en-us", "description": "Lower female voice v2"},
    "bf_bella_v2": {"name": "Bella v2", "gender": "female", "lang": "en-us", "description": "Bella enhanced v2"},
    "bf_heatmap_v2": {"name": "Heatmap v2", "gender": "female", "lang": "en-us", "description": "Heatmap-based female v2"},
    "bf_sarah_v2": {"name": "Sarah v2", "gender": "female", "lang": "en-us", "description": "Sarah enhanced version"},
    "bf_heat_emma": {"name": "Heat Emma", "gender": "female", "lang": "en-us", "description": "Heatmap-based Emma"},
    "bf_heat_alto": {"name": "Heat Alto", "gender": "female", "lang": "en-us", "description": "Heatmap-based alto"},
    "bf_heat_emma_v2": {"name": "Heat Emma v2", "gender": "female", "lang": "en-us", "description": "Heatmap Emma v2"},
    "bf_heat_alto_v2": {"name": "Heat Alto v2", "gender": "female", "lang": "en-us", "description": "Heatmap alto v2"},
    "bf_heat_v2": {"name": "Heat v2", "gender": "female", "lang": "en-us", "description": "Heatmap female v2"},
    "bf_heat_v3": {"name": "Heat v3", "gender": "female", "lang": "en-us", "description": "Heatmap female alternate v3"},
    "af_bella": {"name": "Bella", "gender": "female", "lang": "en-us", "description": "Sweet female voice"},
    "af_nicole": {"name": "Nicole", "gender": "female", "lang": "en-us", "description": "Clear female voice"},
    "af_sarah": {"name": "Sarah", "gender": "female", "lang": "en-us", "description": "MidAtlantic female voice"},
    "af_sky": {"name": "Sky", "gender": "female", "lang": "en-us", "description": "Upbeat female voice"},
    "af_bridge": {"name": "Bridge", "gender": "female", "lang": "en-us", "description": "Neutral female bridge voice"},
    "af_heat_nicole": {"name": "Heat Nicole", "gender": "female", "lang": "en-us", "description": "Heatmap-based Nicole"},
    "af_heat_sarah": {"name": "Heat Sarah", "gender": "female", "lang": "en-us", "description": "Heatmap-based Sarah"},
    "af_heat_v2": {"name": "Heat v2 (af)", "gender": "female", "lang": "en-us", "description": "Heatmap female alternate v2"},
    "af_heat_v3": {"name": "Heat v3", "gender": "female", "lang": "en-us", "description": "Heatmap female v3"},
    "af_heat_alto": {"name": "Heat Alto (af)", "gender": "female", "lang": "en-us", "description": "Heatmap alto alternate"},
    "af_heat_andy": {"name": "Heat Andy (af)", "gender": "female", "lang": "en-us", "description": "Heatmap Andy alternate"},
    "af_sarah_v2": {"name": "Sarah v2 (af)", "gender": "female", "lang": "en-us", "description": "Sarah alternate v2"},
    "af_bella_v2": {"name": "Bella v2 (af)", "gender": "female", "lang": "en-us", "description": "Bella alternate v2"},
    "af_nicole_v2": {"name": "Nicole v2", "gender": "female", "lang": "en-us", "description": "Nicole enhanced v2"},
    "am_adam": {"name": "Adam", "gender": "male", "lang": "en-us", "description": "Deep male voice"},
    "am_michael": {"name": "Michael", "gender": "male", "lang": "en-us", "description": "Professional male voice"},
    "am_eric": {"name": "Eric", "gender": "male", "lang": "en-us", "description": "Casual male voice"},
    "am_andrew": {"name": "Andrew", "gender": "male", "lang": "en-us", "description": "Deep baritone male"},
    "am_robert": {"name": "Robert", "gender": "male", "lang": "en-us", "description": "Authoritative male voice"},
    "am_david": {"name": "David", "gender": "male", "lang": "en-us", "description": "British male voice"},
    "am_alex": {"name": "Alex", "gender": "male", "lang": "en-us", "description": "Versatile male voice"},
    "am_arthur": {"name": "Arthur", "gender": "male", "lang": "en-us", "description": "Mature male voice"},
    "am_liam": {"name": "Liam", "gender": "male", "lang": "en-us", "description": "Young adult male"},
    "am_peter": {"name": "Peter", "gender": "male", "lang": "en-us", "description": "Thoughtful male voice"},
    "am_william": {"name": "William", "gender": "male", "lang": "en-us", "description": "Formal male voice"},
    "am_bridge": {"name": "Bridge M", "gender": "male", "lang": "en-us", "description": "Neutral male bridge voice"},
    "am_heat_eric": {"name": "Heat Eric", "gender": "male", "lang": "en-us", "description": "Heatmap-based Eric"},
    "am_heat_andy": {"name": "Heat Andy", "gender": "male", "lang": "en-us", "description": "Heatmap-based Andy"},
}


def parse_blend_string(voice: str) -> Optional[list[tuple[str, float]]]:
    """
    Parse voice blend string like 'bf_emma(0.7)+af_sarah(0.3)'.

    Returns list of (voice_key, weight) tuples or None if not a blend.
    """
    if "+" not in voice and "(" not in voice:
        return None

    # Match patterns like "bf_emma(0.7)" or "bf_emma"
    pattern = r'([a-z_]+)\(([0-9.]+)\)|([a-z_]+)'
    parts = re.findall(pattern, voice.replace("+", " "))

    result = []
    for weight_str, explicit_weight, key in parts:
        key = key or weight_str
        if key:
            if explicit_weight:
                result.append((key, float(explicit_weight)))
            else:
                result.append((key, 1.0))

    return result if result else None


def get_voice_hash(voice_key: str) -> str:
    """Generate hash for voice key (used for model files)."""
    return hashlib.md5(voice_key.encode()).hexdigest()[:8]


class KokoroEngine(TTSEngine):
    """Kokoro ONNX TTS Engine."""

    _instance: Optional["KokoroEngine"] = None
    _kokoro: Optional[object] = None

    def __init__(self, model_dir: Path | None = None):
        """Initialize Kokoro engine with model directory."""
        self.model_dir = model_dir or config.KOKORO_MODEL_DIR
        self.model_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_engine(cls) -> "KokoroEngine":
        """Get singleton Kokoro engine instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_model(self) -> str:
        """Ensure model is downloaded, return model path."""
        KokoroClass = _get_kokoro()

        # Auto-download from release if model not found
        model_path = self.model_dir / "kokoro-v1.0.onnx"
        if not model_path.exists():
            from kokoro_onnx.utils import download_model
            download_model(str(self.model_dir))

        # Check for voices pack
        voices_path = self.model_dir / "voices.bin"
        if not voices_path.exists():
            from kokoro_onnx.utils import download_model
            download_model(str(self.model_dir), model="voices")

        return str(model_path)

    def _get_kokoro_instance(self):
        """Lazy load and cache Kokoro instance."""
        if self._kokoro is None:
            KokoroClass = _get_kokoro()
            model_path = self._ensure_model()
            voices_path = str(self.model_dir / "voices.bin")
            self._kokoro = KokoroClass(model_path, voices_path)
        return self._kokoro

    async def generate(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        lang: str = "en-us",
    ) -> tuple[np.ndarray, int]:
        """Generate audio from text."""
        kokoro = self._get_kokoro_instance()

        # Handle blend voices
        blend = parse_blend_string(voice)
        if blend and len(blend) > 1:
            # For blends, we generate each and mix
            samples_list = []
            sample_rate = 24000
            for vkey, weight in blend:
                if vkey in KOKORO_VOICE_KEYS:
                    aud, sr = kokoro.create(text, vkey, speed, lang)
                    samples_list.append((aud, sr, weight))

            if samples_list:
                # Mix weighted samples
                max_len = max(len(a) for a, _, _ in samples_list)
                mixed = np.zeros(max_len, dtype=np.float32)
                total_weight = sum(w for _, _, w in samples_list)

                for aud, sr, weight in samples_list:
                    if len(aud) < max_len:
                        aud = np.pad(aud, (0, max_len - len(aud)))
                    mixed += aud * (weight / total_weight)

                return mixed, 24000

        # Single voice generation
        if voice in KOKORO_VOICE_KEYS:
            return kokoro.create(text, voice, speed, lang)
        else:
            # Fallback to default voice
            return kokoro.create(text, "bf_isabella", speed, lang)

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
            # Save as WAV first, then convert to MP3 via ffmpeg
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
        """List available Kokoro voices with metadata."""
        voices = []
        for key, meta in VOICE_METADATA.items():
            voices.append({
                "key": key,
                "name": meta["name"],
                "gender": meta["gender"],
                "lang": meta["lang"],
                "description": meta["description"],
                "engine": "kokoro",
            })
        return voices

    def validate_voice(self, voice: str) -> bool:
        """Check if voice key is valid."""
        if voice in KOKORO_VOICE_KEYS:
            return True
        # Check if it's a valid blend string
        blend = parse_blend_string(voice)
        if blend:
            return all(vk in KOKORO_VOICE_KEYS for vk, _ in blend)
        return False


# Singleton accessor
def get_kokoro_engine() -> KokoroEngine:
    """Get the singleton Kokoro engine instance."""
    return KokoroEngine.get_engine()