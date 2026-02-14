# entities/enemy_node.py
from __future__ import annotations

import pygame
import math

from .animated_node import AnimatedNode
from .projectile_node import ProjectileNode
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

        # Scale modifier (override default sprite_scale)
        self.custom_scale: float | None = cfg.get("scale", None)

        # ---------- Animation state ----------
        self.animations: dict[tuple[str, str], list[pygame.Surface]] = {}
        self.state: str = "idle"      # idle / walk / hurt / dead
        self.direction: str = "down"  # down / left / right / up

        self.facing = pygame.Vector2(1, 0)
        self.velocity = pygame.Vector2(0, 0)

        # ---------- Boss Logic (Must init before loading animations) ----------
        self.is_boss = (cfg.get("type") == "boss")
        self.attack_config = cfg.get("attack_config", {})
        
        # Timers for boss
        self.charge_timer: float = 0.0
        self.attack_cooldown_timer: float = 0.0
        self.attack_anim_done: bool = False
        
        # Target for attack (snapshot player position)
        self.attack_target_pos: pygame.Vector2 | None = None

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
        if self.is_boss:
            states.append("attack")
            states.append("charge")
            
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
            
            # Use resource manager to check/load
            try:
                surf = self.game.resources.load_image(rel_path, scale_override=self.custom_scale)
                frames.append(surf)
                index += 1
            except Exception:
                # If failed on the first frame (index=1), try loading without number suffix
                # e.g. "charge_down.png" instead of "charge_down_01.png"
                if index == 1:
                     rel_path_no_num = f"enemy/{self.sprite_id}/{state}/{state}_{direction}.png"
                     try:
                         surf = self.game.resources.load_image(rel_path_no_num, scale_override=self.custom_scale)
                         frames.append(surf)
                     except Exception:
                         pass # Really not found
                
                # Stop looking for sequence
                break

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

    def update(self, dt: float) -> None:
        self.dt = dt  # Store for use in other methods if needed

        # 1) Timers
        if self.hurt_timer > 0:
            self.hurt_timer -= dt
            
        if self.is_dead:
            self.death_timer -= dt
            if self.death_timer <= 0:
                self.kill()
            self._update_animation_state()
            self._apply_animation()
            super().update(dt)
            return
            
        # 2) Status Effects
        self.status.update(dt)
        
        # 3) Animation config (ถ้าเพิ่งเปลี่ยน state/direction)
        self._update_animation_state()
        
        # 4) AI Logic (Boss or Standard)
        self._update_ai(dt)
        
        # 5) Move & Collide (if not charging/attacking)
        if not (self.is_boss and (self.state == "charge" or self.state == "attack")):
             self._move_and_collide_circle(dt)
        
        # 6) Apply Animation Frame
        self._apply_animation()
        
        # 7) Base update (frame ticking)
        super().update(dt)

    def _update_ai(self, dt: float) -> None:
        """
        AI Decision Making:
        - Boss: Idle -> Chase -> Charge -> Attack -> Cooldown
        - Normal: Patrol <-> Chase
        """
        # --- Common: Physics Decay ---
        # Friction/Drag
        self.velocity *= 0.95 
        self.acceleration *= 0 # Reset force
        
        # --- Boss Logic Updates ---
        if self.is_boss:
             # Cooldown tick
             # Cooldown tick
             if self.attack_cooldown_timer > 0:
                 self.attack_cooldown_timer -= dt
                 # Recovery phase: If just attacked (high cooldown), stay idle
                 # Cooldown is usually 3.0s. Let's say first 1.0s is "recovery"
                 total_cd = self.attack_config.get("cooldown", 3.0)
                 if self.attack_cooldown_timer > (total_cd - 1.0):
                     # Force Idle (stop moving)
                     self.velocity = pygame.Vector2(0, 0)
                     self.state = "idle" # Explicitly set state
                     return
                 
             # Check Charge State
             if self.state == "charge":
                 self.charge_timer -= dt
                 if self.charge_timer <= 0:
                     self._start_attack_animation()
                 return # Don't move while charging
                 
             # Check Attack State
             if self.state == "attack":
                 # Wait for animation to finish
                 if self.check_animation_done():
                     self._finish_attack()
                 return # Don't move while attacking

        # --- Standard Movement / Chase Logic ---
        player = getattr(self.game, "player", None)
        if player is None:
             self._patrol_logic(dt)
             return
             
        # Distance checks
        dist_sq = self.pos.distance_squared_to(player.pos)
        
        # Aggro Check
        if dist_sq <= self._aggro_radius_sq:
            # --- Boss Attack Trigger ---
            if self.is_boss and self._check_boss_attack_condition(player):
                 self._start_charge(player)
                 return

            # --- Chase Movement ---
            steer = pygame.Vector2(0, 0)
            
            # Seek
            dist = math.sqrt(dist_sq)
            if dist > 50: # Don't overlap perfectly
                 steer += self._seek(player.pos)
            
            # Separate
            if self.game and hasattr(self.game, "enemies"):
                 steer += self._separate(self.game.enemies.sprites()) * 1.5
            
            self.acceleration += steer
            
            # Apply Physics
            self.velocity += self.acceleration * dt
            if self.velocity.length() > self.max_speed:
                self.velocity.scale_to_length(self.max_speed)
                
            # Facing
            if self.velocity.length_squared() > 10:
                self.state = "walk"
                # Smooth facing update? or instant? Instant for pixel art usually better
                if abs(self.velocity.x) > abs(self.velocity.y):
                    self.facing = pygame.Vector2(1 if self.velocity.x > 0 else -1, 0)
                else:
                    self.facing = pygame.Vector2(0, 1 if self.velocity.y > 0 else -1)

        else:
            # Idle / Patrol
            self._patrol_logic(dt)

    def _patrol_logic(self, dt: float):
        # Patrol logic (override existing _patrol usage)
        # Use simpler logic or reuse existing _patrol(dt) but adapt it
        # Existing _patrol() updates position directly... let's keep using it for now for simplicity
        # IF we want Boids physics everywhere, we'd rewrite patrol to use forces.
        # For now, fallback to direct pos update if not chasing.
        self._patrol(dt)
        if abs(self.velocity.x) > 1:
            self.state = "walk"
        else:
            self.state = "idle"

    # --- Boss Specific Methods ---
    def _check_boss_attack_condition(self, player) -> bool:
        if self.attack_cooldown_timer > 0:
            return False
            
        dist = self.pos.distance_to(player.pos)
        attack_range = self.attack_config.get("range", 100)
        return dist <= attack_range

    def _start_charge(self, player):
        self.state = "charge"
        self.charge_timer = self.attack_config.get("charge_time", 1.0)
        self.velocity.update(0, 0)
        self.attack_target_pos = player.pos.copy() # Lock target location



    def _start_attack_animation(self):
        self.state = "attack"
        self.frame_index = 0
        self.animation_timer = 0.0
        self.attack_anim_done = False
        
        # Face target
        if self.attack_target_pos:
            diff = self.attack_target_pos - self.pos
            if diff.length_squared() > 0:
                 if abs(diff.x) > abs(diff.y):
                    self.facing = pygame.Vector2(1 if diff.x > 0 else -1, 0)
                 else:
                    self.facing = pygame.Vector2(0, 1 if diff.y > 0 else -1)
        
        # Spawn Rock Barrage (Projectiles)
        self._spawn_rock_barrage()

    def _spawn_rock_barrage(self):
        if not self.attack_target_pos:
            return
            
        import random
        
        # Num rocks
        num_rocks = 8
        
        # Center of attack area
        center = self.attack_target_pos
        radius = self.attack_config.get("damage_radius", 150)
        iso_scale_y = 0.42
        
        dmg_mult = self.attack_config.get("damage_multiplier", 1.5)
        
        for _ in range(num_rocks):
            # Angular distribution
            angle_rad = random.uniform(0, 2 * math.pi)
            # Radial distribution (sqrt for uniform circle area)
            r = radius * math.sqrt(random.random())
            
            # Isometric offset
            off_x = r * math.cos(angle_rad)
            off_y = r * math.sin(angle_rad) * iso_scale_y
            
            target_pt = center + pygame.Vector2(off_x, off_y)
            
            # Start pos: Boss center (or slightly above head)
            start_pos = pygame.Vector2(self.rect.center)
            start_pos.y -= 20 # High up
            
            direction = (target_pt - start_pos)
            if direction.length_squared() > 0:
                direction = direction.normalize()
            else:
                direction = pygame.Vector2(0, 1) # Fallback down
            
            # Groups
            groups = [self.game.all_sprites]
            if hasattr(self.game, "enemy_projectiles"):
                groups.append(self.game.enemy_projectiles)
            elif hasattr(self.game, "projectiles"): # Fallback
                groups.append(self.game.projectiles)
            
            ProjectileNode(
                self,           # owner
                start_pos,      # pos
                direction,      # direction
                880,            # speed
                DamagePacket(   # damage_packet
                    base=0.0,
                    damage_type="physical",
                    scaling_attack=dmg_mult
                ),
                "rock",         # projectile_id
                2.0,            # lifetime
                *groups
            )

    def _finish_attack(self):
        self.state = "idle"
        self.attack_cooldown_timer = self.attack_config.get("cooldown", 3.0)

    # ============================================================
    # Draw Override (Telegraphing)
    # ============================================================
    # ============================================================
    # Draw Override (Telegraphing) - Called manually by GameScene
    # ============================================================
    def draw_extra(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        if self.state == "charge" and self.attack_target_pos:
            radius = self.attack_config.get("damage_radius", 80)
            total_time = self.attack_config.get("charge_time", 1.0)
            
            if total_time > 0:
                progress = 1.0 - (self.charge_timer / total_time)
            else:
                progress = 1.0
                
            # Isometric Projection
            iso_scale_y = 0.42
            width = radius * 2
            height = radius * 2 * iso_scale_y
            
            # Create a surface for the telegraph (with alpha)
            # Make it slightly larger to avoid clipping anti-aliased edges
            s_width, s_height = int(width + 4), int(height + 4)
            s = pygame.Surface((s_width, s_height), pygame.SRCALPHA)
            cx, cy = s_width / 2, s_height / 2
            
            # --- Visual Design ---
            # 1. Base Danger Zone (Low Alpha Red)
            # Requested: ~30% transparency -> Alpha approx 76 (out of 255)
            # We can pulse it slightly for "alive" feel
            pulse = (math.sin(pygame.time.get_ticks() * 0.01) + 1) * 0.5 # 0.0 - 1.0
            base_alpha = 60 + int(20 * pulse) # 60-80 alpha
            
            base_color = (255, 20, 20, base_alpha)
            pygame.draw.ellipse(s, base_color, (2, 2, width, height))
            
            # 2. Outer Warning Rim (Brighter, thinner)
            rim_color = (255, 80, 80, 150)
            pygame.draw.ellipse(s, rim_color, (2, 2, width, height), 2)
            
            # 3. Inner "Filling" Circle (The Timer)
            # Grow from center is usually clearer for "charging up"
            # Or Shrink from outside (classic MMO style). Let's stick to shrink inward as "impact imminent"
            
            # Inner circle properties
            inner_w = width * (1.0 - progress) # Shrink as progress -> 1
            inner_h = height * (1.0 - progress)
            
            if inner_w > 1:
                # Center rect
                start_x = cx - inner_w / 2
                start_y = cy - inner_h / 2
                
                # Color shifts from Yellow -> Red as it gets smaller
                r_val = 255
                g_val = int(255 * (1.0 - progress)) # Yellow -> Red
                inner_color = (r_val, g_val, 0, 180) # High alpha for visibility
                
                ring_rect = pygame.Rect(start_x, start_y, inner_w, inner_h)
                pygame.draw.ellipse(s, inner_color, ring_rect, 2)
                
            # 4. Pattern / Runes (Optional Decoration)
            # Just a static cross or smaller ring to make it look "tech/magic"
            deco_alpha = 40
            deco_color = (255, 0, 0, deco_alpha)
            # Dashed circle effect simulation (just a smaller static ring)
            pygame.draw.ellipse(s, deco_color, (cx - width*0.35, cy - height*0.35, width*0.7, height*0.7), 1)

            
            # Draw to world
            # Position correctly (center - half size)
            center = self.attack_target_pos - camera_offset
            draw_pos = (center.x - s_width/2, center.y - s_height/2)
            
            # Add BLEND_ADD (Additive Blending) for "Glowing" look if desired?
            # Standard BLEND_ALPHA is safer for visibility on bright grounds.
            surface.blit(s, draw_pos)


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

        # dead > hurt > charge/attack > walk/idle
        if self.is_dead and ("dead", self.direction) in self.animations:
            self.state = "dead"
            return

        if self.hurt_timer > 0 and ("hurt", self.direction) in self.animations:
            self.state = "hurt"
            return

        # Boss states (Charge/Attack) take precedence over walk/idle
        if self.is_boss and (self.state == "charge" or self.state == "attack"):
            return

        if self.velocity.length_squared() > 0:
            self.state = "walk"
        else:
            self.state = "idle"

    def check_animation_done(self) -> bool:
        """Check if non-looping animation has finished"""
        return self.finished

    def _apply_animation(self) -> None:
        frames = self.animations.get((self.state, self.direction))
        if not frames:
            return
            
        # Determine loop settings
        should_loop = (self.state not in ("attack", "dead"))
        
        # If frames changed, apply new frames
        if frames is not self.frames:
            # Force reset for attack/dead to start from beginning
            # Also reset if the previous animation was finished (e.g. coming from attack -> idle)
            should_reset = (self.state in ("attack", "dead")) or self.finished
            self.set_frames(frames, loop=should_loop, reset=should_reset)
        else:
            # If frames same, just ensure loop setting is correct (e.g. maybe unlikely to change dynamically but safe)
            self.loop = should_loop


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

        self._apply_animation()

        super().update(dt)

        if self.is_dead:
            self.death_timer -= dt
            if self.death_timer <= 0:
                self.kill()
