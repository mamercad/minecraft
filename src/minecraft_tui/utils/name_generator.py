# Copyright (c) 2025 Mark Mercado <mamercad@gmail.com>
"""Server name generator utility."""

import random

ADJECTIVES = [
    "ancient",
    "brave",
    "calm",
    "crimson",
    "crystal",
    "dawn",
    "diamond",
    "dragon",
    "emerald",
    "eternal",
    "fire",
    "frozen",
    "golden",
    "hidden",
    "iron",
    "jade",
    "lightning",
    "lunar",
    "magic",
    "mystic",
    "nether",
    "noble",
    "ocean",
    "phantom",
    "royal",
    "shadow",
    "silver",
    "sky",
    "solar",
    "storm",
    "thunder",
    "wild",
]

NOUNS = [
    "anvil",
    "beacon",
    "castle",
    "cave",
    "citadel",
    "crater",
    "creeper",
    "dragon",
    "dungeon",
    "fortress",
    "golem",
    "guardian",
    "island",
    "kingdom",
    "mountain",
    "ore",
    "outpost",
    "palace",
    "peak",
    "portal",
    "realm",
    "ruins",
    "shrine",
    "spire",
    "stronghold",
    "temple",
    "tower",
    "village",
    "volcano",
    "world",
]


def generate_server_name() -> str:
    """Generate a random server name in the format <adjective>-<noun>.

    Returns:
        A random server name like "crystal-fortress" or "brave-dragon"
    """
    adjective = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    return f"{adjective}-{noun}"
