"""Tests for narration modules (chunker and parsers)."""
import pytest
from pathlib import Path
import tempfile
import zipfile
import io

from core.narrate.chunker import split_into_chunks
from core.narrate.parsers import (
    parse_document,
    parse_txt,
    parse_epub,
    Chapter,
    _PARSERS,
)


class TestChunker:
    """Tests for split_into_chunks function."""

    def test_chunker_split_into_chunks_short_text(self):
        """Test splitting a short text that fits in one chunk."""
        text = "This is a short sentence. And another one."
        chunks = split_into_chunks(text, chunk_size=200)
        assert len(chunks) == 1
        assert "short sentence" in chunks[0]

    def test_chunker_split_into_chunks_multiple_sentences(self):
        """Test splitting text with multiple sentences."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = split_into_chunks(text, chunk_size=5)
        # Should split into multiple chunks
        assert len(chunks) >= 2

    def test_chunker_boundary_cases(self):
        """Test boundary cases at chunk_size limits."""
        # Text exactly at limit - should be 1 chunk
        words = "word " * 10  # 10 words
        chunks = split_into_chunks(words.strip(), chunk_size=10)
        assert len(chunks) == 1
        
        # Text over limit - should split into 2 chunks
        words = "word " * 15  # 15 words
        chunks = split_into_chunks(words.strip(), chunk_size=10)
        assert len(chunks) == 2

    def test_chunker_max_words(self):
        """Test that chunk_size limits words correctly."""
        # Create text with known word count
        text = " ".join([f"word{i}" for i in range(250)])
        chunks = split_into_chunks(text, chunk_size=100)
        for chunk in chunks:
            assert len(chunk.split()) <= 100

    def test_chunker_empty_text(self):
        """Test that empty text returns empty list."""
        assert split_into_chunks("") == []
        assert split_into_chunks("   ") == []
        assert split_into_chunks(None) == []  # type: ignore

    def test_chunker_oversize_sentence(self):
        """Test that oversized sentences are split on punctuation."""
        # Create a sentence with many words that exceeds chunk_size
        text = ", ".join([" ".join([f"word{j}" for j in range(50)]) for i in range(5)])
        chunks = split_into_chunks(text, chunk_size=100)
        # Should be split into multiple chunks
        assert len(chunks) >= 1
        for chunk in chunks:
            assert len(chunk.split()) <= 100

    def test_chunker_preserves_sentence_boundaries(self):
        """Test that sentence boundaries are preserved when possible."""
        text = "Hello. World! How are you? I'm fine."
        chunks = split_into_chunks(text, chunk_size=50)
        # All sentences should be preserved
        result_text = " ".join(chunks)
        assert "Hello." in result_text
        assert "World!" in result_text


class TestParserTxt:
    """Tests for parse_txt function."""

    def test_parser_parse_txt_simple(self, tmp_path):
        """Test parsing a simple text file."""
        txt_file = tmp_path / "test.txt"
        # Triple newlines separate chapters; double newlines within a chapter
        # parse_txt splits on \n{3,} - so "Chapter One\n\n...\n\n\nChapter Two" works
        txt_file.write_text(
            "Chapter One\n\n"
            "This is the first chapter content.\n"
            "It has multiple paragraphs.\n\n\n"
            "Chapter Two\n\n"
            "This is the second chapter."
        )
        
        chapters = parse_txt(txt_file)
        assert len(chapters) == 2
        assert chapters[0].title == "Chapter One"
        assert "first chapter" in chapters[0].text
        assert chapters[1].title == "Chapter Two"

    def test_parser_parse_txt_no_title(self, tmp_path):
        """Test parsing text file with no title markers."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("This is just some text.\n\nMore text without a title.")
        
        chapters = parse_txt(txt_file)
        assert len(chapters) >= 1

    def test_parser_parse_txt_chapter_word_count(self, tmp_path):
        """Test that Chapter.word_count property works."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Title\n\nThis is a test paragraph with some words.")
        
        chapters = parse_txt(txt_file)
        assert chapters[0].word_count == len("This is a test paragraph with some words.".split())


class TestParserEpub:
    """Tests for parse_epub function."""

    def test_parser_parse_epub_missing_file(self):
        """Test that missing EPUB file raises FileNotFoundError."""
        with pytest.raises((FileNotFoundError, RuntimeError)):
            parse_epub(Path("/nonexistent/file.epub"))

    def test_parser_parse_epub_invalid_file(self, tmp_path):
        """Test that invalid EPUB file raises error."""
        epub_file = tmp_path / "invalid.epub"
        epub_file.write_text("This is not a valid EPUB file.")
        
        # Should raise RuntimeError since no text could be extracted
        with pytest.raises(RuntimeError):
            parse_epub(epub_file)


class TestParserDispatch:
    """Tests for parse_document dispatcher."""

    def test_parser_parse_document_dispatch_txt(self, tmp_path):
        """Test that .txt files are dispatched to parse_txt."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Title\n\nContent")
        
        chapters = parse_document(txt_file)
        assert isinstance(chapters, list)

    def test_parser_parse_document_dispatch_text(self, tmp_path):
        """Test that .text files are dispatched to parse_txt."""
        text_file = tmp_path / "test.text"
        text_file.write_text("Title\n\nContent")
        
        chapters = parse_document(text_file)
        assert isinstance(chapters, list)

    def test_parser_parse_document_dispatch_unsupported(self, tmp_path):
        """Test that unsupported formats raise ValueError."""
        unsupported_file = tmp_path / "test.pdf"
        unsupported_file.write_text("dummy")
        
        with pytest.raises(ValueError) as exc_info:
            parse_document(unsupported_file)
        assert "Unsupported file format" in str(exc_info.value)
        assert ".pdf" in str(exc_info.value)

    def test_parser_dispatcher_has_required_formats(self):
        """Test that dispatcher has all required formats."""
        assert ".txt" in _PARSERS
        assert ".text" in _PARSERS
        assert ".epub" in _PARSERS
