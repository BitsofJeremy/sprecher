"""Whisper STT Engine."""

import whisper
from pathlib import Path
from typing import Optional

import numpy as np


class WhisperEngine:
    """Whisper STT Engine for speech-to-text transcription."""

    _instance: Optional["WhisperEngine"] = None
    _model: Optional[whisper.Whisper] = None

    def __init__(self, model_size: str = "base"):
        """Initialize Whisper engine with model size."""
        self.model_size = model_size
        self._audio_buffer: list[np.ndarray] = []

    @classmethod
    def get_engine(cls, model_size: str = "base") -> "WhisperEngine":
        """Get singleton Whisper engine instance."""
        if cls._instance is None or cls._instance.model_size != model_size:
            cls._instance = cls(model_size)
        return cls._instance

    def _get_model(self) -> whisper.Whisper:
        """Lazy load and cache Whisper model."""
        if self._model is None:
            self._model = whisper.load_model(self.model_size)
        return self._model

    async def transcribe(
        self,
        audio_path: Path | str,
        language: str | None = None,
    ) -> dict:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to audio file
            language: Language code (auto-detect if None)

        Returns:
            Dict with 'text', 'language', 'duration' keys
        """
        model = self._get_model()

        if isinstance(audio_path, str):
            audio_path = Path(audio_path)

        # Load and resample audio if needed
        import torch
        audio = whisper.load_audio(str(audio_path))
        audio = whisper.pad_or_trim(audio)

        # Make log-Mel spectrogram
        mel = whisper.log_mel_spectrogram(audio, n_mels=model.dims.n_mels).to(model.device)

        # Decode
        options = whisper.DecodingOptions(language=language, fp16=torch.cuda.is_available())
        result = whisper.decode(model, mel, options)

        return {
            "text": result.text,
            "language": result.language,
            "duration": len(audio) / whisper.SAMPLE_RATE,
        }

    async def transcribe_from_samples(
        self,
        samples: np.ndarray,
        sample_rate: int,
        language: str | None = None,
    ) -> dict:
        """
        Transcribe from audio samples.

        Args:
            samples: Audio samples as numpy array
            sample_rate: Sample rate
            language: Language code (auto-detect if None)

        Returns:
            Dict with 'text', 'language', 'duration' keys
        """
        model = self._get_model()

        # Resample to 16kHz if needed
        if sample_rate != whisper.SAMPLE_RATE:
            import torch
            target_samples = self._resample(samples, sample_rate, whisper.SAMPLE_RATE)
        else:
            target_samples = samples

        # Pad or trim
        target_samples = whisper.pad_or_trim(target_samples)

        # Make log-Mel spectrogram
        mel = whisper.log_mel_spectrogram(target_samples, n_mels=model.dims.n_mels).to(model.device)

        # Decode
        options = whisper.DecodingOptions(language=language, fp16=torch.cuda.is_available())
        result = whisper.decode(model, mel, options)

        return {
            "text": result.text,
            "language": result.language,
            "duration": len(target_samples) / whisper.SAMPLE_RATE,
        }

    def _resample(self, samples: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Simple resampling using linear interpolation."""
        duration = len(samples) / orig_sr
        target_len = int(duration * target_sr)
        indices = np.linspace(0, len(samples) - 1, target_len)
        return np.interp(indices, np.arange(len(samples)), samples).astype(np.float32)


# Singleton accessor
def get_whisper_engine(model_size: str = "base") -> WhisperEngine:
    """Get the singleton Whisper engine instance."""
    return WhisperEngine.get_engine(model_size)