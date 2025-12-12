# world/spawn_manager.py
# จัดการ wave / timing การเกิดศัตรูจาก enemy_spawns ใน LevelData

from __future__ import annotations

from typing import Any, Dict, List

from entities.enemy_node import EnemyNode
from entities.born_effect_node import BornEffectNode
from world.level_data import LevelData


class SpawnManager:
    def __init__(self, game, level_data: LevelData,
                 enemy_group, all_sprites_group) -> None:
        self.game = game
        self.enemy_group = enemy_group
        self.all_sprites_group = all_sprites_group

        self._elapsed: float = 0.0
        self._schedule: List[Dict[str, Any]] = []

        # ✅ เก็บเอฟเฟ็กต์ที่กำลังเล่นอยู่ แยกตาม spawn_id
        self._active_effects: dict[int, BornEffectNode] = {}

        spawn_id = 0

        for spawn in level_data.enemy_spawns:
            spawn_id += 1

            spawn_time = float(spawn.get("spawn_time", 0.0))
            enemy_type = spawn["type"]
            pos = tuple(spawn["pos"])

            # ถ้ากำหนดเวลาเกิด (>0) -> มี born_effect ก่อน
            if spawn_time > 0.0:
                effect_time = max(0.0, spawn_time - 1.5)
                self._schedule.append({
                    "time": effect_time,
                    "kind": "born_effect",
                    "type": enemy_type,
                    "pos": pos,
                    "spawned": False,
                    "spawn_id": spawn_id,
                })

            # enemy เกิด "หลัง effect จบจริง" (ไม่ต้องตรง spawn_time ก็ได้)
            self._schedule.append({
                "time": spawn_time,
                "kind": "enemy",
                "type": enemy_type,
                "pos": pos,
                "spawned": False,
                "spawn_id": spawn_id,
                "wait_effect": (spawn_time > 0.0),
            })

        # ✅ กันบั๊กเรื่อง break (ในโค้ดเดิมคอมเมนต์บอกว่า sort แล้ว แต่จริง ๆ ยังไม่ sort)
        # และทำให้ born_effect มาก่อน enemy หากเวลาเท่ากัน
        self._schedule.sort(key=lambda e: (e["time"], 0 if e["kind"] == "born_effect" else 1))

    @property
    def is_finished(self) -> bool:
        if not self._schedule:
            return True
        return all(entry["spawned"] for entry in self._schedule)

    def reset(self) -> None:
        self._elapsed = 0.0
        self._active_effects.clear()
        for entry in self._schedule:
            entry["spawned"] = False

    def update(self, dt: float) -> None:
        if not self._schedule:
            return

        self._elapsed += dt

        for entry in self._schedule:
            if entry["spawned"]:
                continue

            if self._elapsed < entry["time"]:
                break

            if entry["kind"] == "born_effect":
                eff = BornEffectNode(
                    self.game,
                    entry["pos"],
                    self.all_sprites_group,
                )
                self._active_effects[entry["spawn_id"]] = eff
                entry["spawned"] = True
                continue

            if entry["kind"] == "enemy":
                # ✅ ถ้ามี born_effect ให้รอจนมัน "จบจริง" (ถูก kill) ก่อน
                if entry.get("wait_effect", False):
                    eff = self._active_effects.get(entry["spawn_id"])
                    if eff is not None and eff.alive():
                        # เอฟเฟ็กต์ยังเล่นอยู่ -> ยังไม่ spawn enemy
                        continue

                EnemyNode(
                    self.game,
                    entry["pos"],
                    self.all_sprites_group,
                    self.enemy_group,
                    enemy_id=entry["type"],
                )

                entry["spawned"] = True
                # cleanup
                self._active_effects.pop(entry["spawn_id"], None)

