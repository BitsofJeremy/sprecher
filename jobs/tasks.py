"""Job task handlers."""

import logging
import uuid
from pathlib import Path

from jobs.models import TTSJob, NarrateJob, STTJob
import config

logger = logging.getLogger(__name__)


async def tts_task(job: TTSJob) -> Path:
    """
    Run TTS generation task.

    Args:
        job: TTSJob with voice, text, output config

    Returns:
        Path to generated audio file
    """
    # Get the appropriate engine
    if job.engine == "kokoro":
        from core.tts.kokoro_engine import get_kokoro_engine
        engine = get_kokoro_engine()
    elif job.engine == "qwen":
        from core.tts.qwen_engine import get_qwen_engine
        engine = get_qwen_engine()
    else:
        raise ValueError(f"Unknown engine: {job.engine}")

    # Generate output path if not set
    output_path = Path(job.output_path) if job.output_path else None
    if not output_path:
        output_path = config.WORK_DIR / "data" / "output" / f"{uuid.uuid4().hex[:12]}.{job.audio_format}"

    await engine.generate_to_file(
        text=job.source_path,
        voice=job.voice_key,
        output_path=output_path,
        speed=job.speed,
        audio_format=job.audio_format,
    )

    return output_path


async def run_tts_task(job: TTSJob) -> Path:
    """
    Run TTS generation task (wrapper for backward compatibility).

    Args:
        job: TTSJob with voice, text, output config

    Returns:
        Path to generated audio file
    """
    return await tts_task(job)


async def _process_stt_job(job: "STTJob") -> dict:
    """Internal function to process an STT job."""
    from core.stt.whisper_engine import get_whisper_engine
    from db.jobs import complete_job, fail_job, update_job

    try:
        await update_job(job.id, status="running", progress=10)

        engine = get_whisper_engine()
        result = await engine.transcribe(job.source_path, language=job.language)

        await complete_job(job.id, result["text"])
        await update_job(job.id, progress=100)

        return result

    except Exception as e:
        await fail_job(job.id, str(e))
        raise


async def _process_narrate_job(job: "NarrateJob") -> Path:
    """Internal function to process a narration job."""
    from core.narrate.parsers import parse_document
    from core.narrate.chunker import split_into_chunks
    from core.narrate.assembler import assemble_chunks, embed_metadata
    from db.jobs import complete_job, fail_job, update_job

    source_path = Path(job.source_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Source document not found: {source_path}")

    try:
        await update_job(job.id, status="running", progress=0)

        # Parse document into chapters
        chapters = parse_document(source_path)
        if not chapters:
            raise ValueError("No chapters could be extracted from document")

        total_chunks = sum(len(split_into_chunks(ch.text)) for ch in chapters)
        await update_job(job.id, total_chunks=total_chunks, progress=0)

        # Get TTS engine
        if job.engine == "kokoro":
            from core.tts.kokoro_engine import get_kokoro_engine
            engine = get_kokoro_engine()
        elif job.engine == "qwen":
            from core.tts.qwen_engine import get_qwen_engine
            engine = get_qwen_engine()
        else:
            raise ValueError(f"Unknown engine: {job.engine}")

        # Generate audio for each chunk
        wav_files = []
        chunk_idx = 0
        completed = 0

        for chapter in chapters:
            chunks = split_into_chunks(chapter.text)
            for text_chunk in chunks:
                chunk_output = config.WORK_DIR / "data" / "chunks" / f"chunk_{job.id}_{chunk_idx:04d}.wav"
                chunk_output.parent.mkdir(parents=True, exist_ok=True)

                await engine.generate_to_file(
                    text=text_chunk,
                    voice=job.voice_key,
                    output_path=chunk_output,
                    speed=job.speed,
                    audio_format="wav",
                )

                wav_files.append(chunk_output)
                chunk_idx += 1
                completed += 1

                if total_chunks > 0:
                    progress = int((completed / total_chunks) * 100)
                    await update_job(job.id, progress=progress, completed_chunks=completed)

        if not wav_files:
            raise ValueError("No audio chunks were generated")

        output_path = Path(job.output_path) if job.output_path else \
                      config.WORK_DIR / "data" / "output" / f"narrate_{job.id}.{job.audio_format}"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        success = assemble_chunks(
            wav_files,
            output_path,
            audio_format=job.audio_format,
            do_post_process=True,
        )

        if not success:
            raise RuntimeError("Failed to assemble audio chunks")

        if job.cover_path and Path(job.cover_path).exists():
            embed_metadata(
                audio_path=output_path,
                title=job.title,
                author=job.author,
                album=job.title,
                cover_path=job.cover_path,
            )

        # Clean up chunk files
        for wf in wav_files:
            wf.unlink(missing_ok=True)

        await complete_job(job.id, str(output_path))
        return output_path

    except Exception as e:
        await fail_job(job.id, str(e))
        raise
