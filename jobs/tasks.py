"""Job task handlers."""

from pathlib import Path
from typing import Optional

from jobs.models import TTSJob, NarrateJob, STTJob


async def run_tts_task(job: TTSJob) -> Path:
    """
    Run TTS generation task.

    Args:
        job: TTSJob with voice, text, output config

    Returns:
        Path to generated audio file
    """
    from core.tts.kokoro_engine import get_kokoro_engine

    engine = get_kokoro_engine()

    # Generate audio
    output_path = Path(job.output_path) if job.output_path else None
    if not output_path:
        from config import WORK_DIR
        import uuid
        output_path = WORK_DIR / "data" / "output" / f"{uuid.uuid4()}.{job.audio_format}"

    await engine.generate_to_file(
        text="",  # Will be set from job
        voice=job.voice_key,
        output_path=output_path,
        speed=job.speed,
        audio_format=job.audio_format,
    )

    return output_path


async def run_narrate_task(job: NarrateJob) -> Path:
    """
    Run document narration task.

    Args:
        job: NarrateJob with document and voice config

    Returns:
        Path to generated audio file
    """
    # Placeholder - will be implemented in Phase 1b
    raise NotImplementedError("Document narration not yet implemented")


async def run_stt_task(job: STTJob) -> dict:
    """
    Run STT transcription task.

    Args:
        job: STTJob with audio file path

    Returns:
        Dict with text, language, duration
    """
    from core.stt.whisper_engine import get_whisper_engine

    engine = get_whisper_engine()
    result = await engine.transcribe(job.source_path, language=job.language)

    return result