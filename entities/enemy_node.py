# entities/enemy_node.py
from __future__ import annotations

import pygame
import math

from .animated_node import AnimatedNode
from .damage_number_node import DamageNumberNode
from .hit_effect_node import HitEffectNode
from combat.damage_system import Stats, DamagePacket, compute_damage, DamageResult
from combat.status_effect_system import StatusEffectManager
from config.enemy_config import ENEMY_CONFIG


# helper สำหรับการชน circle + segment
def circle_segment_mtv(center: pygame.Vector2,
                       radius: float,
                       a: pygame.Vector2,
                       b: pygame.Vector2) -> pygame.Vector2 | None:
    """
    หา minimal translation vector (MTV) ที่ต้องขยับวงกลม
    ออกจาก segment a-b ถ้าไม่ชนให้คืน None
    """
    ab = b - a
    ab_len_sq = ab.x * ab.x + ab.y * ab.y
    if ab_len_sq == 0:
        # segment เส้นสั้นมาก → ใช้จุด a แทน
        to_center = center - a
        dist_sq = to_center.length_squared()
        if dist_sq >= radius * radius or dist_sq == 0:
            return None
        dist = math.sqrt(dist_sq)
        overlap = radius - dist
        return to_center.normalize() * overlap

    # project center ลงเส้น a-b แล้ว clamp ให้อยู่ใน [0, 1]
    t = (center - a).dot(ab) / ab_len_sq
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    closest = a + ab * t

    diff = center - closest
    dist_sq = diff.length_squared()
    if dist_sq >= radius * radius or dist_sq == 0:
        return None

    dist = math.sqrt(dist_sq)
    overlap = radius - dist
    normal = diff / dist

    return normal * overlap

