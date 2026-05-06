"""Tests for Voices API endpoints."""
import pytest
import json


class TestVoicesList:
    """Tests for GET /api/voices endpoint."""

    def test_get_voices(self, test_client, auth_headers):
        """Test listing voices."""
        response = test_client.get("/api/voices", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "voices" in data
        assert isinstance(data["voices"], list)

    def test_get_voices_filter_by_engine(self, test_client, auth_headers):
        """Test listing voices filtered by engine."""
        response = test_client.get(
            "/api/voices?engine=kokoro",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for voice in data["voices"]:
            assert voice["engine"] == "kokoro"


class TestVoicesCreate:
    """Tests for POST /api/voices endpoint."""

    def test_post_voices(self, test_client, auth_headers):
        """Test creating a voice."""
        response = test_client.post(
            "/api/voices",
            headers=auth_headers,
            data={
                "name": "Test Voice",
                "engine": "kokoro",
                "voice_type": "preset",
                "voice_key": "bf_emma",
                "language": "en-us",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "slug" in data
        assert data["slug"] == "test-voice"

    def test_post_voices_invalid_engine(self, test_client, auth_headers):
        """Test that invalid engine returns 400."""
        response = test_client.post(
            "/api/voices",
            headers=auth_headers,
            data={
                "name": "Test Voice",
                "engine": "invalid_engine",
                "voice_type": "preset",
            },
        )
        assert response.status_code == 400

    def test_post_voices_invalid_voice_type(self, test_client, auth_headers):
        """Test that invalid voice_type returns 400."""
        response = test_client.post(
            "/api/voices",
            headers=auth_headers,
            data={
                "name": "Test Voice",
                "engine": "kokoro",
                "voice_type": "invalid_type",
            },
        )
        assert response.status_code == 400


class TestVoicesGet:
    """Tests for GET /api/voices/{id} endpoint."""

    def test_get_voice_by_id(self, test_client, auth_headers):
        """Test getting a voice by ID."""
        # Create a voice first
        create_response = test_client.post(
            "/api/voices",
            headers=auth_headers,
            data={
                "name": "My Test Voice",
                "engine": "kokoro",
                "voice_type": "preset",
                "voice_key": "bf_emma",
            },
        )
        voice_id = create_response.json()["id"]
        
        # Get the voice
        response = test_client.get(f"/api/voices/{voice_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == voice_id
        assert data["name"] == "My Test Voice"

    def test_get_voice_not_found(self, test_client, auth_headers):
        """Test that non-existent voice returns 404."""
        response = test_client.get("/api/voices/99999", headers=auth_headers)
        assert response.status_code == 404


class TestVoicesUpdate:
    """Tests for PUT /api/voices/{id} endpoint."""

    def test_put_voice(self, test_client, auth_headers):
        """Test updating a voice."""
        # Create a voice first
        create_response = test_client.post(
            "/api/voices",
            headers=auth_headers,
            data={
                "name": "Original Name",
                "engine": "kokoro",
                "voice_type": "preset",
                "voice_key": "bf_emma",
            },
        )
        voice_id = create_response.json()["id"]
        
        # Update the voice
        response = test_client.put(
            f"/api/voices/{voice_id}",
            headers=auth_headers,
            data={
                "name": "Updated Name",
                "voice_description": "A nice voice",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify update
        get_response = test_client.get(f"/api/voices/{voice_id}", headers=auth_headers)
        assert get_response.json()["name"] == "Updated Name"


class TestVoicesDelete:
    """Tests for DELETE /api/voices/{id} endpoint."""

    def test_delete_voice(self, test_client, auth_headers):
        """Test deleting a voice."""
        # Create a voice first
        create_response = test_client.post(
            "/api/voices",
            headers=auth_headers,
            data={
                "name": "To Be Deleted",
                "engine": "kokoro",
                "voice_type": "preset",
                "voice_key": "bf_emma",
            },
        )
        voice_id = create_response.json()["id"]

        # Delete the voice
        response = test_client.delete(f"/api/voices/{voice_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify deletion
        get_response = test_client.get(f"/api/voices/{voice_id}", headers=auth_headers)
        assert get_response.status_code == 404
