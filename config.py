"""Sprecher configuration."""

from pathlib import Path
import os

# Base paths
WORK_DIR = Path(os.environ.get("SPRECHER_WORK_DIR", "~/sprecher")).expanduser()
PORT = int(os.environ.get("SPRECHER_PORT", "8400"))
HOST = os.environ.get("SPRECHER_HOST", "0.0.0.0")
DB_PATH = os.environ.get("SPRECHER_DB_PATH", str(WORK_DIR / "sprecher.db"))

# Model directories
KOKORO_MODEL_DIR = Path(os.environ.get("SPRECHER_KOKORO_MODEL_DIR", "~/.claude/kokoro-models")).expanduser()
QWEN_MODEL_SIZE = os.environ.get("SPRECHER_QWEN_MODEL_SIZE", "auto")

# Audio settings
CHUNK_SIZE_WORDS = int(os.environ.get("SPRECHER_CHUNK_SIZE_WORDS", "200"))
AUDIO_FORMAT = os.environ.get("SPRECHER_AUDIO_FORMAT", "mp3")
AUDIO_BITRATE = os.environ.get("SPRECHER_AUDIO_BITRATE", "128k")

# Engine settings
DEFAULT_ENGINE = os.environ.get("SPRECHER_DEFAULT_ENGINE", "kokoro")

# Auth
API_KEY = os.environ.get("SPRECHER_API_KEY", "")
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
# Set SPRECHER_AUTH_DISABLED=true to disable API auth (useful for local web UI)
AUTH_DISABLED = os.environ.get("SPRECHER_AUTH_DISABLED", "false").lower() == "true"

# Ensure runtime directories exist
def ensure_dirs() -> None:
    """Create all required runtime directories."""
    for subdir in ["data/uploads", "data/chunks", "data/output", "data/voices"]:
        dir_path = WORK_DIR / subdir
        dir_path.mkdir(parents=True, exist_ok=True)

# Initialize directories on import
ensure_dirs()