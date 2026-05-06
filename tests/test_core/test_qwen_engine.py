"""Tests for Qwen TTS Engine."""
import pytest
from unittest.mock import patch, MagicMock

from core.tts.qwen_engine import QwenEngine, _get_qwen3_tts


class TestQwenEngine:
    """Tests for QwenEngine class."""

    def test_qwen_validate_voice_valid(self):
        """Test that valid Qwen voices pass validation."""
        engine = QwenEngine()
        # Reset singleton for testing
        QwenEngine._instance = None
        QwenEngine._qwen = None

        # Qwen has stub voices
        assert engine.validate_voice("qwen_clone_default") is True
        assert engine.validate_voice("qwen_design_default") is True

    def test_qwen_validate_voice_invalid(self):
        """Test that invalid Qwen voices fail validation."""
        engine = QwenEngine()
        # Reset singleton for testing
        QwenEngine._instance = None
        QwenEngine._qwen = None

        assert engine.validate_voice("invalid_voice") is False
        assert engine.validate_voice("") is False
        assert engine.validate_voice("bf_emma") is False  # Kokoro voice

    def test_qwen_list_voices(self):
        """Test that list_voices returns stub voices."""
        engine = QwenEngine()
        # Reset singleton for testing
        QwenEngine._instance = None
        QwenEngine._qwen = None

        voices = engine.list_voices()
        assert len(voices) == 2
        # Check first voice has expected fields
        voice = voices[0]
        assert "key" in voice
        assert "name" in voice
        assert "gender" in voice
        assert "engine" in voice
        assert voice["engine"] == "qwen"
        assert voice["voice_type"] == "clone"

    def test_qwen_is_available_defaults_to_false(self):
        """Test that Qwen engine defaults to unavailable (stub implementation)."""
        with patch("core.tts.qwen_engine._get_qwen3_tts") as mock_get:
            mock_get.return_value = None
            engine = QwenEngine()
            # Reset singleton for testing
            QwenEngine._instance = None
            QwenEngine._qwen = None
            assert engine.is_available is False
