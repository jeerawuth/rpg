# config/player_config.py

from combat.damage_system import Stats

PLAYER_CONFIG: dict[str, dict] = {
    "knight": {
        "speed": 250,
        "scale": 1.0,
        "stats": Stats(
            max_hp=100,
            hp=100,
            attack=20,
            magic=5,
            armor=5,
            resistances={"physical": 0.1},
            crit_chance=0.1,
            crit_multiplier=1.7,
        ),
        "description": "Standard melee warrior. Balanced usage."
    },
    "wizard": {
        "speed": 300,
        "scale": 0.6,
        "stats": Stats(
            max_hp=80,
            hp=80,
            attack=10,
            magic=25,
            armor=2,
            resistances={"physical": 0.0, "fire": 0.2},
            crit_chance=0.15,
            crit_multiplier=2.0,
        ),
        "description": "High magic damage, low defense."
    },
     # Fallback spec if needed
    "default": {
        "speed": 220,
        "stats": Stats(
            max_hp=100,
            hp=100,
            attack=20,
            magic=5,
            armor=5,
            resistances={"physical": 0.0},
            crit_chance=0.1,
            crit_multiplier=1.5,
        ),
    }

}