class EnemyNode(AnimatedNode):
    # cache animations ต่อ sprite_id เพื่อไม่ต้องโหลด/scale ซ้ำทุกตัว
    _ANIMATION_CACHE: dict[str, dict[tuple[str, str], list[pygame.Surface]]] = {}

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

        # ---------- โหลด animations (ใช้ cache ถ้ามีแล้ว) ----------
        cached = EnemyNode._ANIMATION_CACHE.get(self.sprite_id)
        if cached is not None:
            self.animations = cached
        else:
            self._load_animations()
            EnemyNode._ANIMATION_CACHE[self.sprite_id] = self.animations

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

        # <--- เพิ่มส่วนนี้: คุณสมบัติการชนแบบวงกลม (เหมือนใน player_node.py) --->
        # ใช้ center (Vector2) + radius สำหรับระบบชนแบบวงกลม
        self.pos = pygame.math.Vector2(self.rect.center)
        self.radius: float = 40.0  # กำหนดขนาดรัศมี (อาจลองปรับ 10.0 - 20.0 ตามขนาดศัตรู)

        # เส้น boundary สำหรับชน (รับค่าจาก GameScene)
        # list[tuple[pygame.Vector2, pygame.Vector2]]
        self.collision_segments: list[tuple[pygame.Vector2, pygame.Vector2]] = []
        # <--- สิ้นสุดส่วนที่เพิ่ม --->


        # ตำแหน่งแบบ float สำหรับคำนวณความเร็ว กรณี patrol
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

        # manager สำหรับ status effect (เช่น damage_taken multiplier)
        self.status = StatusEffectManager(self)

        # ---------- AI / Movement ----------
        # ใช้ speed จาก config (เหมือนของเดิม)
        self.speed: float = cfg.get("speed", 60)
        self.max_speed = self.speed  # Alias for Boids logic
        self.max_force = 150.0  # Controls agility/turning speed
        self.acceleration = pygame.Vector2(0, 0)
        
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
    # Movement / AI (Steering Behaviors)
    # ============================================================
    def _seek(self, target_pos: pygame.Vector2) -> pygame.Vector2:
        """
        Steering force to move towards target
        """
        desired = target_pos - self.pos
        # ถ้าถึงจุดหมายแล้ว (ระยะใกล้มาก) ให้หยุด
        dist = desired.length()
        if dist < 1.0:
            return pygame.Vector2(0, 0)
            
        desired = desired.normalize() * self.max_speed
        steer = desired - self.velocity
        
        # Limit steer force
        if steer.length() > self.max_force:
            steer.scale_to_length(self.max_force)
            
        return steer

    def _separate(self, neighbors: list[EnemyNode]) -> pygame.Vector2:
        """
        Steering force to avoid crowding neighbors
        """
        desired_separation = self.radius * 2.2 # ระยะห่างที่ต้องการ (ใหญ่กว่าตัวนิดหน่อย)
        steer = pygame.Vector2(0, 0)
        count = 0
        
        for other in neighbors:
            if other is self or other.is_dead:
                continue
                
            d = self.pos.distance_to(other.pos)
            if 0 < d < desired_separation:
                # คำนวณ vector หนี (จาก other -> self)
                diff = self.pos - other.pos
                diff.normalize_ip()
                diff /= d  # Weight by distance (ยิ่งใกล้ยิ่งหนีแรง)
                steer += diff
                count += 1
                
        if count > 0:
            steer /= count
            if steer.length() > 0:
                steer.normalize_ip()
                steer *= self.max_speed
                steer -= self.velocity
                if steer.length() > self.max_force:
                    steer.scale_to_length(self.max_force)
                    
        return steer

    # ============================================================
    # Movement / AI (Old Patrol)
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
        left_limit = self._origin_x - self.move_range

        if self.pos_x > right_limit:
            self.pos_x = right_limit
            self.patrol_dir = -1
        elif self.pos_x < left_limit:
            self.pos_x = left_limit
            self.patrol_dir = 1

        self.rect.x = round(self.pos_x)

        self.facing.x = 1 if self.patrol_dir > 0 else -1
        self.facing.y = 0

    def _update_ai(self, dt: float) -> None:
        """
        เลือกว่า enemy ตัวนี้จะ 'patrol' เฉย ๆ หรือ 'วิ่งไล่ player'
        โดยใช้ระบบ Steering Behaviors
        """
        if self.is_dead:
            self.velocity.update(0, 0)
            return

        # ถ้า game ยังไม่รู้จัก player ก็ patrol ไปก่อน
        player = getattr(self.game, "player", None)
        if player is None:
            self._patrol(dt)
            return

        # คำนวณระยะห่าง
        ex, ey = self.rect.center
        px, py = player.rect.center
        
        pos_vec = self.pos
        player_pos = pygame.Vector2(px, py)
        dist_sq = pos_vec.distance_squared_to(player_pos)

        # ถ้า player อยู่ในรัศมี -> ไล่ตามด้วย Physics
        if dist_sq <= self._aggro_radius_sq:
            # 1. Reset acceleration
            self.acceleration *= 0 
            
            # 2. Add Forces
            # Seek Force
            seek_force = self._seek(player_pos)
            self.acceleration += seek_force
            
            # Separation Force (Optional: ถ้า enemies เยอะๆ ควรเปิดใช้)
            # ต้องดึง list เพื่อนบ้านมาจาก game.enemies
            # เพื่อประสิทธิภาพ เราจะ separate เฉพาะตัวใกล้ๆ จริงๆ (แต่ในที่นี้ขอ check หมดหรือสุ่มก็ได้)
            if self.game and hasattr(self.game, "enemies"):
                 # สุ่ม check บ้างเพื่อลดภาระ หรือ check หมดถ้ามีไม่เยอะ
                sep_force = self._separate(self.game.enemies.sprites())
                self.acceleration += sep_force * 1.5 # Weight separation higher
            
            # 3. Apply Physics
            self.velocity += self.acceleration * dt
            # Limit speed
            if self.velocity.length() > self.max_speed:
                self.velocity.scale_to_length(self.max_speed)
                
            # 4. update position (ทำใน update หลักแล้ว แต่ต้องส่ง velocity ไป)
            # เราจะไม่อัปเดต rect ที่นี่ จะทำใน update() หลักผ่าน _move_and_collide_circle

            # ปรับทิศหัน
            if self.velocity.length_squared() > 10: # ขยับนิดเดียวไม่ต้องหัน
                self.facing = self.velocity.normalize()

        else:
            # ถ้าไกลเกินรัศมี -> เดิน patrol ไป-มาเหมือนเดิม
            # (Patrol แบบเดิมมันปรับ rect เลย อาจจะต้องปรับปรุงถ้าจะให้เนียน)
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
    # Collision helper
    # ============================================================
    def set_collision_segments(
        self,
        segments: list[tuple[pygame.Vector2, pygame.Vector2]],
    ) -> None:
        """ ให้ GameScene ส่งเส้น boundary จาก TileMap มาให้ """
        self.collision_segments = segments

    def _move_and_collide_circle(self, dt: float) -> None:
        """
        เคลื่อนที่และจัดการชนกำแพง/ขอบเขตด้วยวิธี Circle vs Segment
        """
        # คำนวณตำแหน่งใหม่แบบไม่ชนก่อน
        new_pos = self.pos + self.velocity * dt

        # ลูปชนซ้ำ 4 ครั้ง (เผื่อหลุดกำแพง)
        for _ in range(4):
            moved = False
            
            # ลูปเช็คชนกับ segment ทั้งหมด
            for a, b in self.collision_segments:
                # คำนวณ MTV (Minimal Translation Vector)
                mtv = circle_segment_mtv(new_pos, self.radius, a, b)
                
                if mtv is not None:
                    # ขยับตัวละครออกจากกำแพง
                    new_pos += mtv
                    moved = True
            
            # ถ้าไม่มีการชนแล้ว → จบการลูป
            if not moved:
                break

        # อัปเดตตำแหน่งจริง
        self.pos = new_pos
        self.rect.center = (round(self.pos.x), round(self.pos.y))

    # ============================================================
    # Combat
    # ============================================================
    def take_hit(self, attacker_stats: Stats, damage_packet: DamagePacket) -> DamageResult:
        if self.is_dead:
            # ตายแล้วโดนซ้ำ ไม่ต้องเปลี่ยน state เพิ่ม
            return compute_damage(attacker_stats, self.stats, damage_packet)

        # 🔊 เล่นเสียงโดนตี (ถ้ามีไฟล์)
        if self.sfx_hit is not None:
            self.sfx_hit.play()

        # modifier จาก status (เช่น debuff ทำให้โดนแรงขึ้น)
        dmg_mult = self.status.get_multiplier("damage_taken")
        damage_packet.attacker_multiplier *= dmg_mult

        # compute_damage จะไปหัก HP ใน self.stats ให้เอง
        result = compute_damage(attacker_stats, self.stats, damage_packet)

        if result.killed:
            self.is_dead = True
            self.death_timer = 0.5
        else:
            self.hurt_timer = 0.25
            self.state = "hurt"

        # Spawn Damage Number
        if result.final_damage > 0:
            DamageNumberNode(
                self.game,
                self.rect.midtop,
                result.final_damage,
                self.game.all_sprites,
                is_crit=result.is_crit
            )
            
            # Spawn Hit Effect
            HitEffectNode(
                self.game,
                self.rect.center,
                self.game.all_sprites,
                scale=1.2 if result.is_crit else 0.8
            )

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
            self._update_ai(dt)
            
            # <--- แทนที่การเคลื่อนที่ด้วยเมธอดชนกำแพง --->
            if self.velocity.length_squared() > 0:
                self._move_and_collide_circle(dt)
            else:
                # ถ้าไม่มีความเร็ว ก็แค่อัปเดต rect ให้ตรงกับ pos
                self.rect.center = (round(self.pos.x), round(self.pos.y))
            # <--- สิ้นสุดการแก้ไข --->
            
        # ถ้าอยู่ในช่วง hurt หรือ dead ก็ให้ rect ตรงกับ pos ปัจจุบัน
        else:
             self.rect.center = (round(self.pos.x), round(self.pos.y))


        self._update_animation_state()
        self._apply_animation()

        super().update(dt)

        if self.is_dead:
            self.death_timer -= dt
            if self.death_timer <= 0:
                self.kill()
