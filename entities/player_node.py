# entities/player_node.py
from __future__ import annotations

import pygame

from .node_base import NodeBase
from combat.damage_system import Stats, DamagePacket
from combat.status_effect_system import StatusEffectManager
from config.settings import PLAYER_SPEED

# ทำให้รันได้แม้ยังไม่ได้ทำระบบ inventory/equipment
try:
    from items.inventory import Inventory
    from items.equipment import Equipment
except ImportError:  # เผื่อคุณยังไม่ได้สร้างไฟล์เหล่านี้
    Inventory = None
    Equipment = None


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

        # --- COMBAT STATS ---
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
        self.status = StatusEffectManager(self)

        # --- INVENTORY / EQUIPMENT (ถ้ามีคลาสให้ใช้) ---
        if Inventory is not None:
            self.inventory = Inventory(size=20)
            # ของเริ่มต้น
            self.inventory.add_item("potion_small", 5)
            self.inventory.add_item("sword_basic", 1)
        else:
            self.inventory = None

        if Equipment is not None:
            self.equipment = Equipment()
        else:
            self.equipment = None

        # --- MOVEMENT & COLLISION ---
        self.move_speed = PLAYER_SPEED          # pixels / second
        self.facing = pygame.Vector2(1, 0)      # ทิศที่หัน (ใช้ตอนยิง)
        self.collision_rects: list[pygame.Rect] = []  # จะได้จาก TileMap

    # ========== COLLISION API ==========
    def set_collision_rects(self, rects) -> None:
        """ให้ GameScene ส่ง list ของกำแพงเข้ามาทุกเฟรม"""
        self.collision_rects = list(rects) if rects is not None else []

    # ========== MOVEMENT + COLLISION ==========
    def _move_with_collision(self, dx: float, dy: float) -> None:
        # แกน X
        self.rect.x += int(dx)
        for block in self.collision_rects:
            if self.rect.colliderect(block):
                if dx > 0:
                    self.rect.right = block.left
                elif dx < 0:
                    self.rect.left = block.right

        # แกน Y
        self.rect.y += int(dy)
        for block in self.collision_rects:
            if self.rect.colliderect(block):
                if dy > 0:
                    self.rect.bottom = block.top
                elif dy < 0:
                    self.rect.top = block.bottom

    def _handle_input(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        move_dir = pygame.Vector2(0, 0)

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move_dir.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move_dir.y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move_dir.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move_dir.x += 1

        if move_dir.length_squared() > 0:
            move_dir = move_dir.normalize()
            dx = move_dir.x * self.move_speed * dt
            dy = move_dir.y * self.move_speed * dt

            # ขยับพร้อมเช็คชนกำแพง
            self._move_with_collision(dx, dy)

            # เก็บทิศไว้ใช้ตอนยิง
            self.facing = move_dir

    # ========== COMBAT ==========
    def _get_current_weapon_base_damage(self) -> int:
        """ตัวอย่างง่าย ๆ: ถ้ามี equipment ก็ให้ base สูงขึ้นหน่อย"""
        if self.equipment is not None:
            weapon = self.equipment.get_item("main_hand")
            if weapon and weapon.item_type == "weapon":
                if weapon.id == "sword_basic":
                    return 15
                elif weapon.id == "sword_iron":
                    return 25
                else:
                    return 18
        return 10  # ชกมือเปล่า

    def shoot(self) -> None:
        """ยิง projectile ไปในทิศทาง self.facing"""
        from .projectile_node import ProjectileNode

        direction = self.facing
        if direction.length_squared() == 0:
            direction = pygame.Vector2(1, 0)

        base_damage = self._get_current_weapon_base_damage()

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
        self.stats.hp = max(0, self.stats.hp - result_damage)
        if self.stats.is_dead():
            print("Player died!")

    # ========== UPDATE ==========
    def update(self, dt: float) -> None:
        self.status.update(dt)
        self._handle_input(dt)
