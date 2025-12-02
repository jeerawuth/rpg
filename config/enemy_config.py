# config/enemy_config.py

from combat.damage_system import Stats

ENEMY_CONFIG: dict[str, dict] = {
    "goblin": {
        "sprite_id": "goblin",
        "stats": Stats(
            max_hp=160,
            hp=100,
            attack=10,
            magic=0,
            armor=3,
            resistances={"fire": 0.1},
            crit_chance=0.05,
            crit_multiplier=1.5,
        ),
        "speed": 180,
        "move_range": 80,
        "aggro_radius": 200,   # <<--- รัศมีมองเห็น / ไล่ตาม (หน่วยเป็นพิกเซล)
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
        "speed": 120,
        "move_range": 800,
        "aggro_radius": 260,   # <<--- รัศมีมองเห็น / ไล่ตาม (หน่วยเป็นพิกเซล)
        "xp_reward": 10,
    },
    "orc": {
        "sprite_id": "orc",
        "stats": Stats(
            max_hp=120,
            hp=100,
            attack=15,
            magic=0,
            armor=3,
            resistances={"fire": 0.2},
            crit_chance=0.05,
            crit_multiplier=1.5,
        ),
        "speed": 100,
        "move_range": 800,
        "aggro_radius": 260,   # <<--- รัศมีมองเห็น / ไล่ตาม (หน่วยเป็นพิกเซล)
        "xp_reward": 10,
    },
    # เพิ่ม enemy ชนิดใหม่ได้เรื่อย ๆ
    # "orc": {...},
    # "bat": {...},
}
