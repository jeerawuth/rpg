from __future__ import annotations

import pygame

from .animated_node import AnimatedNode
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


class PlayerNode(AnimatedNode):
    def __init__(
        self,
        game,
        pos: tuple[int, int],
        projectile_group: pygame.sprite.Group,
        *groups,
    ) -> None:
        self.game = game
        self.projectile_group = projectile_group

        # ---------- Animation config ----------
        # animations[(state, direction)] -> list[Surface]
        self.animations: dict[tuple[str, str], list[pygame.Surface]] = {}
        self.state: str = "idle"      # idle / walk / attack / hurt / dead / cast
        self.direction: str = "down"  # down / left / right / up
        self.is_moving: bool = False

        # สำหรับระบบ movement / หันทิศ
        self.facing = pygame.Vector2(0, 1)

        # โหลดเฟรมทั้งหมดตามโครงสร้างไฟล์:
        # assets/graphics/images/player/{state}/{state}_{direction}_01.png
        self._load_animations()

        # ---------- SHOOT COOLDOWN ----------
        self.shoot_cooldown = 0.8   # หน่วง 0.8 วินาทีก่อนยิงดอกใหม่ (ปรับได้)
        self.shoot_timer = 0.0      # ตัวนับเวลาคูลดาวน์

        # เลือกเฟรมเริ่มต้น (idle/down ถ้ามี, ไม่งั้นใช้ชุดแรกใน animations หรือ dummy)
        if ("idle", "down") in self.animations:
            start_frames = self.animations[("idle", "down")]
        else:
            if self.animations:
                start_frames = next(iter(self.animations.values()))
            else:
                # fallback: วงกลมสีขาว 1 เฟรม (กรณีคุณยังไม่มีรูป)
                radius = 16
                base_image = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(
                    base_image,
                    (240, 240, 240),
                    (radius, radius),
                    radius,
                )
                start_frames = [base_image]

        # AnimatedNode: frames, frame_duration, loop, *groups
        super().__init__(start_frames, 0.12, True, *groups)

        # ตั้งตำแหน่งเริ่มต้นให้ sprite
        self.rect.center = pos

        # ---------- COMBAT STATS ----------
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

        # ---------- INVENTORY / EQUIPMENT (ถ้ามีคลาสให้ใช้) ----------
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

        # ---------- MOVEMENT & COLLISION ----------
        self.move_speed = PLAYER_SPEED          # pixels / second
        self.collision_rects: list[pygame.Rect] = []  # จะได้จาก TileMap

    # ==================== ANIMATION LOADING ====================
    def _load_animations(self) -> None:
        """โหลดเฟรมทุก state+direction เข้า self.animations"""
        states = ["idle", "walk", "attack", "hurt", "dead", "cast"]
        directions = ["down", "left", "right", "up"]

        for state in states:
            for direction in directions:
                frames = self._load_animation_sequence(state, direction)
                if frames:
                    self.animations[(state, direction)] = frames
                # ถ้าไม่มีไฟล์ชุดนั้นก็ไม่ต้อง error ปล่อยให้ fallback จัดการ

    def _load_animation_sequence(self, state: str, direction: str) -> list[pygame.Surface]:
        """
        โหลดเฟรมจากโครงสร้าง:
            assets/graphics/images/player/{state}/{state}_{direction}_01.png
            assets/graphics/images/player/{state}/{state}_{direction}_02.png
            ...

        เช่น state='walk', direction='up':
            player/walk/walk_up_01.png
            player/walk/walk_up_02.png
        """
        frames: list[pygame.Surface] = []
        index = 1

        while True:
            rel_path = f"player/{state}/{state}_{direction}_{index:02d}.png"
            try:
                surf = self.game.resources.load_image(rel_path)
            except Exception:
                break
            else:
                frames.append(surf)
                index += 1

        return frames

    def _update_animation_state(self) -> None:
        """
        อัปเดต self.state / self.direction จากการเคลื่อนไหวพื้นฐาน
        (ถ้าในอนาคตมีสถานะโจมตี/โดนตี ก็สามารถเปลี่ยน self.state
         ที่ logic อื่น แล้วค่อยเรียก _apply_animation() ได้)
        """
        # ถ้ามี state พิเศษอื่น (เช่น attack/hurt/dead/cast) ให้ควบคุมจาก logic อื่น
        if self.state in ("attack", "hurt", "dead", "cast"):
            return

        if self.is_moving:
            self.state = "walk"
        else:
            self.state = "idle"

        # ใช้ self.facing เป็นตัวบอกทิศ
        dx, dy = self.facing.x, self.facing.y
        if abs(dx) > abs(dy):
            self.direction = "right" if dx > 0 else "left"
        else:
            self.direction = "down" if dy > 0 else "up"

    def _apply_animation(self) -> None:
        """เลือกชุดเฟรมให้ตรงกับ state+direction ปัจจุบัน และส่งเข้า AnimatedNode"""
        key = (self.state, self.direction)
        frames = self.animations.get(key)

        if not frames:
            # fallback เป็น idle/down ถ้ามี
            frames = self.animations.get(("idle", "down"))
            if not frames:
                return

        # เปลี่ยนเซ็ตเฟรม และ reset index ทุกครั้ง
        self.set_frames(frames, reset=True)

    # ==================== COLLISION API ====================
    def set_collision_rects(self, rects) -> None:
        """ให้ GameScene ส่ง list ของกำแพงเข้ามาทุกเฟรม"""
        self.collision_rects = list(rects) if rects is not None else []

    # ==================== MOVEMENT + COLLISION ====================
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

    # ==================== INPUT / MOVEMENT ====================
    def _handle_input(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        move_dir = pygame.Vector2(0, 0)
        self.is_moving = False

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

            # เก็บทิศไว้ใช้ตอนยิง + ให้ระบบแอนิเมชันรู้ว่า "กำลังเดิน"
            self.facing = move_dir
            self.is_moving = True

    # ==================== COMBAT ====================
    def _get_current_weapon_base_damage(self) -> int:
        """ดึง base damage ของอาวุธในมือหลัก (มีผลกับธนูที่ยิง)"""
        if getattr(self, "equipment", None) is not None:
            weapon = self.equipment.get_item("main_hand")
            if weapon and weapon.item_type == "weapon":
                if weapon.id == "bow_power_1":
                    return 25   # ธนูแรงขึ้น
                elif weapon.id == "sword_basic":
                    return 15
                # else สายอื่น ๆ
        return 10  # ไม่มีอาวุธ ถือมือเปล่า


    # ==================== ยิง ====================
    def shoot(self) -> None:
        # ถ้ายังไม่พ้นคูลดาวน์ ห้ามยิง
        if self.shoot_timer > 0:
            return

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
            self,
            self.rect.center,
            direction,
            450,
            packet,
            1.5,
            self.projectile_group,
            self.game.all_sprites,
        )

        # ตั้งคูลดาวน์ใหม่หลังยิง
        self.shoot_timer = self.shoot_cooldown


    def take_damage(self, attacker_stats: Stats, result_damage: int) -> None:
        self.stats.hp = max(0, self.stats.hp - result_damage)
        if self.stats.is_dead():
            print("Player died!")

    # ==================== UPDATE LOOP ====================
    def update(self, dt: float) -> None:
        # อัปเดตสถานะต่าง ๆ (buff/debuff ฯลฯ)
        self.status.update(dt)

        # ลดตัวนับเวลาคูลดาวน์ยิงธนู
        if self.shoot_timer > 0:
            self.shoot_timer -= dt
            if self.shoot_timer < 0:
                self.shoot_timer = 0

        # อินพุต + การเคลื่อนที่ + แอนิเมชัน
        self._handle_input(dt)
        self._update_animation_state()
        self._apply_animation()
        super().update(dt)


