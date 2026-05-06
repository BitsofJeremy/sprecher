"""Job data classes."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class JobStatus(str, Enum):
    """Job status enum."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobScope(str, Enum):
    """Job scope enum."""
    TTS = "tts"
    STT = "stt"
    NARRATE = "narrate"


@dataclass
class TTSJob:
    """TTS Job data."""
    id: Optional[int] = None
    title: str = ""
    engine: str = "kokoro"
    voice_id: Optional[int] = None
    voice_key: str = "bf_isabella"
    status: JobStatus = JobStatus.QUEUED
    scope: JobScope = JobScope.TTS
    source_path: str = ""
    output_path: Optional[str] = None
    audio_format: str = "wav"
    speed: float = 1.0
    total_chunks: int = 0
    completed_chunks: int = 0
    progress: int = 0
    error_message: Optional[str] = None
    author: str = ""
    cover_path: str = ""
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class NarrateJob:
    """Narrate Job data (document narration)."""
    id: Optional[int] = None
    title: str = ""
    engine: str = "kokoro"
    voice_id: Optional[int] = None
    voice_key: str = "bf_isabella"
    status: JobStatus = JobStatus.QUEUED
    scope: JobScope = JobScope.NARRATE
    source_path: str = ""
    output_path: Optional[str] = None
    audio_format: str = "mp3"
    speed: float = 1.0
    total_chunks: int = 0
    completed_chunks: int = 0
    progress: int = 0
    error_message: Optional[str] = None
    author: str = ""
    cover_path: str = ""
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class STTJob:
    """STT Job data."""
    id: Optional[int] = None
    title: str = "STT Transcription"
    engine: str = "whisper"
    status: JobStatus = JobStatus.QUEUED
    scope: JobScope = JobScope.STT
    source_path: str = ""
    output_path: Optional[str] = None
    language: Optional[str] = None
    progress: int = 0
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None