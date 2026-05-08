"""Storage management API - cleanup old audio files."""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

import config
from api.voices import verify_api_key

router = APIRouter(prefix="/storage", tags=["storage"])


def _get_output_files() -> list[dict]:
    """Get list of output files with metadata."""
    output_dir = config.WORK_DIR / "data" / "output"
    if not output_dir.exists():
        return []

    files = []
    for f in output_dir.iterdir():
        if f.is_file():
            stat = f.stat()
            files.append({
                "name": f.name,
                "size": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M"),
                "age_days": (datetime.now() - datetime.fromtimestamp(stat.st_ctime)).days,
            })
    return sorted(files, key=lambda x: x["name"])


def _get_stats() -> dict:
    """Get storage statistics."""
    files = _get_output_files()
    total_size = sum(f["size"] for f in files)
    return {
        "file_count": len(files),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "output_dir": str(config.WORK_DIR / "data" / "output"),
    }


@router.get("/stats")
async def get_stats(authorization: Optional[str] = Header(None)):
    """Get storage statistics."""
    await verify_api_key(authorization)
    return JSONResponse(_get_stats())


@router.get("/files")
async def list_files(authorization: Optional[str] = Header(None)):
    """List all output files."""
    await verify_api_key(authorization)
    return JSONResponse({"files": _get_output_files()})


@router.post("/cleanup-old")
async def cleanup_old(days: int = 30, authorization: Optional[str] = Header(None)):
    """Delete files older than specified days."""
    await verify_api_key(authorization)

    output_dir = config.WORK_DIR / "data" / "output"
    if not output_dir.exists():
        return JSONResponse({"deleted": 0, "message": "Output directory not found"})

    cutoff = datetime.now() - timedelta(days=days)
    deleted = 0

    for f in output_dir.iterdir():
        if f.is_file():
            file_time = datetime.fromtimestamp(f.stat().st_ctime)
            if file_time < cutoff:
                f.unlink()
                deleted += 1

    return JSONResponse({
        "deleted": deleted,
        "message": f"Deleted {deleted} file(s) older than {days} days",
        "stats": _get_stats(),
    })


@router.post("/delete-selected")
async def delete_selected(filenames: list[str], authorization: Optional[str] = Header(None)):
    """Delete selected files."""
    await verify_api_key(authorization)

    output_dir = config.WORK_DIR / "data" / "output"
    deleted = 0

    for name in filenames:
        file_path = output_dir / name
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            deleted += 1

    return JSONResponse({
        "deleted": deleted,
        "message": f"Deleted {deleted} file(s)",
        "stats": _get_stats(),
    })


@router.post("/delete-all")
async def delete_all(authorization: Optional[str] = Header(None)):
    """Delete all output files."""
    await verify_api_key(authorization)

    output_dir = config.WORK_DIR / "data" / "output"
    deleted = 0

    for f in output_dir.iterdir():
        if f.is_file():
            f.unlink()
            deleted += 1

    return JSONResponse({
        "deleted": deleted,
        "message": f"Deleted {deleted} file(s)",
        "stats": _get_stats(),
    })


@router.delete("/files/{filename}")
async def delete_file(filename: str, authorization: Optional[str] = Header(None)):
    """Delete a single file."""
    await verify_api_key(authorization)

    output_dir = config.WORK_DIR / "data" / "output"
    file_path = output_dir / filename

    if not file_path.exists():
        return JSONResponse({"error": "File not found"}, status_code=404)

    file_path.unlink()
    return JSONResponse({
        "message": f"Deleted {filename}",
        "stats": _get_stats(),
    })