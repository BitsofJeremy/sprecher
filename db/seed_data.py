"""Seed database with Kokoro preset voices and system voices."""

import aiosqlite
from typing import Any

# Kokoro voice list from kokoro-hook with metadata
KOKORO_VOICES = [
    {"key": "bf_isabella", "name": "Isabella", "gender": "female", "lang": "en-us", "description": "Warm, versatile female voice"},
    {"key": "bf_emma", "name": "Emma", "gender": "female", "lang": "en-us", "description": "Bright, friendly female voice"},
    {"key": "bf_sarah", "name": "Sarah", "gender": "female", "lang": "en-us", "description": "Professional female voice"},
    {"key": "bf_nicole", "name": "Nicole", "gender": "female", "lang": "en-us", "description": "Calm, reassuring female voice"},
    {"key": "bf_mia", "name": "Mia", "gender": "female", "lang": "en-us", "description": "Young, energetic female voice"},
    {"key": "bf_rebecca", "name": "Rebecca", "gender": "female", "lang": "en-us", "description": "British female voice"},
    {"key": "bf_zoey", "name": "Zoey", "gender": "female", "lang": "en-us", "description": "Casual American female"},
    {"key": "bf_luna", "name": "Luna", "gender": "female", "lang": "en-us", "description": "Soft, gentle female voice"},
    {"key": "bf_ashley", "name": "Ashley", "gender": "female", "lang": "en-us", "description": "Professional business female"},
    {"key": "bf_ava", "name": "Ava", "gender": "female", "lang": "en-us", "description": "Expressive female voice"},
    {"key": "bf_olivia", "name": "Olivia", "gender": "female", "lang": "en-us", "description": "Authoritative female voice"},
    {"key": "bf_natasha", "name": "Natasha", "gender": "female", "lang": "en-us", "description": "Russian-influenced female"},
    {"key": "bf_victoria", "name": "Victoria", "gender": "female", "lang": "en-us", "description": "Elegant female voice"},
    {"key": "bf_chloe", "name": "Chloe", "gender": "female", "lang": "en-us", "description": "Youthful female voice"},
    {"key": "bf_fem_v2", "name": "Female v2", "gender": "female", "lang": "en-us", "description": "Enhanced female voice"},
    {"key": "af_bella", "name": "Bella", "gender": "female", "lang": "en-us", "description": "Sweet female voice"},
    {"key": "af_nicole", "name": "Nicole", "gender": "female", "lang": "en-us", "description": "Clear female voice"},
    {"key": "af_sarah", "name": "Sarah", "gender": "female", "lang": "en-us", "description": "MidAtlantic female voice"},
    {"key": "af_sky", "name": "Sky", "gender": "female", "lang": "en-us", "description": "Upbeat female voice"},
    {"key": "am_adam", "name": "Adam", "gender": "male", "lang": "en-us", "description": "Deep male voice"},
    {"key": "am_michael", "name": "Michael", "gender": "male", "lang": "en-us", "description": "Professional male voice"},
    {"key": "am_eric", "name": "Eric", "gender": "male", "lang": "en-us", "description": "Casual male voice"},
    {"key": "am_andrew", "name": "Andrew", "gender": "male", "lang": "en-us", "description": "Deep baritone male"},
    {"key": "am_robert", "name": "Robert", "gender": "male", "lang": "en-us", "description": "Authoritative male voice"},
    {"key": "am_david", "name": "David", "gender": "male", "lang": "en-us", "description": "British male voice"},
    {"key": "am_alex", "name": "Alex", "gender": "male", "lang": "en-us", "description": "Versatile male voice"},
    {"key": "am_arthur", "name": "Arthur", "gender": "male", "lang": "en-us", "description": "Mature male voice"},
    {"key": "am_liam", "name": "Liam", "gender": "male", "lang": "en-us", "description": "Young adult male"},
    {"key": "am_peter", "name": "Peter", "gender": "male", "lang": "en-us", "description": "Thoughtful male voice"},
    {"key": "am_william", "name": "William", "gender": "male", "lang": "en-us", "description": "Formal male voice"},
    {"key": "bf_heatmap_v2", "name": "Heatmap v2", "gender": "female", "lang": "en-us", "description": "Heatmap-based female v2"},
    {"key": "bf_sarah_v2", "name": "Sarah v2", "gender": "female", "lang": "en-us", "description": "Sarah enhanced version"},
    {"key": "bf_heat_emma", "name": "Heat Emma", "gender": "female", "lang": "en-us", "description": "Heatmap-based Emma"},
    {"key": "af_heat_nicole", "name": "Heat Nicole", "gender": "female", "lang": "en-us", "description": "Heatmap-based Nicole"},
    {"key": "af_heat_sarah", "name": "Heat Sarah", "gender": "female", "lang": "en-us", "description": "Heatmap-based Sarah"},
    {"key": "am_heat_eric", "name": "Heat Eric", "gender": "male", "lang": "en-us", "description": "Heatmap-based Eric"},
    {"key": "bf_alto_v2", "name": "Alto v2", "gender": "female", "lang": "en-us", "description": "Lower female voice v2"},
    {"key": "bf_bella_v2", "name": "Bella v2", "gender": "female", "lang": "en-us", "description": "Bella enhanced v2"},
    {"key": "bf_heat_alto", "name": "Heat Alto", "gender": "female", "lang": "en-us", "description": "Heatmap-based alto"},
    {"key": "af_bridge", "name": "Bridge", "gender": "female", "lang": "en-us", "description": "Neutral female bridge voice"},
    {"key": "am_bridge", "name": "Bridge M", "gender": "male", "lang": "en-us", "description": "Neutral male bridge voice"},
    {"key": "bf_heat_v2", "name": "Heat v2", "gender": "female", "lang": "en-us", "description": "Heatmap female v2"},
    {"key": "af_heat_v2", "name": "Heat v2 (af)", "gender": "female", "lang": "en-us", "description": "Heatmap female alternate v2"},
    {"key": "bf_emma_v1", "name": "Emma v1", "gender": "female", "lang": "en-us", "description": "Original Emma voice"},
    {"key": "bf_heat_emma_v2", "name": "Heat Emma v2", "gender": "female", "lang": "en-us", "description": "Heatmap Emma v2"},
    {"key": "af_sarah_v2", "name": "Sarah v2 (af)", "gender": "female", "lang": "en-us", "description": "Sarah alternate v2"},
    {"key": "af_bella_v2", "name": "Bella v2 (af)", "gender": "female", "lang": "en-us", "description": "Bella alternate v2"},
    {"key": "af_nicole_v2", "name": "Nicole v2", "gender": "female", "lang": "en-us", "description": "Nicole enhanced v2"},
    {"key": "af_heat_v3", "name": "Heat v3", "gender": "female", "lang": "en-us", "description": "Heatmap female v3"},
    {"key": "bf_heat_v3", "name": "Heat v3 (bf)", "gender": "female", "lang": "en-us", "description": "Heatmap female alternate v3"},
    {"key": "af_heat_alto", "name": "Heat Alto (af)", "gender": "female", "lang": "en-us", "description": "Heatmap alto alternate"},
    {"key": "bf_heat_alto_v2", "name": "Heat Alto v2", "gender": "female", "lang": "en-us", "description": "Heatmap alto v2"},
    {"key": "am_heat_andy", "name": "Heat Andy", "gender": "male", "lang": "en-us", "description": "Heatmap-based Andy"},
    {"key": "af_heat_andy", "name": "Heat Andy (af)", "gender": "male", "lang": "en-us", "description": "Heatmap Andy alternate"},
]

