"""Tests for jobs database operations."""
import pytest
from unittest.mock import patch

from db.jobs import (
    create_job,
    get_job,
    list_jobs,
    update_job,
    complete_job,
    fail_job,
)


class TestCreateAndGetJob:
    """Tests for create_job and get_job functions."""

    @pytest.mark.asyncio
    async def test_create_and_get_job(self, test_db, mock_get_db):
        """Test creating and retrieving a job."""
        with patch("db.get_db.get_db", mock_get_db):
            with patch("db.jobs.get_db", mock_get_db):
                job_id = await create_job(
                    title="Test TTS Job",
                    engine="kokoro",
                    voice_key="bf_emma",
                    status="queued",
                    scope="tts",
                    source_path="Test text",
                )

                assert job_id is not None
                assert isinstance(job_id, int)

                # Get the job
                job = await get_job(job_id)
                assert job is not None
                assert job["title"] == "Test TTS Job"
                assert job["engine"] == "kokoro"
                assert job["voice_key"] == "bf_emma"
                assert job["status"] == "queued"

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, test_db, mock_get_db):
        """Test that getting non-existent job returns None."""
        with patch("db.get_db.get_db", mock_get_db):
            with patch("db.jobs.get_db", mock_get_db):
                job = await get_job(99999)
                assert job is None


class TestListJobs:
    """Tests for list_jobs function."""

    @pytest.mark.asyncio
    async def test_list_jobs_with_filter(self, test_db, mock_get_db):
        """Test listing jobs with filters."""
        with patch("db.get_db.get_db", mock_get_db):
            with patch("db.jobs.get_db", mock_get_db):
                # Create multiple jobs
                await create_job(
                    title="TTS Job 1",
                    engine="kokoro",
                    status="queued",
                    scope="tts",
                    source_path="Text 1",
                )
                await create_job(
                    title="TTS Job 2",
                    engine="kokoro",
                    status="completed",
                    scope="tts",
                    source_path="Text 2",
                )
                await create_job(
                    title="STT Job",
                    engine="whisper",
                    status="queued",
                    scope="stt",
                    source_path="Audio 1",
                )

                # List all jobs
                all_jobs = await list_jobs(limit=100)
                assert len(all_jobs) == 3

                # Filter by status
                queued_jobs = await list_jobs(status="queued")
                assert len(queued_jobs) == 2

                # Filter by engine
                kokoro_jobs = await list_jobs(engine="kokoro")
                assert len(kokoro_jobs) == 2

                # Filter by scope
                tts_jobs = await list_jobs(scope="tts")
                assert len(tts_jobs) == 2


class TestUpdateJob:
    """Tests for update_job function."""

    @pytest.mark.asyncio
    async def test_update_job(self, test_db, mock_get_db):
        """Test updating job fields."""
        with patch("db.get_db.get_db", mock_get_db):
            with patch("db.jobs.get_db", mock_get_db):
                job_id = await create_job(
                    title="Original Title",
                    engine="kokoro",
                    status="queued",
                    scope="tts",
                    source_path="Text",
                )

                # Update the job
                success = await update_job(
                    job_id,
                    status="running",
                    progress=50,
                )
                assert success is True

                # Verify update
                job = await get_job(job_id)
                assert job["status"] == "running"
                assert job["progress"] == 50


class TestCompleteJob:
    """Tests for complete_job function."""

    @pytest.mark.asyncio
    async def test_complete_job(self, test_db, mock_get_db):
        """Test marking a job as completed."""
        with patch("db.get_db.get_db", mock_get_db):
            with patch("db.jobs.get_db", mock_get_db):
                job_id = await create_job(
                    title="Job to Complete",
                    engine="kokoro",
                    status="running",
                    scope="tts",
                    source_path="Text",
                )

                # Mark as completed
                success = await complete_job(job_id, output_path="/path/to/output.wav")
                assert success is True

                # Verify
                job = await get_job(job_id)
                assert job["status"] == "completed"
                assert job["progress"] == 100
                assert job["output_path"] == "/path/to/output.wav"
                assert job["completed_at"] is not None


class TestFailJob:
    """Tests for fail_job function."""

    @pytest.mark.asyncio
    async def test_fail_job(self, test_db, mock_get_db):
        """Test marking a job as failed."""
        with patch("db.get_db.get_db", mock_get_db):
            with patch("db.jobs.get_db", mock_get_db):
                job_id = await create_job(
                    title="Job to Fail",
                    engine="kokoro",
                    status="running",
                    scope="tts",
                    source_path="Text",
                )

                # Mark as failed
                success = await fail_job(job_id, error_message="Something went wrong")
                assert success is True

                # Verify
                job = await get_job(job_id)
                assert job["status"] == "failed"
                assert job["error_message"] == "Something went wrong"
                assert job["completed_at"] is not None
