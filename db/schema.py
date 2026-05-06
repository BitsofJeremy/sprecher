"""Database schema initialization."""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS voices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    engine TEXT NOT NULL CHECK(engine IN ('kokoro', 'qwen', 'system')),
    voice_type TEXT NOT NULL CHECK(voice_type IN ('clone', 'designed', 'preset', 'blend')),
    voice_key TEXT,
    language TEXT,
    voice_description TEXT,
    ref_audio_path TEXT,
    ref_text TEXT,
    sample_audio_path TEXT,
    speaking_style TEXT DEFAULT '',
    emotional_range TEXT DEFAULT '[]',
    is_system BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    engine TEXT NOT NULL CHECK(engine IN ('kokoro', 'qwen', 'whisper')),
    voice_id INTEGER REFERENCES voices(id),
    voice_key TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    scope TEXT NOT NULL DEFAULT 'tts',
    source_path TEXT NOT NULL DEFAULT '',
    output_path TEXT,
    audio_format TEXT NOT NULL DEFAULT 'wav',
    speed REAL DEFAULT 1.0,
    total_chunks INTEGER NOT NULL DEFAULT 0,
    completed_chunks INTEGER NOT NULL DEFAULT 0,
    progress INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    author TEXT NOT NULL DEFAULT '',
    cover_path TEXT NOT NULL DEFAULT '',
    language TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,
    title TEXT NOT NULL,
    word_count INTEGER NOT NULL DEFAULT 0,
    text TEXT NOT NULL DEFAULT '',
    audio_path TEXT
);

CREATE TABLE IF NOT EXISTS tts_clips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    voice_id INTEGER,
    voice_key TEXT NOT NULL DEFAULT '',
    audio_path TEXT NOT NULL,
    audio_format TEXT NOT NULL DEFAULT 'wav',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_engine ON jobs(engine);
CREATE INDEX IF NOT EXISTS idx_voices_engine ON voices(engine);
"""


def init_db_schema(conn):
    """Initialize database schema. Works with both sync (sqlite3) and async (aiosqlite) connections."""
    import asyncio
    # Check if it's an aiosqlite connection (has awaitable executescript)
    try:
        coro = conn.executescript(SCHEMA_SQL)
        # It's async - await it
        if hasattr(coro, '__await__'):
            # Create an event loop if needed and run the coroutine
            try:
                loop = asyncio.get_running_loop()
                # We're in async context, use create_task or handle differently
                pass
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(coro)
                return
            # Fallback - run in own loop
            loop = asyncio.new_event_loop()
            loop.run_until_complete(coro)
        else:
            conn.commit()
    except AttributeError:
        # Sync sqlite3 connection
        conn.executescript(SCHEMA_SQL)
        conn.commit()


async def init_db_schema_async(conn):
    """Async version for use with await."""
    await conn.executescript(SCHEMA_SQL)
    await conn.commit()