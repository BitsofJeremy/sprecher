"""MiniMax TTS Engine — supports voice cloning via reference audio."""

import os
import re
import uuid
import asyncio
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf
import httpx

import config
from core.tts.base import TTSEngine

MINIMAX_API_BASE = "https://api.minimaxi.chat/v1"


def _get_minimax_key() -> str:
    """Get MiniMax API key from config."""
    return getattr(config, "MINIMAX_API_KEY", os.environ.get("MINIMAX_API_KEY", ""))


class MiniMaxEngine(TTSEngine):
    """MiniMax TTS Engine with voice cloning support."""

    _instance: Optional["MiniMaxEngine"] = None

    def __init__(self):
        self.available = bool(_get_minimax_key())

    @classmethod
    def get_engine(cls) -> "MiniMaxEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def is_available(self) -> bool:
        return self.available

    async def generate(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        lang: str = "en-us",
    ) -> tuple[np.ndarray, int]:
        """Generate audio via MiniMax T2A API."""
        api_key = _get_minimax_key()
        if not api_key:
            return np.zeros(24000, dtype=np.float32), 24000

        # Map lang to MiniMax format
        lang_map = {"en-us": "English", "en": "English", "zh-cn": "Chinese"}
        mm_lang = lang_map.get(lang.lower(), "English")

        # Build voice_setting
        voice_setting: dict = {"voice_id": voice}

        # If voice looks like a reference audio path (local file), use reference_audio_url
        # Ephergent voices: voice keys are like "ephergent_pixel", "ephergent_clive", etc.
        # They store the reference .wav at a known path on the server
        if voice.startswith("ephergent_") or voice.startswith("/"):
            ref_path = voice if voice.startswith("/") else None
            if ref_path and Path(ref_path).exists():
                voice_setting = {
                    "voice_id": "fixed-voice-id",
                    "reference_audio_url": f"file://{ref_path}",
                }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{MINIMAX_API_BASE}/t2a_v2",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "speech-2.8-hd",
                    "text": text,
                    "stream": False,
                    "voice_setting": voice_setting,
                    "language_boost": mm_lang,
                },
            )

        if resp.status_code != 200:
            return np.zeros(24000, dtype=np.float32), 24000

        audio_bytes = resp.content
        import tempfile
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            data, sr = sf.read(tmp_path, dtype="float32")
            if len(data.shape) > 1:
                data = data.mean(axis=1)
            return data, sr
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)

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
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if audio_format == "mp3":
            import tempfile, subprocess
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            sf.write(tmp_path, samples, sample_rate)
            try:
                subprocess.run([
                    "ffmpeg", "-y", "-i", tmp_path,
                    "-codec:a", "libmp3lame", "-b:a", "128k",
                    str(output_path),
                ], check=True, capture_output=True)
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        else:
            sf.write(str(output_path), samples, sample_rate)

        return output_path

    def list_voices(self) -> list[dict]:
        """MiniMax has no fixed voice list — returns the custom clone voices from DB."""
        return []

    def validate_voice(self, voice: str) -> bool:
        """Accept any voice_key that looks like a MiniMax voice ID."""
        return bool(re.match(r"^[\w-]{20,}$", voice))


def get_minimax_engine() -> MiniMaxEngine:
    return MiniMaxEngine.get_engine()
