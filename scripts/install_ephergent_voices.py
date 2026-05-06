#!/usr/bin/env python3
"""
Install Ephergent voices into Sprecher.

Copies reference audio files to the server's voice directory,
registers voices in Sprecher's database, and optionally
creates MiniMax voice clones for each character.

Usage:
    python3 scripts/install_ephergent_voices.py [--dry-run]

Environment:
    SPRECHER_WORK_DIR     - Sprecher data directory (default: ~/sprecher)
    MINIMAX_API_KEY       - MiniMax API key for voice cloning
    SPRECHER_API_KEY      - Sprecher API key (if auth enabled)
"""

import os
import sys
import json
import argparse
import subprocess
import tempfile
import shutil
from pathlib import Path

# Ephergent voice definitions
EPHERGENT_VOICES = [
    {
        "slug": "pixel-paradox",
        "name": "Pixel Paradox",
        "key": "ephergent_pixel",
        "wav": "pixel.wav",
        "txt": "pixel.txt",
        "description": "The interdimensional courier with a coffee obsession and a talent for surviving reality crashes. Yours truly.",
    },
    {
        "slug": "a1",
        "name": "A1",
        "key": "ephergent_a1",
        "wav": "a1.wav",
        "txt": "a1.txt",
        "description": "The hyper-logical assistant navigating existential crises with meticulous precision and unsettling sincerity.",
    },
    {
        "slug": "clive",
        "name": "Clive",
        "key": "ephergent_clive",
        "wav": "clive.wav",
        "txt": "clive.txt",
        "description": "The grizzled gumshoe who's seen it all, from paperclip shortages to reality audits.",
    },
    {
        "slug": "baron",
        "name": "Baron",
        "key": "ephergent_baron",
        "wav": "baron.wav",
        "txt": "baron.txt",
        "description": "The Grand Gnome Hegemony's most unconventional operative. Lawn care is strategy.",
    },
    {
        "slug": "glitch",
        "name": "Glitch",
        "key": "ephergent_glitch",
        "wav": "glitch.wav",
        "txt": "glitch.txt",
        "description": "Reality's favorite bug. Glitches aren't failures — they're features that make us human.",
    },
    {
        "slug": "kai",
        "name": "Kai",
        "key": "ephergent_kai",
        "wav": "kai.wav",
        "txt": "kai.txt",
        "description": "The quiet mystic who sees the breath beneath the chaos. Dimensional monk.",
    },
    {
        "slug": "lumina",
        "name": "Lumina",
        "key": "ephergent_lumina",
        "wav": "lumina.wav",
        "txt": "lumina.txt",
        "description": "The photographer making history permanent. Every photo is defiance against The Board's erasure.",
    },
    {
        "slug": "meatball",
        "name": "Meatball",
        "key": "ephergent_meatball",
        "wav": "meatball.wav",
        "txt": "meatball.txt",
        "description": "The goodest boy in the interdimensional crisis. Professional meatball enthusiast.",
    },
    {
        "slug": "nano",
        "name": "Nano",
        "key": "ephergent_nano",
        "wav": "nano.wav",
        "txt": "nano.txt",
        "description": "The data broker with expensive taste and a talent for finding corrupted probability streams.",
    },
    {
        "slug": "nocturne",
        "name": "Nocturne",
        "key": "ephergent_nocturne",
        "wav": "nocturne.wav",
        "txt": "nocturne.txt",
        "description": "The critic from the great condensers. Sophisticated despair elevated to high art.",
    },
]


def get_work_dir() -> Path:
    return Path(os.environ.get("SPRECHER_WORK_DIR", "~/sprecher")).expanduser()


def get_api_base() -> str:
    host = os.environ.get("SPRECHER_HOST", "localhost")
    port = os.environ.get("SPRECHER_PORT", "8400")
    return f"http://{host}:{port}"


def api_headers() -> dict:
    key = os.environ.get("SPRECHER_API_KEY", "")
    if key:
        return {"Authorization": f"Bearer {key}"}
    return {}


