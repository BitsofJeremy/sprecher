"""Database connection management with aiosqlite."""

from contextlib import contextmanager
from typing import Generator

import aiosqlite

import config


@contextmanager
async def get_db() -> Generator[aiosqlite.Connection, None, None]:
    """Get async database connection with WAL mode."""
    db = await aiosqlite.connect(config.DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        yield db
    finally:
        await db.close()