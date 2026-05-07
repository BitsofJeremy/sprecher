#!/usr/bin/env python3
"""
Install Ephergent voices into Sprecher using Qwen3-TTS voice cloning.

This script:
1. Copies reference .wav files from the Ephergent voices source dir
   to the Sprecher data directory
2. Registers each character voice in Sprecher's SQLite DB
3. Copies characters_data.py so it can be imported at runtime

The voices use Qwen3-TTS voice cloning (create_voice_clone_prompt API).
Each voice is registered with voice_type='ephergent' and engine='qwen'.

Usage:
    # From the sprecher repo root:
    python3 scripts/install_ephergent_voices.py

    # Or from any directory with a --source flag:
    python3 scripts/install_ephergent_voices.py --source /path/to/WeirDing

Environment:
    SPRECHER_WORK_DIR   - Sprecher data dir (default: ~/sprecher)
    SPRECHER_API_KEY    - Sprecher API key (if auth enabled)
"""

import os
import sys
import shutil
import sqlite3
import argparse
from pathlib import Path

# Character definitions (mirrors characters_data.py from WeirDing)
CHARACTERS = {
    "a1": {
        "name": "ARC",
        "voice_description": (
            "Mid-range male voice, measured and precise with stoic British formality. "
            "Butler-like composure with occasional subtle emotional breaks. "
            "Dry wit delivered through understatement. Formal, refined articulation."
        ),
        "speaking_style": "Formal address, British idioms, espresso metaphors for emotions",
        "emotional_range": ["politely bewildered", "dry wit", "quiet concern", "understated terror"],
        "ref_audio": "a1.wav",
        "ref_text": (
            "Miss Paradox, I do believe reality is experiencing what one might call "
            "an existential crisis. Most inconvenient. I've prepared your espresso "
            "precisely as preferred, though I confess I'm uncertain whether I did so "
            "because you need it, or because I need to provide it."
        ),
    },
    "baron": {
        "name": "Baron Klaus von Gnomendorf",
        "voice_description": (
            "Deep, resonant baritone voice. Pompous and grandiose with Germanic/Austrian "
            "aristocratic accent. Commanding presence despite comedic context. "
            "Self-important delivery with elaborate vocabulary."
        ),
        "speaking_style": "Military tactical language applied to gardening, verbose monologues",
        "emotional_range": ["pompous pride", "sputtering indignation", "maniacal glee", "frustrated"],
        "ref_audio": "baron.wav",
        "ref_text": (
            "Fellow operatives! I have identified a critical weakness in this dimensional "
            "crisis. The enemy has failed to consider proper lawn maintenance! Today's "
            "victory proves that superior intellect and garden management can triumph "
            "over chaos itself. The Grand Gnome Hegemony grows ever closer to reality!"
        ),
    },
    "clive": {
        "name": "Clive Stapler",
        "voice_description": (
            "Gravelly, world-weary male voice. Classic 1940s American noir detective tone. "
            "Weathered and cynical, carrying the weight of 90 years of experience. "
            "Hard-boiled delivery with dark humor."
        ),
        "speaking_style": "Noir detective narration, office supply metaphors, short punchy observations",
        "emotional_range": ["cynical", "world-weary", "darkly humorous", "grieving"],
        "ref_audio": "clive.wav",
        "ref_text": (
            "I've seen it all, kid. From paperclip shortages to reality audits. "
            "The old gumshoe always said: trust the patterns, not the promises. "
            "Word on the desk is, The Board's been measuring smiles again. "
            "It's Corporate Corp wearing a different tie."
        ),
    },
    "glitch": {
        "name": "Zephyr Glitch",
        "voice_description": (
            "Higher energy youthful male voice, 21 years old. Manic and enthusiastic "
            "with modern American accent. Fast-paced delivery with underlying emotional "
            "strain from grief. Tech-speak patterns."
        ),
        "speaking_style": "Rapid-fire tech jargon, coding metaphors for emotions, verbal tangents",
        "emotional_range": ["manic enthusiasm", "nervous energy", "grief-tinged hope", "excited"],
        "ref_audio": "glitch.wav",
        "ref_text": (
            "Okay, so reality just kernel panicked, and I'm pretty sure the error "
            "message is in ancient Sumerian, which is both terrifying and kind of cool? "
            "Bugs aren't failures, they're features. Glitches make us human."
        ),
    },
    "kai": {
        "name": "Om Kai",
        "voice_description": (
            "Low to mid-range male voice, grounded and serene. Gentle and wise tone "
            "with calm, measured delivery. Contemplative and unhurried pacing. "
            "Slight Eastern philosophical quality."
        ),
        "speaking_style": "Buddhist metaphors, quantum physics analogies, measured breathing room between thoughts",
        "emotional_range": ["serene acceptance", "gentle wisdom", "patient compassion", "quiet struggle"],
        "ref_audio": "kai.wav",
        "ref_text": (
            "The dimensional fluctuations mirror the breath, chaotic on surface, "
            "following deeper patterns of interdependence. True balance isn't absence "
            "of chaos, it's full acceptance of it. Stay balanced. Stay compassionate. "
            "Stay imperfect."
        ),
    },
    "lumina": {
        "name": "Luminara Usha",
        "voice_description": (
            "Mid-range female voice, professional and precise. Calm observer tone "
            "with clear, neutral articulation. Measured and deliberate delivery "
            "with emerging emotional honesty."
        ),
        "speaking_style": "Photography technical language, framing scenes like photographs, matter-of-fact",
        "emotional_range": ["professional calm", "quiet determination", "emerging vulnerability", "defiant"],
        "ref_audio": "lumina.wav",
        "ref_text": (
            "My light meter indicates impossibility. Standard Tuesday reading. "
            "Every photo I take is an act of defiance against forgetting. "
            "The Board wants to erase history; I'm making it permanent."
        ),
    },
    "meatball": {
        "name": "Meatball",
        "voice_description": (
            "Deep, friendly male voice with enthusiastic energy. Earnest and simple "
            "delivery, lovable and warm. Occasional intimidating shift when protective. "
            "Unpretentious and straightforward."
        ),
        "speaking_style": "Simple direct sentences, always mentions meatballs, literal interpretation of metaphors",
        "emotional_range": ["enthusiastic joy", "earnest concern", "protective intimidation", "confused but helpful"],
        "ref_audio": "meatball.wav",
        "ref_text": (
            "Woof! I like meatballs! Is someone in trouble? I don't understand "
            "interdimensional physics, but you seem worried. I like meatballs. "
            "Can I help by sitting on something?"
        ),
    },
    "nano": {
        "name": "Nano",
        "voice_description": (
            "Mid-range female voice, 25 years old. Cryptic and pragmatic with "
            "street-smart edge. Glitchy quality with sudden starts and stops. "
            "Transactional and fragmented delivery."
        ),
        "speaking_style": "Cryptic bursts, fragmented sentences, mentions CLX currency, appears/disappears",
        "emotional_range": ["cryptic detachment", "street-smart cynicism", "transactional", "mysterious"],
        "ref_audio": "nano.wav",
        "ref_text": (
            "Got the data you wanted. Cost you CLX. Reality's expensive these days, "
            "especially on Tuesdays. Don't trust the probability streams. "
            "They're corrupted. Nano out."
        ),
    },
    "nocturne": {
        "name": "Nocturne Aesthete",
        "voice_description": (
            "Low to mid-range voice, elegant and melancholic. Baroque eloquence with "
            "old-world aristocratic quality. Refined and beautiful language, "
            "dripping with cultivated ennui."
        ),
        "speaking_style": "Baroque elaborate language, artistic criticism metaphors, archaic vocabulary",
        "emotional_range": ["refined melancholy", "elegant disdain", "exquisite sensitivity", "cultivated ennui"],
        "ref_audio": "nocturne.wav",
        "ref_text": (
            "One observes this dimensional disturbance with the eye of a critic. "
            "The composition is chaotic, the emotional resonance crude. "
            "Our carefully cultivated ennui, refined near the great condensers, "
            "is an art form. Raw despair is simply vulgar."
        ),
    },
    "pixel": {
        "name": "Pixel Paradox",
        "voice_description": (
            "Mid-range female voice, conversational and authentic. Casual with "
            "urgency and snark, modern American accent. Raw and imperfect delivery "
            "like talking to a friend over coffee."
        ),
        "speaking_style": "Friend-catching-you-up energy, tangents, corporate-burnout snark, meta-awareness",
        "emotional_range": ["snarky exhaustion", "authentic confusion", "protective determination", "raw honesty"],
        "ref_audio": "pixel.wav",
        "ref_text": (
            "Okay, so you're not gonna believe what happened. I'm just trying to "
            "enjoy my interdimensional coffee when reality decides to kernel panic. "
            "Stay weird, keep your phase-shifters calibrated."
        ),
    },
}


