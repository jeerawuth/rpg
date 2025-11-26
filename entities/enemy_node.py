# entities/enemy_node.py
from __future__ import annotations

import pygame

from .node_base import NodeBase
from combat.damage_system import Stats, DamagePacket, compute_damage, DamageResult
from combat.status_effect_system import StatusEffectManager


class EnemyNode(NodeBase):
    def __init__(self, game, pos: tuple[int, int], *groups) -> None:
        super().__init__(*groups)
        self.game = game

        # กราฟิกชั่วคราว: สี่เหลี่ยมสีแดง
        self.image = pygame.Surface((28, 28))
        self.image.fill((200, 40, 40))
        self.rect = self.image.get_rect(center=pos)

        # combat stats
        self.stats = Stats(
            max_hp=60,
            hp=60,
            attack=10,
            magic=0,
            armor=3,
            resistances={"fire": 0.1},
            crit_chance=0.05,
            crit_multiplier=1.5,
        )

        # status effects
        self.status = StatusEffectManager(self)

        # AI เล็กน้อย (เดินซ้าย-ขวา)
        self.speed = 80
        self.direction = 1  # 1 = ขวา, -1 = ซ้าย
        self.move_range = 80
        self._origin_x = pos[0]

    # ---------- AI / MOVE ----------
    def _patrol(self, dt: float) -> None:
        self.rect.x += int(self.direction * self.speed * dt)
        if abs(self.rect.x - self._origin_x) > self.move_range:
            self.direction *= -1

    # ---------- COMBAT ----------
    def take_hit(self, attacker_stats: Stats, damage_packet: DamagePacket) -> DamageResult:
        """
        โดนโจมตีจาก attacker
        - apply status modifier (ถ้าต้องใช้)
        - คำนวนดาเมจ
        - เช็คตาย
        """
        # ถ้ามี debuff "damage_taken" ก็ใช้ปรับ multiplier ใน packet ได้
        dmg_mult = self.status.get_multiplier("damage_taken")
        damage_packet.attacker_multiplier *= dmg_mult

        result = compute_damage(attacker_stats, self.stats, damage_packet)

        print(
            f"Enemy hit for {result.final_damage} dmg "
            f"({'CRIT' if result.is_crit else 'normal'}) "
            f"HP: {self.stats.hp}/{self.stats.max_hp}"
        )

        if result.killed:
            print("Enemy died!")
            self.kill()
            # TODO: ดรอป loot, ให้ XP ฯลฯ

        return result

    # ---------- UPDATE ----------
    def update(self, dt: float) -> None:
        self.status.update(dt)
        self._patrol(dt)