# System preset voices (user-facing presets combining multiple Kokoro voices)
SYSTEM_PRESETS = [
    {
        "name": "Gentle Blend",
        "slug": "gentle_blend",
        "voice_key": "bf_isabella(0.7)+bf_emma(0.3)",
        "description": "Soft blend of Isabella and Emma for gentle narration",
    },
    {
        "name": "Professional",
        "slug": "professional",
        "voice_key": "am_michael(0.6)+af_nicole(0.4)",
        "description": "Business-appropriate neutral voice",
    },
    {
        "name": "Narrator",
        "slug": "narrator",
        "voice_key": "am_robert",
        "description": "Authoritative narrator voice",
    },
    {
        "name": "Energetic",
        "slug": "energetic",
        "voice_key": "af_sky(0.8)+am_alex(0.2)",
        "description": "Upbeat and energetic speaking style",
    },
]

# Ephergent character voice blends - these give each character their distinct sound
EPHERGENT_CHARACTER_VOICES = [
    {
        "name": "Pixel Paradox",
        "slug": "pixel_paradox",
        "voice_key": "bf_isabella(1.5)+bm_george(1)+af_bella(0.5)+af_sarah(0.5)",
        "description": "Underground journalist voice - warm, versatile, slightly husky with authority",
    },
    {
        "name": "A1 (Arc)",
        "slug": "a1_assistant",
        "voice_key": "bm_lewis(0.8)+bm_george(1.5)+bf_alice(0.4)+am_adam(0.7)+am_onyx(0.4)",
        "description": "British AI assistant - smooth, authoritative with subtle warmth",
    },
    {
        "name": "Clive Stapler",
        "slug": "clive_stapler",
        "voice_key": "am_onyx(0.5)+bm_george(1.3)+bm_lewis(0.7)",
        "description": "Noir detective informant - world-weary, gravelly, wise",
    },
    {
        "name": "Zephyr Glitch",
        "slug": "zephyr_glitch",
        "voice_key": "bm_lewis(0.7)+bf_lily(1)+am_onyx(0.3)+am_puck(0.3)+am_fenrir(0.3)",
        "description": "Manic tech-head - energetic, rapid, with underlying edge",
    },
    {
        "name": "Luminara Usha",
        "slug": "luminara_usha",
        "voice_key": "bf_lily(0.3)+af_nova(0.2)+hf_beta(1.5)",
        "description": "Calm observer - measured, neutral with emerging warmth",
    },
    {
        "name": "Om Kai",
        "slug": "om_kai",
        "voice_key": "hm_omega(1.5)+am_puck(0.8)+bm_lewis(1)",
        "description": "Contemplative guide - deep, serene, unhurried wisdom",
    },
]


