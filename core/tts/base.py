"""Abstract base class for TTS engines."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import numpy as np


class TTSEngine(ABC):
    """Abstract base class for TTS engines."""

    @abstractmethod
    async def generate(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        lang: str = "en-us",
    ) -> tuple[np.ndarray, int]:
        """
        Generate audio from text.

        Args:
            text: Text to synthesize
            voice: Voice key or blend string
            speed: Speech speed (1.0 = normal)
            lang: Language code

        Returns:
            Tuple of (audio_samples, sample_rate)
        """

    @abstractmethod
    async def generate_to_file(
        self,
        text: str,
        voice: str,
        output_path: Path,
        speed: float = 1.0,
        lang: str = "en-us",
        audio_format: str = "wav",
    ) -> Path:
        """
        Generate audio and save to file.

        Args:
            text: Text to synthesize
            voice: Voice key or blend string
            output_path: Output file path
            speed: Speech speed
            lang: Language code
            audio_format: Output format (wav, mp3)

        Returns:
            Path to generated file
        """

    @abstractmethod
    def list_voices(self) -> list[dict]:
        """List available voices with metadata."""

    @abstractmethod
    def validate_voice(self, voice: str) -> bool:
        """Check if voice key is valid."""