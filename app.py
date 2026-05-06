#!/usr/bin/env python3
"""Sprecher - Unified TTS/STT Service entry point."""

from sprecher.app.main import app

if __name__ == "__main__":
    import uvicorn
    import config

    uvicorn.run(
        "sprecher.app.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
    )