def get_work_dir() -> Path:
    # Auto-detect: prefer the directory this script lives in's parent,
    # falling back to ~/sprecher
    script_dir = Path(__file__).resolve().parent  # .../sprecher/scripts
    sprecher_root = script_dir.parent
    if (sprecher_root / "app").exists() or (sprecher_root / "core").exists():
        return sprecher_root
    return Path(os.environ.get("SPRECHER_WORK_DIR", "~/sprecher")).expanduser()


def get_db_path() -> Path:
    return Path(os.environ.get("SPRECHER_DB_PATH", str(get_work_dir() / "sprecher.db")))


def install(source_dir: Path, dry_run: bool = False, skip_copy: bool = False) -> None:
    """Install Ephergent voices into Sprecher."""
    work_dir = get_work_dir()
    db_path = get_db_path()
    voices_dir = work_dir / "data" / "voices" / "ephergent"
    voices_dir.mkdir(parents=True, exist_ok=True)

    print(f"Work dir:    {work_dir}")
    print(f"DB path:     {db_path}")
    print(f"Voices dir:  {voices_dir}")
    print(f"Source dir:  {source_dir}")
    print()

    if not skip_copy:
        # Copy reference audio files
        for slug, char in CHARACTERS.items():
            src_wav = source_dir / char["ref_audio"]
            dst_wav = voices_dir / f"{slug}_ref.wav"
            if not src_wav.exists():
                print(f"  [SKIP] {slug}: {src_wav} not found")
                continue
            if dry_run:
                print(f"  [DRY] Would copy {src_wav} -> {dst_wav}")
            else:
                shutil.copy2(src_wav, dst_wav)
                print(f"  [OK]   {slug}: copied {src_wav.name} -> {dst_wav.name}")

    # Register in DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Ensure voices table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            engine TEXT DEFAULT 'qwen',
            voice_type TEXT DEFAULT 'ephergent',
            voice_key TEXT,
            language TEXT DEFAULT 'en-us',
            voice_description TEXT,
            ref_audio_path TEXT,
            ref_text TEXT,
            sample_audio_path TEXT,
            speaking_style TEXT,
            emotional_range TEXT,
            is_system INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    import json
    for slug, char in CHARACTERS.items():
        ref_audio_path = str(voices_dir / f"{slug}_ref.wav")

        # Check if already exists
        row = cursor.execute(
            "SELECT id FROM voices WHERE slug=?", (slug,)
        ).fetchone()
        if row:
            print(f"  [EXISTS] {slug}: already in DB, skipping")
            continue

        if dry_run:
            print(f"  [DRY] Would insert voice '{char['name']}' (slug={slug})")
            continue

        cursor.execute("""
            INSERT INTO voices (
                name, slug, engine, voice_type, voice_key,
                language, voice_description, ref_audio_path, ref_text,
                speaking_style, emotional_range
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            char["name"],
            slug,
            "qwen",
            "clone",
            f"ephergent_{slug}",
            "en-us",
            char["voice_description"],
            ref_audio_path,
            char["ref_text"],
            char["speaking_style"],
            json.dumps(char["emotional_range"]),
        ))
        print(f"  [DB]    {slug}: inserted voice id={cursor.lastrowid}")

    conn.commit()
    conn.close()
    print(f"\nDone. {len(CHARACTERS)} voices registered.")


def main():
    parser = argparse.ArgumentParser(description="Install Ephergent voices into Sprecher")
    parser.add_argument("--source", type=Path, default=None,
                        help="Source directory containing ephergent_voices/ (default: auto-detect)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without making changes")
    parser.add_argument("--skip-copy", action="store_true",
                        help="Skip copying audio files (DB only)")
    args = parser.parse_args()

    # Auto-detect source
    if args.source:
        source_dir = args.source  # use --source path exactly as given
    else:
        candidates = [
            Path("/home/debian/Downloads/ai_speech/WeirDing/ephergent_voices"),
            Path("/home/debian/Documents/The_Ephergent_Archive/ephergent_voices"),
            Path.home() / "Downloads/ai_speech/WeirDing/ephergent_voices",
        ]
        source_dir = next((p for p in candidates if p.exists()), None)
        if not source_dir:
            print("ERROR: Could not find ephergent_voices directory.")
            print("  Tried:", [str(p) for p in candidates])
            print("  Use --source to specify manually.")
            sys.exit(1)

    print(f"Installing Ephergent voices from: {source_dir}")
    if args.dry_run:
        print("[DRY RUN]\n")
    install(source_dir, dry_run=args.dry_run, skip_copy=args.skip_copy)


if __name__ == "__main__":
    main()
