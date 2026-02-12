# config/enemy_config.py

from combat.damage_system import Stats

ENEMY_CONFIG: dict[str, dict] = {
    "goblin": {
        "sprite_id": "goblin",
        "scale": 0.35,
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
        "scale": 0.5,  # ตัวใหญ่กว่าปกติ (ปกติ 0.25)
        "stats": Stats(
            max_hp=1000,
            hp=1000,
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
        # Config สำหรับ Boss AI
        "type": "boss",
        "attack_config": {
            "range": 350,           # ระยะเริ่มโจมตี
            "cooldown": 3.0,        # เวลาพักระหว่างท่า
            "charge_time": 1.0,     # เวลาชาร์จ (วงแดง)
            "damage_radius": 150,   # รัศมีระเบิดพลัง
            "damage_multiplier": 1.5, # ความแรงท่าไม้ตาย (คูณจาก base attack)
        }
    },
    "troll": {
        "sprite_id": "troll",
        "stats": Stats(
            max_hp=200,
            hp=200,
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
        "scale": 0.2,  # ตัวเล็กกว่าปกติ (ปกติ 0.25)
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
    "demona": {
        "sprite_id": "demona",
        "stats": Stats(
            max_hp=200,
            hp=200,
            attack=30,
            magic=0,
            armor=3,
            resistances={"fire": 0.4},
            crit_chance=0.05,
            crit_multiplier=1.5,
        ),
        "speed": 100,
        "move_range": 700,
        "aggro_radius": 660,   # <<--- รัศมีมองเห็น / ไล่ตาม (หน่วยเป็นพิกเซล)
        "xp_reward": 10,
    },
    "green": {
        "sprite_id": "green",
        "scale": 0.2,
        "stats": Stats(
            max_hp=100,
            hp=100,
            attack=10,
            magic=0,
            armor=3,
            resistances={"fire": 0.4},
            crit_chance=0.05,
            crit_multiplier=1.5,
        ),
        "speed": 80,
        "move_range": 600,
        "aggro_radius": 560,   # <<--- รัศมีมองเห็น / ไล่ตาม (หน่วยเป็นพิกเซล)
        "xp_reward": 10,
    },
    "spider": {
        "sprite_id": "spider",
        "stats": Stats(
            max_hp=40,
            hp=40,
            attack=10,
            magic=0,
            armor=3,
            resistances={"fire": 0.4},
            crit_chance=0.05,
            crit_multiplier=1.5,
        ),
        "speed": 150,
        "move_range": 700,
        "aggro_radius": 660,   # <<--- รัศมีมองเห็น / ไล่ตาม (หน่วยเป็นพิกเซล)
        "xp_reward": 10,
    },
    # เพิ่ม enemy ชนิดใหม่ได้เรื่อย ๆ
    # "orc": {...},
    # "bat": {...},
}
