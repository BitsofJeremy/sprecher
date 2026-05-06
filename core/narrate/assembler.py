"""Audio post-processing and assembly for Sprecher narration.

Handles silence trimming, normalisation, and concatenation of WAV chunks
into a single output file (MP3, M4A, or WAV).
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import numpy as np
from pydub import AudioSegment
from pydub.effects import normalize
from pydub.silence import detect_leading_silence

logger = logging.getLogger(__name__)


def trim_silence(
    audio: AudioSegment,
    threshold: int = -45,
    chunk_size: int = 1000,
) -> AudioSegment:
    """Trim leading and trailing silence from *audio*.

    Args:
        audio: The AudioSegment to trim.
        threshold: Silence threshold in dBFS (default -45).
        chunk_size: Detection granularity in ms (default 1000).

    Returns:
        A new AudioSegment with silence removed from both ends.
    """
    leading = detect_leading_silence(audio, silence_threshold=threshold, chunk_size=chunk_size)
    trimmed = audio[leading:]
    trailing = detect_leading_silence(trimmed.reverse(), silence_threshold=threshold, chunk_size=chunk_size)
    if trailing:
        trimmed = trimmed[:-trailing]
    return trimmed


def post_process_audio(audio: AudioSegment) -> AudioSegment:
    """Trim silence and normalise *audio* to -3 dBFS peak.

    Args:
        audio: The AudioSegment to process.

    Returns:
        Processed AudioSegment.
    """
    audio = trim_silence(audio)
    audio = normalize(audio, headroom=3.0)
    return audio


def assemble_chunks(
    wav_files: list[Path],
    output_path: Path,
    audio_format: str = "mp3",
    bitrate: str = "128k",
    do_post_process: bool = True,
) -> bool:
    """Concatenate WAV chunk files into a single output file.

    Each chunk is individually post-processed (if enabled) before
    concatenation, and the final combined audio receives a second
    post-processing pass.

    Args:
        wav_files: Ordered list of WAV file paths to concatenate.
        output_path: Destination path for the assembled file.
        audio_format: Output format -- ``mp3``, ``m4a``, or ``wav``.
        bitrate: Audio bitrate for lossy formats (default ``128k``).
        do_post_process: Whether to apply silence trimming + normalisation.

    Returns:
        ``True`` if assembly succeeded, ``False`` if no audio was produced.
    """
    if not wav_files:
        return False

    combined = AudioSegment.empty()
    for wf in wav_files:
        try:
            chunk_audio = AudioSegment.from_wav(str(wf))
            if do_post_process:
                raw_samples = np.array(chunk_audio.get_array_of_samples(), dtype=np.float32)
                if len(raw_samples) > 0:
                    raw_peak = np.max(np.abs(raw_samples)) / (2 ** (chunk_audio.sample_width * 8 - 1))
                    logger.debug("Assembler: chunk %s raw peak: %.4f", wf.name, raw_peak)
                chunk_audio = post_process_audio(chunk_audio)
            combined += chunk_audio
        except Exception as e:
            logger.warning("Failed to process chunk %s: %s", wf, e)
            continue

    if len(combined) == 0:
        return False

    if do_post_process:
        combined = post_process_audio(combined)

    # pydub uses "mp4" as the format name for m4a containers
    fmt = "mp4" if audio_format == "m4a" else audio_format
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.export(str(output_path), format=fmt, bitrate=bitrate)
    return True


def embed_metadata(
    audio_path: Path,
    title: str = "",
    author: str = "",
    album: str = "",
    genre: str = "Audiobook",
    cover_path: str | Path | None = None,
    track_number: int | None = None,
) -> bool:
    """Embed metadata tags into an audio file using ffmpeg.

    Args:
        audio_path: Path to the audio file.
        title: Title tag.
        author: Author name (written to Artist tag).
        album: Album tag (typically the book title).
        genre: Genre tag (default "Audiobook").
        cover_path: Optional path to a JPEG or PNG cover image.
        track_number: Optional track number.

    Returns:
        ``True`` if metadata was embedded successfully.
    """
    import logging
    _log = logging.getLogger(__name__)

    if not audio_path.exists():
        return False

    # Build ffmpeg metadata command
    output_path = audio_path.with_suffix(audio_path.suffix + ".tmp")
    cmd = ["ffmpeg", "-y", "-i", str(audio_path)]

    # Add metadata
    if title:
        cmd.extend(["-metadata", f"title={title}"])
    if author:
        cmd.extend(["-metadata", f"artist={author}"])
    if album:
        cmd.extend(["-metadata", f"album={album}"])
    if genre:
        cmd.extend(["-metadata", f"genre={genre}"])
    if track_number is not None:
        cmd.extend(["-metadata", f"track={track_number}"])

    # Add cover art
    if cover_path:
        cp = Path(cover_path)
        if cp.exists():
            cmd.extend(["-i", str(cp), "-map", "0:a", "-map", "1:v"])
            cmd.extend(["-c:v", "copy"])
            if cp.suffix.lower() in (".jpg", ".jpeg"):
                cmd.extend(["-metadata", "comment=Cover (JPEG)"])
            elif cp.suffix.lower() == ".png":
                cmd.extend(["-metadata", "comment=Cover (PNG)"])

    cmd.extend(["-codec", "copy", str(output_path)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0 and output_path.exists():
            output_path.replace(audio_path)
            return True
        else:
            _log.warning("ffmpeg metadata embed failed: %s", result.stderr[:500])
            if output_path.exists():
                output_path.unlink()
            return False
    except Exception as e:
        _log.warning("Failed to embed metadata: %s", e)
        if output_path.exists():
            output_path.unlink()
        return False