async def seed_voices(db: aiosqlite.Connection) -> None:
    """Seed Kokoro preset voices and system presets if not already seeded."""
    # Check if voices already exist
    cursor = await db.execute("SELECT COUNT(*) FROM voices WHERE engine = 'kokoro' AND voice_type = 'preset'")
    row = await cursor.fetchone()
    if row[0] > 0:
        return  # Already seeded

    # Insert Kokoro preset voices
    for voice in KOKORO_VOICES:
        await db.execute(
            """
            INSERT INTO voices (name, slug, engine, voice_type, voice_key, language, voice_description, is_system)
            VALUES (?, ?, 'kokoro', 'preset', ?, ?, ?, 1)
            """,
            (voice["name"], voice["key"], voice["key"], voice["lang"], voice["description"])
        )

    # Insert system presets
    for preset in SYSTEM_PRESETS:
        await db.execute(
            """
            INSERT INTO voices (name, slug, engine, voice_type, voice_key, voice_description, is_system)
            VALUES (?, ?, 'kokoro', 'blend', ?, ?, 1)
            """,
            (preset["name"], preset["slug"], preset["voice_key"], preset["description"])
        )

    # Insert Ephergent character voice blends
    for char_voice in EPHERGENT_CHARACTER_VOICES:
        await db.execute(
            """
            INSERT INTO voices (name, slug, engine, voice_type, voice_key, voice_description, is_system)
            VALUES (?, ?, 'kokoro', 'blend', ?, ?, 1)
            """,
            (char_voice["name"], char_voice["slug"], char_voice["voice_key"], char_voice["description"])
        )

    await db.commit()


async def seed_system_voices(db: aiosqlite.Connection) -> None:
    """Seed default system voice for demo purposes."""
    cursor = await db.execute("SELECT COUNT(*) FROM voices WHERE engine = 'system' AND is_system = 1")
    row = await cursor.fetchone()
    if row[0] > 0:
        return

    await db.execute(
        """
        INSERT INTO voices (name, slug, engine, voice_type, voice_key, voice_description, is_system)
        VALUES ('Default Assistant', 'default_assistant', 'system', 'preset', 'bf_isabella', 'Default Kokoro voice for general use', 1)
        """
    )
    await db.commit()