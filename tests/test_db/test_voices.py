"""Tests for voices database operations."""
import pytest
from unittest.mock import patch

from db.voices import (
    create_voice,
    get_voice,
    list_voices,
    update_voice,
    delete_voice,
)


class TestCreateAndGetVoice:
    """Tests for create_voice and get_voice functions."""

    @pytest.mark.asyncio
    async def test_create_and_get_voice(self, test_db, mock_get_db):
        """Test creating and retrieving a voice."""
        with patch("db.get_db.get_db", mock_get_db):
            with patch("db.voices.get_db", mock_get_db):
                voice_id = await create_voice(
                    name="Test Voice",
                    slug="test-voice",
                    engine="kokoro",
                    voice_type="preset",
                    voice_key="bf_emma",
                    language="en-us",
                )

                assert voice_id is not None
                assert isinstance(voice_id, int)

                # Get the voice
                voice = await get_voice(voice_id)
                assert voice is not None
                assert voice["name"] == "Test Voice"
                assert voice["slug"] == "test-voice"
                assert voice["engine"] == "kokoro"
                assert voice["voice_key"] == "bf_emma"

    @pytest.mark.asyncio
    async def test_get_voice_not_found(self, test_db, mock_get_db):
        """Test that getting non-existent voice returns None."""
        with patch("db.get_db.get_db", mock_get_db):
            with patch("db.voices.get_db", mock_get_db):
                voice = await get_voice(99999)
                assert voice is None


class TestListVoices:
    """Tests for list_voices function."""

    @pytest.mark.asyncio
    async def test_list_voices_filter_by_engine(self, test_db, mock_get_db):
        """Test listing voices filtered by engine."""
        with patch("db.get_db.get_db", mock_get_db):
            with patch("db.voices.get_db", mock_get_db):
                # Create voices for different engines
                await create_voice(
                    name="Kokoro Voice",
                    slug="kokoro-voice",
                    engine="kokoro",
                    voice_type="preset",
                    voice_key="bf_emma",
                )
                await create_voice(
                    name="Qwen Voice",
                    slug="qwen-voice",
                    engine="qwen",
                    voice_type="clone",
                    voice_key="qwen_clone_default",
                )

                # List all voices
                all_voices = await list_voices(limit=100)
                assert len(all_voices) == 2

                # Filter by engine
                kokoro_voices = await list_voices(engine="kokoro")
                assert len(kokoro_voices) == 1
                assert kokoro_voices[0]["engine"] == "kokoro"

                qwen_voices = await list_voices(engine="qwen")
                assert len(qwen_voices) == 1
                assert qwen_voices[0]["engine"] == "qwen"


class TestUpdateVoice:
    """Tests for update_voice function."""

    @pytest.mark.asyncio
    async def test_update_voice(self, test_db, mock_get_db):
        """Test updating voice fields."""
        with patch("db.get_db.get_db", mock_get_db):
            with patch("db.voices.get_db", mock_get_db):
                voice_id = await create_voice(
                    name="Original Name",
                    slug="original-name",
                    engine="kokoro",
                    voice_type="preset",
                    voice_key="bf_emma",
                )

                # Update the voice
                success = await update_voice(
                    voice_id,
                    name="Updated Name",
                    voice_description="A nice voice",
                )
                assert success is True

                # Verify update
                voice = await get_voice(voice_id)
                assert voice["name"] == "Updated Name"
                assert voice["voice_description"] == "A nice voice"


class TestDeleteVoice:
    """Tests for delete_voice function."""

    @pytest.mark.asyncio
    async def test_delete_voice_success(self, test_db, mock_get_db):
        """Test successfully deleting a non-system voice."""
        with patch("db.get_db.get_db", mock_get_db):
            with patch("db.voices.get_db", mock_get_db):
                voice_id = await create_voice(
                    name="Deletable Voice",
                    slug="deletable-voice",
                    engine="kokoro",
                    voice_type="preset",
                )

                # Delete the voice
                success = await delete_voice(voice_id)
                assert success is True

                # Verify deletion
                voice = await get_voice(voice_id)
                assert voice is None

    @pytest.mark.asyncio
    async def test_delete_voice_protected_system(self, test_db, mock_get_db):
        """Test that system voices cannot be deleted."""
        import aiosqlite

        with patch("db.get_db.get_db", mock_get_db):
            with patch("db.voices.get_db", mock_get_db):
                # Insert a system voice directly into the DB
                async with aiosqlite.connect(test_db) as db:
                    await db.execute(
                        "INSERT INTO voices "
                        "(name, slug, engine, voice_type, voice_key, is_system) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        ("System Voice", "system-voice", "system", "preset", "system_default", 1),
                    )
                    await db.commit()

                # Retrieve to get the id
                all_voices = await list_voices(limit=100)
                system_voice = next(v for v in all_voices if v["slug"] == "system-voice")
                voice_id = system_voice["id"]

                # Try to delete - should succeed (the function doesn't actually block it,
                # but we verify the system voice IS protected by is_system=1)
                success = await delete_voice(voice_id)
                # The actual protection is the WHERE is_system=0 in the DELETE query
                # So this should return False (0 rows affected)
                assert success is False

                # Voice should still exist
                voice = await get_voice(voice_id)
                assert voice is not None
