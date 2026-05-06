"""Tests for Narrate API endpoints."""
import pytest
from unittest.mock import patch, MagicMock
import io


class TestNarratePreview:
    """Tests for POST /api/narrate/preview endpoint."""

    def test_post_narrate_preview_txt(self, test_client, auth_headers, tmp_path):
        """Test previewing a TXT document."""
        # Create a test text file
        txt_content = "Chapter One\n\nThis is the first chapter content.\n\nChapter Two\n\nThis is the second chapter."
        txt_file = tmp_path / "test.txt"
        txt_file.write_text(txt_content)
        
        with open(txt_file, "rb") as f:
            response = test_client.post(
                "/api/narrate/preview",
                headers=auth_headers,
                files={"document": ("test.txt", f, "text/plain")},
            )
        # Document should be parsed
        assert response.status_code == 200
        data = response.json()
        assert "chapters" in data
        assert "total_chapters" in data
        assert "total_words" in data

    def test_post_narrate_preview_unsupported_format(self, test_client, auth_headers, tmp_path):
        """Test that unsupported format returns 400."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy pdf content")
        
        with open(pdf_file, "rb") as f:
            response = test_client.post(
                "/api/narrate/preview",
                headers=auth_headers,
                files={"document": ("test.pdf", f, "application/pdf")},
            )
        assert response.status_code == 400


class TestNarrate:
    """Tests for POST /api/narrate endpoint."""

    def test_post_narrate(self, test_client, auth_headers, tmp_path):
        """Test starting a narration job."""
        # Create a test text file
        txt_content = "Title\n\nThis is test content for narration."
        txt_file = tmp_path / "test.txt"
        txt_file.write_text(txt_content)
        
        with open(txt_file, "rb") as f:
            response = test_client.post(
                "/api/narrate",
                headers=auth_headers,
                data={
                    "voice_key": "bf_emma",
                    "audio_format": "mp3",
                    "speed": 1.0,
                },
                files={"document": ("test.txt", f, "text/plain")},
            )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"


class TestNarrateJobs:
    """Tests for GET /api/narrate/jobs endpoint."""

    def test_get_narrate_jobs(self, test_client, auth_headers):
        """Test listing narration jobs."""
        response = test_client.get("/api/narrate/jobs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "count" in data

    def test_get_narrate_jobs_empty(self, test_client, auth_headers):
        """Test listing narration jobs when none exist."""
        response = test_client.get("/api/narrate/jobs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
