# config/enemy_config.py

from combat.damage_system import Stats

ENEMY_CONFIG: dict[str, dict] = {
    "goblin": {
        "sprite_id": "goblin",
        "stats": Stats(
            max_hp=60,
            hp=60,
            attack=10,
            magic=0,
            armor=3,
            resistances={"fire": 0.1},
            crit_chance=0.05,
            crit_multiplier=1.5,
        ),
        "speed": 80,
        "move_range": 80,
        "xp_reward": 10,
    },
    "slime_green": {
        "sprite_id": "slime_green",
        "stats": Stats(
            max_hp=60,
            hp=60,
            attack=10,
            magic=0,
            armor=3,
            resistances={"fire": 0.1},
            crit_chance=0.05,
            crit_multiplier=1.5,
        ),
        "speed": 100,
        "move_range": 800,
        "xp_reward": 10,
    },
    # เพิ่ม enemy ชนิดใหม่ได้เรื่อย ๆ
    # "orc": {...},
    # "bat": {...},
}
