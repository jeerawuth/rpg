# config/enemy_config.py

from combat.damage_system import Stats

ENEMY_CONFIG: dict[str, dict] = {
    "goblin": {
        "sprite_id": "goblin",
        "stats": Stats(
            max_hp=40,
            hp=40,
            attack=10,
            magic=0,
            armor=3,
            resistances={"fire": 0.1},
            crit_chance=0.05,
            crit_multiplier=1.5,
        ),
        "speed": 90,
        "move_range": 280,
        "aggro_radius": 700,   # <<--- รัศมีมองเห็น / ไล่ตาม (หน่วยเป็นพิกเซล)
        "xp_reward": 10,
    },
    "slime_green": {
        "sprite_id": "slime_green",
        "stats": Stats(
            max_hp=50,
            hp=50,
            attack=10,
            magic=0,
            armor=3,
            resistances={"fire": 0.1},
            crit_chance=0.05,
            crit_multiplier=1.5,
        ),
        "speed": 120,
        "move_range": 800,
        "aggro_radius": 600,   # <<--- รัศมีมองเห็น / ไล่ตาม (หน่วยเป็นพิกเซล)
        "xp_reward": 10,
    },
    "orc": {
        "sprite_id": "orc",
        "stats": Stats(
            max_hp=60,
            hp=60,
            attack=15,
            magic=0,
            armor=3,
            resistances={"fire": 0.2},
            crit_chance=0.05,
            crit_multiplier=1.5,
        ),
        "speed": 110,
        "move_range": 800,
        "aggro_radius": 660,   # <<--- รัศมีมองเห็น / ไล่ตาม (หน่วยเป็นพิกเซล)
        "xp_reward": 10,
    },
    "boss_orc": {
        "sprite_id": "boss_orc",
        "stats": Stats(
            max_hp=80,
            hp=80,
            attack=35,
            magic=0,
            armor=3,
            resistances={"fire": 0.2},
            crit_chance=0.05,
            crit_multiplier=1.5,
        ),
        "speed": 90,
        "move_range": 800,
        "aggro_radius": 660,   # <<--- รัศมีมองเห็น / ไล่ตาม (หน่วยเป็นพิกเซล)
        "xp_reward": 10,
    },
    "troll": {
        "sprite_id": "troll",
        "stats": Stats(
            max_hp=90,
            hp=90,
            attack=40,
            magic=0,
            armor=3,
            resistances={"fire": 0.4},
            crit_chance=0.05,
            crit_multiplier=1.5,
        ),
        "speed": 90,
        "move_range": 800,
        "aggro_radius": 660,   # <<--- รัศมีมองเห็น / ไล่ตาม (หน่วยเป็นพิกเซล)
        "xp_reward": 10,
    },
    "undead": {
        "sprite_id": "undead",
        "stats": Stats(
            max_hp=300,
            hp=300,
            attack=40,
            magic=0,
            armor=3,
            resistances={"fire": 0.4},
            crit_chance=0.05,
            crit_multiplier=1.5,
        ),
        "speed": 100,
        "move_range": 800,
        "aggro_radius": 660,   # <<--- รัศมีมองเห็น / ไล่ตาม (หน่วยเป็นพิกเซล)
        "xp_reward": 10,
    },
    # เพิ่ม enemy ชนิดใหม่ได้เรื่อย ๆ
    # "orc": {...},
    # "bat": {...},
}
