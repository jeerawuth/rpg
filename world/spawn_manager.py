# world/spawn_manager.py
# จัดการ wave / timing การเกิดศัตรูจาก enemy_spawns ใน LevelData

from __future__ import annotations

from typing import Any, Dict, List

from entities.enemy_node import EnemyNode
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
            spawn_time = float(spawn.get("spawn_time", 0.0))  # ถ้าไม่มี field ใช้ 0

            self._schedule.append({
                "time": spawn_time,
                "type": spawn["type"],
                "pos": tuple(spawn["pos"]),
                "spawned": False,
            })

        # เรียงตามเวลาไว้ก่อน
        self._schedule.sort(key=lambda e: e["time"])

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

            # ถึงเวลาแล้ว → สร้าง EnemyNode ใส่ group
            EnemyNode(
                self.game,
                entry["pos"],
                self.all_sprites_group,
                self.enemy_group,
                enemy_id=entry["type"],
            )
            entry["spawned"] = True
