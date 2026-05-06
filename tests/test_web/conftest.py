"""Playwright test configuration and fixtures."""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest_asyncio
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async fixtures."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_work_dir(tmp_path):
    """Create a temporary work directory."""
    work_dir = tmp_path / "sprecher_test"
    data_dir = work_dir / "data"
    (data_dir / "uploads").mkdir(parents=True, exist_ok=True)
    (data_dir / "chunks").mkdir(parents=True, exist_ok=True)
    (data_dir / "output").mkdir(parents=True, exist_ok=True)
    (data_dir / "voices").mkdir(parents=True, exist_ok=True)
    return work_dir


@pytest.fixture
def sprecher_client(temp_work_dir, monkeypatch):
    """Create a FastAPI TestClient with temp DB and work dir."""
    import asyncio
    import tempfile
    import os
    from fastapi.testclient import TestClient
    from unittest.mock import patch, MagicMock

    # Create temp DB
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    # Patch config
    import config
    monkeypatch.setattr(config, "WORK_DIR", temp_work_dir)
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(config, "API_KEY", "test-api-key")
    monkeypatch.setattr(config, "AUTH_DISABLED", True)

    # Ensure dirs
    config.ensure_dirs()

    # Mock the job runner to avoid background threads
    with patch("jobs.queue.get_job_runner") as mock_runner:
        mock_runner_instance = MagicMock()
        mock_runner_instance.enqueue = MagicMock(return_value=asyncio.Future())
        mock_runner_instance.enqueue.return_value.set_result(None)
        mock_runner.return_value = mock_runner_instance

        # Import app after patching config
        from app.main import app

        # Initialize DB schema
        import aiosqlite
        from db.schema import init_db_schema

        async def init_test_db():
            async with aiosqlite.connect(db_path) as db:
                init_db_schema(db)
                await db.commit()

        asyncio.run(init_test_db())

        with TestClient(app) as client:
            yield client

    # Cleanup
    os.unlink(db_path)


@pytest.fixture
def browser_context_args(browser_context_args):
    """Configure browser context for testing."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 800},
        "ignore_https_errors": True,
    }
