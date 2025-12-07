# entities/enemy_node.py
from __future__ import annotations

import pygame

from .animated_node import AnimatedNode
from combat.damage_system import Stats, DamagePacket, compute_damage, DamageResult
from combat.status_effect_system import StatusEffectManager
from config.enemy_config import ENEMY_CONFIG


class EnemyNode(AnimatedNode):
    def __init__(
        self,
        game,
        pos: tuple[int, int],
        *groups,
        enemy_id: str = "goblin",  # ใช้ enemy_id มาจาก level01.json
    ) -> None:
        self.game = game
        self.enemy_id = enemy_id

        # ---------- อ่าน config ตาม enemy_id ----------
        cfg = ENEMY_CONFIG.get(enemy_id)
        if cfg is None:
            raise ValueError(f"Unknown enemy_id: {enemy_id}")

        # โฟลเดอร์สไปรต์ (เช่น goblin, slime_green)
        self.sprite_id: str = cfg.get("sprite_id", enemy_id)

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
        try:
            self.sfx_hit = self.game.resources.load_sound("sfx/enemy_hit.wav")
            self.sfx_hit.set_volume(0.7)
        except FileNotFoundError:
            self.sfx_hit = None  # กัน error ถ้ายังไม่มีไฟล์

        # ---------- Position ----------
        self.rect.center = pos
        
        # ตำแหน่งแบบ float สำหรับคำนวณความเร็ว กรณีเดินสวนสนาม
        self.pos_x = float(self.rect.x)

        # ---------- Combat stats จาก ENEMY_CONFIG ----------
        base_stats: Stats = cfg["stats"]
        # ทำสำเนา ไม่ใช้ object เดียวกันทุกตัว
        self.stats = Stats(
            max_hp=base_stats.max_hp,
            hp=base_stats.hp,
            attack=base_stats.attack,
            magic=base_stats.magic,
            armor=base_stats.armor,
            resistances=dict(base_stats.resistances),
            crit_chance=base_stats.crit_chance,
            crit_multiplier=base_stats.crit_multiplier,
        )

        self.status = StatusEffectManager(self)

        # ---------- AI / Movement ----------
        self.speed: float = cfg.get("speed", 60)
        self.patrol_dir: int = 1       # 1 = เดินขวา, -1 = เดินซ้าย
        self.move_range: float = cfg.get("move_range", 80)
        self._origin_x: int = pos[0]

        # รัศมีที่ถ้า player เข้ามาใกล้ จะเริ่มวิ่งไล่
        self.aggro_radius: float = cfg.get("aggro_radius", 200)
        self._aggro_radius_sq: float = self.aggro_radius * self.aggro_radius


        # ---------- Timers ----------
        self.hurt_timer: float = 0.0
        self.is_dead: bool = False
        self.death_timer: float = 0.0

        # ค่า XP ที่จะดรอปตอนตาย (ตอนนี้ยังไม่ใช้ แต่อาจใช้ในระบบเลเวลภายหลัง)
        self.xp_reward: int = cfg.get("xp_reward", 0)

    # ============================================================
    # Hp ratio calculation
    # ============================================================
    @property
    def hp_ratio(self) -> float:
        """คืนค่า 0.0–1.0 แทนสัดส่วน HP ปัจจุบัน"""
        if self.stats.max_hp <= 0:
            return 0.0
        ratio = self.stats.hp / self.stats.max_hp
        return max(0.0, min(1.0, ratio))
    
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
        if self.is_dead:
            self.velocity.update(0, 0)
            return

        # ป้องกัน dt กระโดด
        dt = min(dt, 1 / 30)

        # ถ้ามีส่วนอื่นไปแก้ rect.x มา ให้ sync หนึ่งครั้งตอนเริ่ม
        if not hasattr(self, "pos_x"):
            self.pos_x = float(self.rect.x)

        self.velocity.x = self.patrol_dir * self.speed
        self.velocity.y = 0

        self.pos_x += self.velocity.x * dt

        right_limit = self._origin_x + self.move_range
        left_limit  = self._origin_x - self.move_range

        if self.patrol_dir > 0 and self.pos_x >= right_limit:
            self.pos_x = right_limit
            self.patrol_dir = -1
        elif self.patrol_dir < 0 and self.pos_x <= left_limit:
            self.pos_x = left_limit
            self.patrol_dir = 1

        self.rect.x = round(self.pos_x)

        self.facing.x = 1 if self.patrol_dir > 0 else -1
        self.facing.y = 0



    def _update_ai(self, dt: float) -> None:
        """
        เลือกว่า enemy ตัวนี้จะ 'patrol' เฉย ๆ หรือ 'วิ่งไล่ player'
        ตามระยะ aggro_radius
        """
        if self.is_dead:
            self.velocity.update(0, 0)
            return

        # ถ้า game ยังไม่รู้จัก player ก็ patrol ไปก่อน
        player = getattr(self.game, "player", None)
        if player is None:
            self._patrol(dt)
            return

        ex, ey = self.rect.center
        px, py = player.rect.center

        dx = px - ex
        dy = py - ey
        dist_sq = dx * dx + dy * dy

        # ถ้า player อยู่ในรัศมี -> ไล่ตาม
        if dist_sq <= self._aggro_radius_sq:
            # หาทิศทางไปหา player
            vec = pygame.Vector2(dx, dy)
            if vec.length_squared() > 0:
                vec = vec.normalize()

            # ตั้งความเร็วให้วิ่งเข้าหา player
            self.velocity.x = vec.x * self.speed
            self.velocity.y = vec.y * self.speed

            # ขยับตำแหน่ง (ตอนนี้ยังไม่ได้ทำชนกับกำแพง ถ้าจะทำจริง
            # ค่อยแตกเป็น _move_and_collide แบบ Player)
            self.rect.x += int(self.velocity.x * dt)
            self.rect.y += int(self.velocity.y * dt)

            # ปรับทิศหันให้ตรงกับทิศวิ่ง
            self.facing.x = vec.x
            self.facing.y = vec.y
        else:
            # ถ้าไกลเกินรัศมี -> เดิน patrol ไป-มาเหมือนเดิม
            self._patrol(dt)


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
            # ตายแล้วโดนซ้ำ ไม่ต้องเปลี่ยน state เพิ่ม
            return compute_damage(attacker_stats, self.stats, damage_packet)

        # 🔊 เล่นเสียงโดนตี (ถ้ามีไฟล์)
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
            f"[Enemy:{self.enemy_id}] took {result.final_damage} dmg "
            f"({'CRIT' if result.is_crit else 'normal'}) "
            f"HP: {self.stats.hp}/{self.stats.max_hp}"
        )

        if result.killed:
            print(f"[Enemy:{self.enemy_id}] died!")
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

        # นับเวลาหยุดนิ่ง/โดนตี (hurt_timer)
        if not self.is_dead and self.hurt_timer > 0:
            self.hurt_timer -= dt
            if self.hurt_timer < 0:
                self.hurt_timer = 0.0

        # ถ้ายังไม่ตาย และไม่ได้อยู่ในช่วงหยุดนิ่ง ค่อยอัปเดต AI / เดินไล่ player
        if not self.is_dead and self.hurt_timer <= 0:
            # เดิมใช้ patrol อย่างเดียว -> เปลี่ยนเป็นใช้ AI
            self._update_ai(dt)

        self._update_animation_state()
        self._apply_animation()

        super().update(dt)

        if self.is_dead:
            self.death_timer -= dt
            if self.death_timer <= 0:
                self.kill()


