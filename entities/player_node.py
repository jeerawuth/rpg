# entities/player_node.py
from __future__ import annotations

import pygame

from .node_base import NodeBase
from combat.damage_system import Stats, DamagePacket
from combat.status_effect_system import StatusEffectManager
from config.settings import PLAYER_SPEED
from items.inventory import Inventory
from items.equipment import Equipment
from items.item_database import ITEM_DB


class PlayerNode(NodeBase):
    def __init__(
        self,
        game,
        pos: tuple[int, int],
        projectile_group: pygame.sprite.Group,
        *groups,
    ) -> None:
        super().__init__(*groups)
        self.game = game
        self.projectile_group = projectile_group

        # กราฟิกชั่วคราว: วงกลมสีขาว
        radius = 16
        self.image = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (240, 240, 240), (radius, radius), radius)
        self.rect = self.image.get_rect(center=pos)

        # combat stats
        self.stats = Stats(
            max_hp=100,
            hp=100,
            attack=20,
            magic=5,
            armor=5,
            resistances={"fire": 0.2},
            crit_chance=0.1,
            crit_multiplier=1.7,
        )

        # status effects (buff/debuff)
        self.status = StatusEffectManager(self)

        # INVENTORY & EQUIPMENT
        self.inventory = Inventory(size=20)
        self.equipment = Equipment()

        # ของเริ่มต้น
        self.inventory.add_item("potion_small", 5)
        self.inventory.add_item("sword_basic", 1)
        self.inventory.add_item("sword_iron", 1)

        # movement
        self.move_speed = PLAYER_SPEED
        self.velocity = pygame.Vector2(0, 0)

        # direction เอาไว้ใช้กับการยิง (เริ่มต้นมองขวา)
        self.facing = pygame.Vector2(1, 0)

    # ---------- INPUT + MOVE ----------
    def _handle_input(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        self.velocity.update(0, 0)

        if keys[pygame.K_w]:
            self.velocity.y -= 1
        if keys[pygame.K_s]:
            self.velocity.y += 1
        if keys[pygame.K_a]:
            self.velocity.x -= 1
        if keys[pygame.K_d]:
            self.velocity.x += 1

        if self.velocity.length_squared() > 0:
            self.velocity = self.velocity.normalize() * self.move_speed * dt
            self.rect.centerx += int(self.velocity.x)
            self.rect.centery += int(self.velocity.y)
            # อัปเดตทิศที่หัน
            self.facing = self.velocity.normalize()

    # ---------- COMBAT ----------
    def shoot(self) -> None:
        """ยิง projectile ไปในทิศทางที่ player กำลังหันอยู่ (self.facing)."""
        from .projectile_node import ProjectileNode

        direction = self.facing
        if direction.length_squared() == 0:
            direction = pygame.Vector2(1, 0)  # ถ้ายังไม่เคยเดิน ให้ยิงไปทางขวา

        # คำนวณ base damage จากอาวุธที่ใส่อยู่
        weapon = self.equipment.get_item("main_hand")
        if weapon and weapon.item_type == "weapon":
            # ตัวอย่างง่าย ๆ: ต่างกันแค่เลข base
            if weapon.id == "sword_basic":
                base_damage = 15
            elif weapon.id == "sword_iron":
                base_damage = 25
            else:
                base_damage = 18
        else:
            base_damage = 10  # ชกมือเปล่า

        packet = DamagePacket(
            base=base_damage,
            damage_type="physical",
            scaling_attack=0.8,
        )

        ProjectileNode(
            self,                 # owner
            self.rect.center,     # pos
            direction,            # direction
            450,                  # speed
            packet,               # damage_packet
            1.5,                  # lifetime
            self.projectile_group,
            self.game.all_sprites,
        )

    def take_damage(self, attacker_stats: Stats, result_damage: int) -> None:
        """ไว้ให้ enemy ใช้ตอนโจมตี player (ตอนนี้ยังไม่ถูกเรียกใช้)."""
        self.stats.hp = max(0, self.stats.hp - result_damage)
        if self.stats.is_dead():
            print("Player died!")

    # ---------- UPDATE ----------
    def update(self, dt: float) -> None:
        self.status.update(dt)
        self._handle_input(dt)
