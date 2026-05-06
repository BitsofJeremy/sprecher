"""Tests for Kokoro TTS Engine."""
import pytest
from unittest.mock import patch, MagicMock
import numpy as np

from core.tts.kokoro_engine import (
    parse_blend_string,
    get_voice_hash,
    KokoroEngine,
    KOKORO_VOICE_KEYS,
    VOICE_METADATA,
)


class TestParseBlendString:
    """Tests for parse_blend_string function."""

    def test_parse_blend_string_valid_two_voices(self):
        """Test parsing a valid blend string with two voices."""
        result = parse_blend_string("bf_emma(0.7)+af_sarah(0.3)")
        assert result is not None
        assert len(result) == 2
        assert result[0] == ("bf_emma", 0.7)
        assert result[1] == ("af_sarah", 0.3)

    def test_parse_blend_string_valid_single_voice_with_weight(self):
        """Test parsing a single voice with explicit weight."""
        result = parse_blend_string("bf_emma(1.0)")
        assert result is not None
        assert len(result) == 1
        assert result[0] == ("bf_emma", 1.0)

    def test_parse_blend_string_valid_single_voice_no_weight(self):
        """Test parsing a single voice without weight (no blend)."""
        result = parse_blend_string("bf_emma")
        assert result is None

    def test_parse_blend_string_valid_multiple_voices(self):
        """Test parsing a blend string with three voices."""
        result = parse_blend_string("bf_emma(0.5)+af_sarah(0.3)+am_adam(0.2)")
        assert result is not None
        assert len(result) == 3
        assert result[0] == ("bf_emma", 0.5)
        assert result[1] == ("af_sarah", 0.3)
        assert result[2] == ("am_adam", 0.2)

    def test_parse_blend_string_invalid_no_blend(self):
        """Test that non-blend strings return None."""
        assert parse_blend_string("bf_emma") is None
        assert parse_blend_string("invalid_voice") is None

    def test_parse_blend_string_invalid_random_string(self):
        """Test that random strings return None."""
        assert parse_blend_string("not a voice at all") is None
        assert parse_blend_string("hello world") is None


class TestVoiceHash:
    """Tests for get_voice_hash function."""

    def test_voice_hash_generation(self):
        """Test that voice hash is deterministic."""
        hash1 = get_voice_hash("bf_emma")
        hash2 = get_voice_hash("bf_emma")
        assert hash1 == hash2
        assert len(hash1) == 8

    def test_voice_hash_different_voices(self):
        """Test that different voices produce different hashes."""
        hash1 = get_voice_hash("bf_emma")
        hash2 = get_voice_hash("bf_isabella")
        assert hash1 != hash2


class TestKokoroEngine:
    """Tests for KokoroEngine class."""

    def test_kokoro_engine_validate_voice_valid(self):
        """Test that valid voices pass validation."""
        engine = KokoroEngine()
        assert engine.validate_voice("bf_emma") is True
        assert engine.validate_voice("af_sarah") is True
        assert engine.validate_voice("am_adam") is True

    def test_kokoro_engine_validate_voice_invalid(self):
        """Test that invalid voices fail validation."""
        engine = KokoroEngine()
        assert engine.validate_voice("invalid_voice") is False
        assert engine.validate_voice("") is False
        assert engine.validate_voice("bf_nonexistent") is False

    def test_kokoro_engine_validate_voice_valid_blend(self):
        """Test that valid blend strings pass validation."""
        engine = KokoroEngine()
        assert engine.validate_voice("bf_emma(0.7)+af_sarah(0.3)") is True

    def test_kokoro_engine_validate_voice_invalid_blend(self):
        """Test that invalid blend strings fail validation."""
        engine = KokoroEngine()
        # Blend with invalid voice
        assert engine.validate_voice("bf_emma(0.7)+invalid_voice(0.3)") is False

    def test_kokoro_engine_list_voices(self):
        """Test that list_voices returns correct fields."""
        engine = KokoroEngine()
        voices = engine.list_voices()
        assert len(voices) > 0
        # Check first voice has expected fields
        voice = voices[0]
        assert "key" in voice
        assert "name" in voice
        assert "gender" in voice
        assert "lang" in voice
        assert "description" in voice
        assert "engine" in voice
        assert voice["engine"] == "kokoro"

    @patch("core.tts.kokoro_engine.KokoroEngine._get_kokoro_instance")
    def test_kokoro_engine_generate_mock(self, mock_get_instance):
        """Test generate method with mocked Kokoro."""
        mock_kokoro_instance = MagicMock()
        mock_audio = np.zeros(24000, dtype=np.float32)
        mock_kokoro_instance.create.return_value = (mock_audio, 24000)
        mock_get_instance.return_value = mock_kokoro_instance

        engine = KokoroEngine()
        # Reset singleton for testing
        KokoroEngine._instance = None
        KokoroEngine._kokoro = None

        import asyncio
        result = asyncio.run(engine.generate("Hello world", "bf_emma"))
        assert result is not None
        audio, sr = result
        assert isinstance(audio, np.ndarray)
        assert sr == 24000