def install_voices(source_dir: Path, dry_run: bool = False) -> dict[str, str]:
    """Copy voice files to Sprecher's voice directory and register in DB.

    Returns dict mapping slug -> minimax_voice_id (if cloned).
    """
    work_dir = get_work_dir()
    voices_dir = work_dir / "data" / "voices" / "ephergent"
    voices_dir.mkdir(parents=True, exist_ok=True)

    minimax_key = os.environ.get("MINIMAX_API_KEY", "")
    minimax_voice_ids: dict[str, str] = {}

    for voice in EPHERGENT_VOICES:
        slug = voice["slug"]
        key = voice["key"]
        wav_file = source_dir / voice["wav"]
        txt_file = source_dir / voice["txt"]

        if not wav_file.exists():
            print(f"  [SKIP] {slug}: {wav_file} not found")
            continue

        if dry_run:
            print(f"  [DRY] Would copy {wav_file} -> {voices_dir / voice['wav']}")
            print(f"  [DRY] Would register voice '{voice['name']}' (key={key})")
            continue

        # Copy files to voice directory
        dest_wav = voices_dir / voice["wav"]
        dest_txt = voices_dir / voice["txt"]
        shutil.copy2(wav_file, dest_wav)
        if txt_file.exists():
            shutil.copy2(txt_file, dest_txt)

        # Register in Sprecher DB via API
        # ref_audio_path = absolute path to the reference wav
        ref_audio_path = str(dest_wav)
        ref_text = txt_file.read_text().strip() if txt_file.exists() else ""

        print(f"  [OK] {slug}: files copied to {voices_dir}")
        print(f"       ref_audio_path = {ref_audio_path}")

        # Call Sprecher voice create API
        api_base = get_api_base()
        try:
            import urllib.request
            data = json.dumps({
                "name": voice["name"],
                "engine": "kokoro",  # registered as kokoro type; engine selection happens at TTS time
                "voice_type": "clone",
                "voice_key": key,
                "language": "en-us",
                "voice_description": voice["description"],
                "ref_audio_path": ref_audio_path,
                "ref_text": ref_text,
                "speaking_style": "character voice for The Ephergent sci-fi radio drama",
                "slug": slug,
            }).encode()
            req = urllib.request.Request(
                f"{api_base}/api/voices",
                data=data,
                headers={**api_headers(), "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
                print(f"       DB: voice_id={result.get('id')} slug={result.get('slug')}")
        except Exception as e:
            print(f"       DB ERROR: {e}")

        # Create MiniMax voice clone (requires API key)
        if minimax_key and wav_file.exists():
            try:
                voice_id = create_minimax_voice_clone(
                    minimax_key, voice["name"], wav_file, txt_file
                )
                if voice_id:
                    minimax_voice_ids[slug] = voice_id
                    print(f"       MiniMax: voice_id={voice_id}")
            except Exception as e:
                print(f"       MiniMax ERROR: {e}")

    return minimax_voice_ids


def create_minimax_voice_clone(
    api_key: str,
    name: str,
    wav_path: Path,
    txt_path: Path | None,
) -> str | None:
    """Upload reference audio to MiniMax and return a persistent voice_id.

    Uses MiniMax's voice cloning API endpoint.
    """
    import urllib.request

    url = "https://api.minimaxi.chat/v1/voice clone/create"

    with open(wav_path, "rb") as wav_f:
        wav_data = wav_f.read()

    txt_data = b""
    if txt_path and txt_path.exists():
        txt_data = txt_path.read_bytes()

    # multipart/form-data request
    boundary = "----FormBoundary" + os.urandom(12).hex()
    body = b""

    # name field
    body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"name\"\r\n\r\n{name}\r\n".encode()

    # audio_file field
    body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"audio_file\"; filename=\"{wav_path.name}\"\r\nContent-Type: audio/wav\r\n\r\n".encode() + wav_data + b"\r\n"

    # text_file field (optional)
    if txt_data:
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"text_file\"; filename=\"{txt_path.name if txt_path else 'ref.txt'}\"\r\nContent-Type: text/plain\r\n\r\n".encode() + txt_data + b"\r\n"

    body += f"--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            return result.get("voice_id") or result.get("data", {}).get("voice_id")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()[:200]
        print(f"       MiniMax HTTP {e.code}: {error_body}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Install Ephergent voices into Sprecher")
    parser.add_argument("--source", type=Path, default=None,
                        help="Source directory containing Ephergent voice files")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without making changes")
    args = parser.parse_args()

    # Default source: The Ephergent Archive
    if args.source:
        source_dir = args.source
    else:
        possible = [
            Path("/home/debian/Documents/The_Ephergent_Archive/ephergent_voices"),
            Path("~/Documents/The_Ephergent_Archive/ephergent_voices"),
        ]
        source_dir = next((p for p in possible if p.exists()), None)
        if not source_dir:
            print("ERROR: Source directory not found.")
            print("  Tried:", [str(p) for p in possible])
            sys.exit(1)

    print(f"Installing Ephergent voices from: {source_dir}")
    print(f"Work dir: {get_work_dir()}")
    if args.dry_run:
        print("[DRY RUN - no changes will be made]\n")

    result = install_voices(source_dir, dry_run=args.dry_run)

    print("\nDone.")
    if result:
        print("MiniMax voice IDs:")
        for slug, vid in result.items():
            print(f"  {slug}: {vid}")
    else:
        print("No MiniMax voice clones created (set MINIMAX_API_KEY to enable)")


if __name__ == "__main__":
    main()
