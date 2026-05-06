"""DB test fixtures."""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from contextlib import asynccontextmanager

import aiosqlite
from db.schema import init_db_schema


@pytest.fixture
def test_db(tmp_path):
    """Create a temporary test database (sync path for use in patches)."""
    db_path = tmp_path / "test_sprecher.db"

    # Initialize schema
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    init_db_schema(conn)
    conn.close()

    yield str(db_path)


@pytest.fixture
async def test_db_async(tmp_path):
    """Create a temporary test database (async version)."""
    db_path = tmp_path / "test_sprecher_async.db"

    async with aiosqlite.connect(str(db_path)) as db:
        init_db_schema(db)
        await db.commit()

    yield str(db_path)


@pytest.fixture
def mock_get_db(test_db):
    """Return an async context manager that yields connections to test_db."""
    @asynccontextmanager
    async def _mock_get_db():
        db = await aiosqlite.connect(test_db)
        db.row_factory = aiosqlite.Row
        try:
            yield db
        finally:
            await db.close()

    return _mock_get_db
