# world/level_data.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Any
import json
import os


@dataclass
class LevelData:
    """
    เก็บข้อมูลของเลเวลที่โหลดมาจากไฟล์ JSON
    """
    id: str
    tileset: str
    tile_size: int
    width: int
    height: int
    layers: Dict[str, List[List[int]]]
    player_spawn: Tuple[int, int]

    # enemy_spawns: list ของ dict เช่น { "type": "goblin", "pos": [x, y] }
    enemy_spawns: List[Dict[str, Any]]

    # item_spawns: list ของ dict เช่น
    # { "item_id": "bow_power_1", "pos": [x, y], "amount": 1 }
    item_spawns: List[Dict[str, Any]]

    # id ของเลเวลถัดไป (ไม่มีให้เป็น "")
    next_level: str = ""

    # enemy_spawns: list ของ dict เช่น { "type": "goblin", "pos": [x, y] }
    enemy_spawns: List[Dict[str, Any]]

    # item_spawns: list ของ dict เช่น
    # { "item_id": "bow_power_1", "pos": [x, y], "amount": 1 }
    item_spawns: List[Dict[str, Any]]



def _get_data_dir() -> str:
    """
    หา path ของโฟลเดอร์ assets/data จากตำแหน่งไฟล์นี้
    โครงสร้างโปรเจ็กต์ประมาณ:
        rpg/
          main.py
          world/level_data.py
          assets/data/level01.json
    """
    # โฟลเดอร์ของไฟล์ level_data.py (เช่น rpg/world)
    here = os.path.dirname(__file__)
    # root ของโปรเจ็กต์ (ขึ้นไป 1 ระดับจาก world/)
    project_root = os.path.dirname(here)
    # assets/data
    data_dir = os.path.join(project_root, "assets", "data")
    return data_dir


def load_level(name: str) -> LevelData:
    """
    โหลดข้อมูลเลเวลจากไฟล์ JSON ใน assets/data
    ตัวอย่าง:
        load_level("level01") -> โหลด assets/data/level01.json
    """
    data_dir = _get_data_dir()

    # ถ้า name ไม่มี .json ให้เติมให้
    if not name.endswith(".json"):
        filename = f"{name}.json"
    else:
        filename = name

    full_path = os.path.join(data_dir, filename)

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Level JSON not found: {full_path}")

    with open(full_path, "r", encoding="utf-8") as f:
        raw: Dict[str, Any] = json.load(f)

    # ---------- enemy_spawns: รองรับทั้งรูปแบบเก่า/ใหม่ ----------
    # รูปแบบใหม่ที่เราใช้ตอนนี้ใน level01.json:
    #   "enemy_spawns": [
    #     { "type": "goblin", "pos": [656, 368] },
    #     { "type": "slime_green", "pos": [400, 320] }
    #   ]
    #
    # รูปแบบเก่า (ถ้ายังมีเลเวลอื่นใช้):
    #   "enemy_spawns": [
    #     [656, 368],
    #     [976, 592]
    #   ]
    raw_enemy_spawns = raw.get("enemy_spawns", [])

    enemy_spawns: List[Dict[str, Any]] = []
    for entry in raw_enemy_spawns:
        if isinstance(entry, dict):
            # รูปแบบใหม่: ใช้ตามที่ JSON ให้มา
            # คาดหวังว่า entry มี key: "type", "pos"
            enemy_spawns.append(entry)
        else:
            # รูปแบบเก่า: [x, y] -> แปลงให้เป็น dict
            # กำหนด type เริ่มต้นเป็น "goblin"
            x, y = entry
            enemy_spawns.append({
                "type": "goblin",
                "pos": [x, y],
            })

    # ---------- item_spawns ----------
    # รองรับรูปแบบใหม่ใน level01.json:
    #   "item_spawns": [
    #     { "item_id": "bow_power_1", "pos": [276, 176], "amount": 1 },
    #     { "item_id": "shield", "pos": [296, 376], "amount": 1 }
    #   ]
    raw_item_spawns = raw.get("item_spawns", [])

    item_spawns: List[Dict[str, Any]] = []
    for entry in raw_item_spawns:
        if isinstance(entry, dict):
            # ถ้าไม่ได้ใส่ amount มาใน JSON ให้ default = 1
            if "amount" not in entry:
                entry = {**entry, "amount": 1}
            item_spawns.append(entry)
        else:
            # เผื่ออนาคตมีรูปแบบง่าย ๆ เช่น [x, y, "item_id"]
            # หรือ [x, y] อย่างน้อยก็ไม่ให้เกมพัง
            if len(entry) >= 3:
                x, y, item_id = entry[:3]
            else:
                x, y = entry
                item_id = "unknown"

            item_spawns.append({
                "item_id": item_id,
                "pos": [x, y],
                "amount": 1,
            })


    return LevelData(
        id=raw["id"],
        tileset=raw["tileset"],
        tile_size=raw["tile_size"],
        width=raw["width"],
        height=raw["height"],
        layers=raw["layers"],
        player_spawn=tuple(raw["player_spawn"]),
        enemy_spawns=enemy_spawns,
        item_spawns=item_spawns,
        next_level=raw.get("next_level", "")
    )


