"""API test fixtures."""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from contextlib import asynccontextmanager

import aiosqlite
from fastapi.testclient import TestClient


@asynccontextmanager
async def _mock_get_db(db_path: str):
    """Return a fresh async CM yielding a new connection each time."""
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


@pytest.fixture
def test_client(temp_work_dir, monkeypatch):
    """Create a FastAPI TestClient with mocked dependencies."""
    # Create temp DB
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    # Patch config before importing app
    import config
    monkeypatch.setattr(config, "WORK_DIR", temp_work_dir)
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(config, "API_KEY", "test-api-key")

    # Ensure dirs
    config.ensure_dirs()

    # Initialize DB schema using sync sqlite
    import sqlite3
    from db.schema import init_db_schema

    conn = sqlite3.connect(db_path)
    init_db_schema(conn)
    conn.close()

    # Mock job runner
    async def mock_enqueue(*args, **kwargs):
        return None

    mock_runner_instance = MagicMock()
    mock_runner_instance.enqueue = mock_enqueue

    # A callable that returns a fresh mock get_db CM each time it's called.
    # This mirrors the real get_db() which creates a new connection per call.
    def mock_get_db_factory():
        return _mock_get_db(db_path)

    # Minimal async lifespan that skips the real startup DB logic
    @asynccontextmanager
    async def test_lifespan(app):
        # Manually init the async DB
        async with aiosqlite.connect(db_path) as db:
            init_db_schema(db)
            await db.commit()
        yield

    # Patch all import variants of get_db so lifespan + route handlers both work
    with patch("db.get_db.get_db", mock_get_db_factory), \
         patch("db.get_db", mock_get_db_factory), \
         patch("jobs.queue.get_job_runner", return_value=mock_runner_instance):
        from app.main import app
        app.router.lifespan_context = test_lifespan
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client

    # Cleanup
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def auth_headers():
    """Return authorization headers for API requests."""
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def mock_kokoro_engine():
    """Mock Kokoro engine for API tests."""
    with patch("core.tts.kokoro_engine._get_kokoro") as mock_get:
        mock_instance = MagicMock()
        import numpy as np
        mock_instance.create.return_value = (np.zeros(24000, dtype=np.float32), 24000)
        mock_get.return_value = mock_instance
        yield mock_get
