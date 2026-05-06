"""Database connection management with aiosqlite."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiosqlite

import config


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Get async database connection with WAL mode."""
    db = await aiosqlite.connect(config.DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        yield db
    finally:
        await db.close()