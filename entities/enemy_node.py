# entities/enemy_node.py
from __future__ import annotations

import pygame

from .animated_node import AnimatedNode
from combat.damage_system import Stats, DamagePacket, compute_damage, DamageResult
from combat.status_effect_system import StatusEffectManager


class EnemyNode(AnimatedNode):
    def __init__(self, game, pos: tuple[int, int], *groups) -> None:
        self.game = game

        # ---------- Animation state (เหมือน PlayerNode) ----------
        self.animations: dict[tuple[str, str], list[pygame.Surface]] = {}
        # state: idle / walk / hurt / dead
        self.state: str = "idle"
        # direction: down / left / right / up
        self.direction: str = "down"

        # ใช้สำหรับรู้ว่าศัตรูกำลังหันไปทางไหน
        self.facing = pygame.Vector2(1, 0)
        self.velocity = pygame.Vector2(0, 0)

        # โหลด animations ของศัตรูตามโครง:
        # assets/graphics/images/enemy/goblin/<state>/<state>_<direction>_01.png
        self._load_animations()

        # เลือกเฟรมเริ่มต้น
        if ("idle", "down") in self.animations:
            start_frames = self.animations[("idle", "down")]
        elif self.animations:
            start_frames = next(iter(self.animations.values()))
        else:
            # fallback ถ้ายังไม่มีรูปจริง
            base_image = pygame.Surface((28, 28), pygame.SRCALPHA)
            base_image.fill((200, 40, 40))
            start_frames = [base_image]

        # เรียก AnimatedNode
        super().__init__(start_frames, 0.15, True, *groups)

        # ---------- SFX ----------
        self.sfx_hit = self.game.resources.load_sound("sfx/enemy_hit.wav")
        self.sfx_hit.set_volume(0.7)

        # ตั้งตำแหน่งเริ่มต้นให้ศัตรู
        self.rect.center = pos

        # ---------- Combat stats ----------
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

        # ---------- AI / movement (patrol แนวนอน) ----------
        self.speed = 80
        self.patrol_dir = 1  # 1 = ขวา, -1 = ซ้าย
        self.move_range = 80
        self._origin_x = pos[0]

        # ---------- Hurt / Dead animation timer ----------
        self.hurt_timer: float = 0.0
        self.is_dead: bool = False
        self.death_timer: float = 0.0  # เวลาเล่น dead animation ก่อน kill

    # ============================================================
    # Animation loading (โครงเดียวกับ player แต่เป็น enemy/goblin)
    # ============================================================
    def _load_animations(self) -> None:
        # ตามโฟลเดอร์ที่คุณกำหนด: idle, walk, hurt, dead
        states = ["idle", "walk", "hurt", "dead"]
        directions = ["down", "left", "right", "up"]

        for state in states:
            for direction in directions:
                frames = self._load_animation_sequence(state, direction)
                if frames:
                    self.animations[(state, direction)] = frames

    def _load_animation_sequence(self, state: str, direction: str) -> list[pygame.Surface]:
        """
        โหลดเฟรมตาม pattern:
        assets/graphics/images/enemy/goblin/<state>/<state>_<direction>_01.png
        """
        frames: list[pygame.Surface] = []
        index = 1

        while True:
            rel_path = f"enemy/goblin/{state}/{state}_{direction}_{index:02d}.png"
            try:
                surf = self.game.resources.load_image(rel_path)
            except Exception:
                break
            frames.append(surf)
            index += 1

        return frames

    # ============================================================
    # Movement / AI
    # ============================================================
    def _patrol(self, dt: float) -> None:
        """
        เดินซ้าย-ขวาในช่วง move_range จากจุดกำเนิด
        ถ้าเป็นศัตรูที่ตายแล้วจะไม่ patrol
        """
        if self.is_dead:
            self.velocity.update(0, 0)
            return

        # กำหนดความเร็วตามทิศ
        self.velocity.x = self.patrol_dir * self.speed
        self.velocity.y = 0

        self.rect.x += int(self.velocity.x * dt)

        # กลับทิศเมื่อเดินเกินระยะ
        if abs(self.rect.x - self._origin_x) > self.move_range:
            self.patrol_dir *= -1
            # ปรับ facing ให้ตรงกับการหันของศัตรู
            self.facing.x = 1 if self.patrol_dir > 0 else -1
            self.facing.y = 0

    # ============================================================
    # Animation state update
    # ============================================================
    def _update_animation_state(self) -> None:
        # อัปเดตทิศทางจาก facing
        x, y = self.facing.x, self.facing.y
        if abs(x) > abs(y):
            self.direction = "right" if x > 0 else "left"
        else:
            self.direction = "down" if y >= 0 else "up"

        # ----- dead animation -----
        if self.is_dead and ("dead", self.direction) in self.animations:
            self.state = "dead"
            return

        # ----- hurt animation -----
        if self.hurt_timer > 0 and ("hurt", self.direction) in self.animations:
            self.state = "hurt"
            return

        # ----- idle / walk ปกติ -----
        if self.velocity.length_squared() > 0:
            self.state = "walk"
        else:
            self.state = "idle"

    def _apply_animation(self) -> None:
        frames = self.animations.get((self.state, self.direction))
        if not frames:
            return
        if frames is not self.frames:
            # ใช้เฟรมใหม่ (AnimatedNode จะจัดการ frame index ให้เอง)
            self.set_frames(frames, reset=False)

    # ============================================================
    # Combat
    # ============================================================
    def take_hit(self, attacker_stats: Stats, damage_packet: DamagePacket) -> DamageResult:
        """
        โดนโจมตีจาก attacker:
        - เล่นเสียง
        - ให้ status ปรับ multiplier
        - ใช้ compute_damage (ซึ่งหัก HP ใน self.stats ให้แล้ว)
        - ถ้าตาย -> เล่น dead animation ก่อน kill()
        """
        # ถ้าตายแล้ว ไม่ต้องรับดาเมจเพิ่ม (กันโดน spam)
        if self.is_dead:
            # ยังถือว่าโดนโจมตีไม่สำเร็จ (ดาเมจ 0) ก็ได้
            # แต่เพื่อความง่าย เราจะคืนค่า compute_damage อีกครั้งก็ได้
            return compute_damage(attacker_stats, self.stats, damage_packet)

        # เล่นเสียงโดนตี
        if hasattr(self, "sfx_hit"):
            self.sfx_hit.play()

        # เพิ่ม multiplier จาก debuff (ถ้ามี)
        dmg_mult = self.status.get_multiplier("damage_taken")
        damage_packet.attacker_multiplier *= dmg_mult

        # compute_damage จะคำนวณดาเมจ + หัก HP ใน self.stats.hp ให้เรียบร้อย
        result = compute_damage(attacker_stats, self.stats, damage_packet)

        # ตั้ง hurt animation ชั่วครู่ ถ้ายังไม่ตาย
        if not result.killed:
            self.hurt_timer = 0.25  # แสดงเฟรม hurt ประมาณ 0.25 วินาที
            self.state = "hurt"

        print(
            f"[Enemy] took {result.final_damage} dmg "
            f"({'CRIT' if result.is_crit else 'normal'}) "
            f"HP: {self.stats.hp}/{self.stats.max_hp}"
        )

        if result.killed:
            print("[Enemy] died!")
            # ตั้งสถานะตาย + เวลาเล่น dead animation
            self.is_dead = True
            self.hurt_timer = 0.0       # ไม่ใช้ hurt แล้ว
            self.velocity.update(0, 0)  # หยุดเดิน

            # กำหนดเวลา dead animation (จากจำนวนเฟรม หรือค่าคงที่ก็ได้)
            dead_frames = self.animations.get(("dead", self.direction), None)
            if dead_frames:
                # สมมติให้เฟรมละ 0.15 วินาทีเท่ากับ frame_duration
                self.death_timer = 0.15 * len(dead_frames)
            else:
                # ถ้าไม่มี dead frames ก็ให้เวลาสั้น ๆ
                self.death_timer = 0.4

            # บังคับ state = "dead" เพื่อให้ใช้ชุดเฟรม dead
            self.state = "dead"

        return result

    # ============================================================
    # Update
    # ============================================================
    def update(self, dt: float) -> None:
        # อัปเดต buff/debuff
        self.status.update(dt)

        # ลดเวลา hurt animation (ถ้าไม่ได้ตาย)
        if not self.is_dead and self.hurt_timer > 0:
            self.hurt_timer -= dt
            if self.hurt_timer < 0:
                self.hurt_timer = 0.0

        # AI เคลื่อนที่ (ถ้าตายแล้ว _patrol จะไม่ทำอะไร)
        self._patrol(dt)

        # อัปเดตสถานะ animation ตาม movement + hurt/dead
        self._update_animation_state()
        self._apply_animation()

        # ให้ AnimatedNode อัปเดต frame index ตามเวลา
        super().update(dt)

        # ถ้าอยู่ในสถานะ dead ให้นับเวลา แล้ว kill() เมื่อหมด
        if self.is_dead:
            self.death_timer -= dt
            if self.death_timer <= 0:
                self.kill()
