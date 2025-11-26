# world/level_data.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Any
import json
import os


@dataclass
class LevelData:
    id: str
    tileset: str
    tile_size: int
    width: int
    height: int
    layers: Dict[str, List[List[int]]]
    player_spawn: Tuple[int, int]
    enemy_spawns: List[Tuple[int, int]]


def load_level(level_id: str, base_path: str = "assets/data") -> LevelData:
    filename = f"{level_id}.json"
    full_path = os.path.join(base_path, filename)

    with open(full_path, "r", encoding="utf-8") as f:
        raw: Dict[str, Any] = json.load(f)

    return LevelData(
        id=raw["id"],
        tileset=raw["tileset"],
        tile_size=raw["tile_size"],
        width=raw["width"],
        height=raw["height"],
        layers=raw["layers"],
        player_spawn=tuple(raw.get("player_spawn", (0, 0))),
        enemy_spawns=[tuple(p) for p in raw.get("enemy_spawns", [])],
    )
