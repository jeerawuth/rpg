# world/spawn_manager.py
# จัดการ wave / timing การเกิดศัตรูจาก enemy_spawns ใน LevelData

from __future__ import annotations

from typing import Any, Dict, List

from entities.enemy_node import EnemyNode
from entities.born_effect_node import BornEffectNode   # 💡 เพิ่ม import ตรงนี้
from world.level_data import LevelData


class SpawnManager:
    def __init__(self, game, level_data: LevelData,
                 enemy_group, all_sprites_group) -> None:
        """
        game             = GameApp
        level_data       = LevelData ที่ได้จาก load_level("level01")
        enemy_group      = pygame.sprite.Group() สำหรับศัตรู
        all_sprites_group= group รวมทุก sprite
        """
        self.game = game
        self.enemy_group = enemy_group
        self.all_sprites_group = all_sprites_group

        self._elapsed: float = 0.0   # เวลาในด่าน (วินาที)
        self._schedule: List[Dict[str, Any]] = []

        # สร้างตาราง spawn จาก enemy_spawns ใน level_data
        for spawn in level_data.enemy_spawns:
            spawn_time = float(spawn.get("spawn_time", 0.0))  # เวลาเกิดศัตรูจริง
            enemy_type = spawn["type"]
            pos = tuple(spawn["pos"])

            # ---------- Event 1: สร้าง BornEffectNode ล่วงหน้า 1.5 วิ ----------
            # เงื่อนไขใหม่: ถ้า spawn_time == 0 → ไม่ต้องสร้าง BornEffectNode
            if spawn_time > 0.0:
                effect_time = max(0.0, spawn_time - 1.5)
                self._schedule.append({
                    "time": effect_time,
                    "kind": "born_effect",
                    "type": enemy_type,
                    "pos": pos,
                    "spawned": False,
                })

            # ---------- Event 2: สร้าง Enemy จริง (ทุกกรณี) ----------
            self._schedule.append({
                "time": spawn_time,
                "kind": "enemy",
                "type": enemy_type,
                "pos": pos,
                "spawned": False,
            })


    @property
    def is_finished(self) -> bool:
        """คืน True ถ้า spawn ครบทุกตัวแล้ว (ไม่มีตัวรอเกิดแล้ว)"""
        if not self._schedule:
            return True
        return all(entry["spawned"] for entry in self._schedule)

    def reset(self) -> None:
        """รีเซ็ตเวลาและสถานะ spawn (ถ้าจะใช้ซ้ำซ้อนด่าน)"""
        self._elapsed = 0.0
        for entry in self._schedule:
            entry["spawned"] = False

    def update(self, dt: float) -> None:
        """ให้ GameScene เรียกทุกเฟรม เพื่อเช็คว่าถึงเวลาสร้างศัตรูตัวไหนหรือยัง"""
        if not self._schedule:
            return

        self._elapsed += dt

        for entry in self._schedule:
            if entry["spawned"]:
                continue

            # ยังไม่ถึงเวลา spawn → หยุด loop ได้เลย (เพราะ list ถูก sort แล้ว)
            if self._elapsed < entry["time"]:
                break

            # เช็คชนิด event
            if entry["kind"] == "born_effect":
                # สร้างเอฟเฟกต์แจ้งเกิดศัตรู (ใส่แค่ all_sprites พอ)
                BornEffectNode(
                    self.game,
                    entry["pos"],
                    self.all_sprites_group,
                )

            elif entry["kind"] == "enemy":
                # ถึงเวลาแล้ว → สร้าง EnemyNode ใส่ group
                EnemyNode(
                    self.game,
                    entry["pos"],
                    self.all_sprites_group,
                    self.enemy_group,
                    enemy_id=entry["type"],
                )

            entry["spawned"] = True
