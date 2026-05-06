"""Sentence-boundary-aware text chunking for Sprecher narration.

Splits text into word-count-limited chunks while respecting sentence
boundaries. Oversized sentences are further split on punctuation.
"""
from __future__ import annotations

import re


def split_into_chunks(text: str, chunk_size: int = 200) -> list[str]:
    """Split *text* into chunks of at most *chunk_size* words.

    The splitter tries to break on sentence-ending punctuation (.!?) first.
    If a single sentence exceeds the limit it is broken on commas, semicolons,
    or colons as a fallback. If still no punctuation to split on, falls back
    to splitting on word boundaries.

    Args:
        text: The input text to split.
        chunk_size: Maximum number of words per chunk (default 200).

    Returns:
        A list of non-empty text chunks.
    """
    if not text or not text.strip():
        return []

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current_chunk = ""
    current_words = 0

    for sentence in sentences:
        sentence_words = len(sentence.split())

        if sentence_words > chunk_size:
            # Flush whatever is buffered first
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
                current_words = 0
            # Break the oversized sentence on punctuation
            parts = re.split(r"[,;:]", sentence)
            # If no punctuation found to split on, fall back to word boundaries
            if len(parts) == 1:
                # Split on word boundaries manually
                words = sentence.split()
                for i in range(0, len(words), chunk_size):
                    chunk_words = words[i:i + chunk_size]
                    chunk_text = " ".join(chunk_words)
                    chunks.append(chunk_text)
            else:
                for part in parts:
                    part_words = len(part.split())
                    if current_words + part_words <= chunk_size:
                        current_chunk += part + " "
                        current_words += part_words
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = part + " "
                        current_words = part_words
        else:
            if current_words + sentence_words <= chunk_size:
                current_chunk += sentence + " "
                current_words += sentence_words
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
                current_words = sentence_words

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return [c for c in chunks if c.strip()]
