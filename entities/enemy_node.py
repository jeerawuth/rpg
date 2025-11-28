# entities/enemy_node.py
from __future__ import annotations

import pygame

from .animated_node import AnimatedNode
from combat.damage_system import Stats, DamagePacket, compute_damage, DamageResult
from combat.status_effect_system import StatusEffectManager


class EnemyNode(AnimatedNode):
    def __init__(
        self,
        game,
        pos: tuple[int, int],
        *groups,
        sprite_id: str = "goblin",  # enemy/goblin หรือ enemy/slime_green
    ) -> None:
        self.game = game
        self.sprite_id = sprite_id

        # ---------- Animation state ----------
        self.animations: dict[tuple[str, str], list[pygame.Surface]] = {}
        self.state: str = "idle"      # idle / walk / hurt / dead
        self.direction: str = "down"  # down / left / right / up

        self.facing = pygame.Vector2(1, 0)
        self.velocity = pygame.Vector2(0, 0)

        # โหลด animations จากไฟล์
        self._load_animations()

        # เลือกเฟรมเริ่มต้น
        if ("idle", "down") in self.animations:
            start_frames = self.animations[("idle", "down")]
        elif self.animations:
            start_frames = next(iter(self.animations.values()))
        else:
            # fallback: ไม่มีรูปเลย -> สี่เหลี่ยมแดง
            base_image = pygame.Surface((28, 28), pygame.SRCALPHA)
            base_image.fill((200, 40, 40))
            start_frames = [base_image]

        # AnimatedNode
        super().__init__(start_frames, 0.15, True, *groups)

        # ---------- SFX ----------
        self.sfx_hit = self.game.resources.load_sound("sfx/enemy_hit.wav")
        self.sfx_hit.set_volume(0.7)

        # ---------- Position ----------
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

        self.status = StatusEffectManager(self)

        # ---------- AI / Movement ----------
        self.speed = 80
        self.patrol_dir = 1       # 1 = เดินขวา, -1 = เดินซ้าย
        self.move_range = 80
        self._origin_x = pos[0]

        # ---------- Timers ----------
        self.hurt_timer: float = 0.0
        self.is_dead: bool = False
        self.death_timer: float = 0.0

    # ============================================================
    # Animation loading
    # ============================================================
    def _load_animations(self) -> None:
        # ใช้โฟลเดอร์: enemy/<sprite_id>/<state>/<state>_<direction>_01.png
        # เช่น: enemy/goblin/idle/idle_down_01.png
        states = ["idle", "walk", "hurt", "dead"]
        directions = ["down", "left", "right", "up"]

        for state in states:
            for direction in directions:
                frames = self._load_animation_sequence(state, direction)
                if frames:
                    self.animations[(state, direction)] = frames

    def _load_animation_sequence(self, state: str, direction: str) -> list[pygame.Surface]:
        frames: list[pygame.Surface] = []
        index = 1

        while True:
            # ตรงกับโครงที่คุณใช้:
            # assets/graphics/images/enemy/<sprite_id>/<state>/<state>_<direction>_01.png
            rel_path = f"enemy/{self.sprite_id}/{state}/{state}_{direction}_{index:02d}.png"
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
        """เดินไป-มาในระยะ move_range จากจุดเริ่มต้น"""
        if self.is_dead:
            self.velocity.update(0, 0)
            return

        self.velocity.x = self.patrol_dir * self.speed
        self.velocity.y = 0

        self.rect.x += int(self.velocity.x * dt)

        if abs(self.rect.x - self._origin_x) > self.move_range:
            self.patrol_dir *= -1
            # ปรับทิศหัน
            self.facing.x = 1 if self.patrol_dir > 0 else -1
            self.facing.y = 0

    # ============================================================
    # Animation state
    # ============================================================
    def _update_animation_state(self) -> None:
        # อัปเดตทิศจาก facing
        x, y = self.facing.x, self.facing.y
        if abs(x) > abs(y):
            self.direction = "right" if x > 0 else "left"
        else:
            self.direction = "down" if y >= 0 else "up"

        # dead > hurt > walk/idle
        if self.is_dead and ("dead", self.direction) in self.animations:
            self.state = "dead"
            return

        if self.hurt_timer > 0 and ("hurt", self.direction) in self.animations:
            self.state = "hurt"
            return

        if self.velocity.length_squared() > 0:
            self.state = "walk"
        else:
            self.state = "idle"

    def _apply_animation(self) -> None:
        frames = self.animations.get((self.state, self.direction))
        if not frames:
            return
        if frames is not self.frames:
            self.set_frames(frames, reset=False)

    # ============================================================
    # Combat
    # ============================================================
    def take_hit(self, attacker_stats: Stats, damage_packet: DamagePacket) -> DamageResult:
        if self.is_dead:
            # ตายแล้วโดนซ้ำ ก็ไม่ต้องเปลี่ยน state อะไรเพิ่ม
            return compute_damage(attacker_stats, self.stats, damage_packet)

        # เล่นเสียง
        if hasattr(self, "sfx_hit"):
            self.sfx_hit.play()

        # modifier จาก status
        dmg_mult = self.status.get_multiplier("damage_taken")
        damage_packet.attacker_multiplier *= dmg_mult

        # compute_damage จะหัก HP ใน self.stats ให้เอง
        result = compute_damage(attacker_stats, self.stats, damage_packet)

        if not result.killed:
            self.hurt_timer = 0.25
            self.state = "hurt"

        print(
            f"[Enemy] took {result.final_damage} dmg "
            f"({'CRIT' if result.is_crit else 'normal'}) "
            f"HP: {self.stats.hp}/{self.stats.max_hp}"
        )

        if result.killed:
            print("[Enemy] died!")
            self.is_dead = True
            self.hurt_timer = 0.0
            self.velocity.update(0, 0)

            dead_frames = self.animations.get(("dead", self.direction))
            if dead_frames:
                self.death_timer = 0.15 * len(dead_frames)
            else:
                self.death_timer = 0.4

            self.state = "dead"

        return result

    # ============================================================
    # Update
    # ============================================================
    def update(self, dt: float) -> None:
        self.status.update(dt)

        if not self.is_dead and self.hurt_timer > 0:
            self.hurt_timer -= dt
            if self.hurt_timer < 0:
                self.hurt_timer = 0.0

        self._patrol(dt)

        self._update_animation_state()
        self._apply_animation()

        super().update(dt)

        if self.is_dead:
            self.death_timer -= dt
            if self.death_timer <= 0:
                self.kill()
