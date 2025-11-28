# entities/enemy_node.py
from __future__ import annotations

import pygame

from .animated_node import AnimatedNode
from combat.damage_system import Stats, DamagePacket, compute_damage, DamageResult
from combat.status_effect_system import StatusEffectManager


class EnemyNode(AnimatedNode):
    def __init__(self, game, pos: tuple[int, int], *groups) -> None:
        # เตรียมเฟรมสำหรับ AnimatedNode (กราฟิกชั่วคราว 1 เฟรม)
        base_image = pygame.Surface((28, 28), pygame.SRCALPHA)
        base_image.fill((200, 40, 40))
        frames = [base_image]

        # เรียก AnimatedNode.__init__
        super().__init__(frames, 0.15, True, *groups)

        self.game = game

        # ---------- SFX ----------
        # ใช้ ResourceManager เหมือน player_node
        self.sfx_hit = self.game.resources.load_sound("sfx/enemy_hit.wav")
        self.sfx_hit.set_volume(0.7)

        # ตั้งตำแหน่งเริ่มต้นให้ศัตรู
        self.rect.center = pos

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

        # เล่นเสียงตอนศัตรูโดนโจมตี
        if hasattr(self, "sfx_hit"):
            self.sfx_hit.play()
            
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
        # เรียกใช้ของ AnimatedNode
        super().update(dt)
