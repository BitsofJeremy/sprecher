"""Application lifespan (startup/shutdown events)."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

import config
from db import init_db_schema, seed_voices, seed_system_voices
from db.get_db import get_db
from jobs import get_job_runner


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    On startup:
    - Create required directories
    - Initialize database schema
    - Seed voices if database is empty

    On shutdown:
    - Stop the job runner
    """
    # Startup
    config.ensure_dirs()

    # Initialize database schema and seed data
    async with get_db() as db:
        init_db_schema(db)
        await seed_voices(db)
        await seed_system_voices(db)

    # Start job runner
    runner = get_job_runner()

    yield

    # Shutdown
    runner.stop()