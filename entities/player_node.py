# entities/player_node.py
from __future__ import annotations

import math
import pygame


from .animated_node import AnimatedNode
from combat.damage_system import Stats, DamagePacket, DamageResult, compute_damage
from combat.status_effect_system import StatusEffectManager
from config.settings import PLAYER_SPEED
from .projectile_node import ProjectileNode
from entities.slash_effect_node import SlashEffectNode
# ดาบฟันตามแนวโค้ง
from entities.sword_slash_arc_node import SwordSlashArcNode


# optional imports (เผื่อยังไม่มีระบบ inventory/equipment)
try:
    from items.inventory import Inventory
    from items.equipment import Equipment
except ImportError:
    Inventory = None
    Equipment = None

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

        # ---------- SFX (ใช้ ResourceManager โหลดเสียง) ----------
        self.sfx_slash = self.game.resources.load_sound("sfx/slash.wav")
        self.sfx_bow_shoot = self.game.resources.load_sound("sfx/bow_shoot.wav")

        # ใช้ pickup_itemp.wav เป็นเสียงเก็บไอเท็ม
        self.sfx_item_pickup = self.game.resources.load_sound("sfx/pickup_item.wav")

        self.sfx_slash.set_volume(0.7)
        self.sfx_bow_shoot.set_volume(0.7)
        # ถ้าอยากให้ตอนเก็บของเบากว่านิดนึงก็ได้ เช่น:
        # self.sfx_item_pickup.set_volume(0.5)

        # รูปดาบสำหรับแอนิเมชันวิ่งตามเส้นโค้ง
        try:
            self.sword_slash_image = self.game.resources.load_image(
                "effects/sword_slash.png"      # ปรับ path ตามไฟล์จริงของคุณ
            )
        except Exception:
            self.sword_slash_image = None



        # ---------- Animation state ----------
        self.animations: dict[tuple[str, str], list[pygame.Surface]] = {}
        self.state: str = "idle"      # idle / walk / attack / hurt / dead / cast
        self.direction: str = "down"  # down / left / right / up

        # ใช้เหมือน enemy
        self.hurt_timer: float = 0.0
        self.is_dead: bool = False

        self.velocity = pygame.Vector2(0, 0)
        self.facing = pygame.Vector2(0, 1)

        # โหลดเฟรมทั้งหมดตามโครงสร้าง:
        # assets/graphics/images/player/{state}/{state}_{direction}_01.png
        self._load_animations()

        # โหลดเฟรมท่ายิงธนู (attack_arrow_*)
        self.bow_attack_animations: dict[str, list[pygame.Surface]] = {}
        self._load_bow_attack_animations()

        # เลือกเฟรมเริ่มต้น
        if ("idle", "down") in self.animations:
            start_frames = self.animations[("idle", "down")]
        elif self.animations:
            start_frames = next(iter(self.animations.values()))
        else:
            # fallback กรณียังไม่มีรูปจริง
            radius = 16
            img = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(img, (240, 240, 240), (radius, radius), radius)
            start_frames = [img]

        super().__init__(start_frames, 0.12, True, *groups)


        # ---------- SFX ----------
        try:
            self.sfx_hit = self.game.resources.load_sound("sfx/enemy_hit.wav")
            self.sfx_hit.set_volume(0.9)
        except FileNotFoundError:
            self.sfx_hit = None  # กัน error ถ้ายังไม่มีไฟล์

        # ตั้งตำแหน่งเริ่มต้น
        self.rect.center = pos

        # ใช้ center (Vector2) + radius สำหรับระบบชนแบบวงกลม
        self.pos = pygame.math.Vector2(self.rect.center)
        self.radius: float = 10.0  # ลอง 8–12 แล้วดูว่าเข้ากำแพงสวยที่สุดค่าไหน


        # ---------- Combat stats (RPG style) ----------
        self.stats = Stats(
            max_hp=100,
            hp=100,
            attack=20,
            magic=5,
            armor=5,
            resistances={"physical": 0.0},
            crit_chance=0.1,
            crit_multiplier=1.7,
        )

        # สำเนาค่า base stats สำหรับ recalculation จาก equipment
        self.base_stats = Stats(
            max_hp=self.stats.max_hp,
            hp=self.stats.hp,
            attack=self.stats.attack,
            magic=self.stats.magic,
            armor=self.stats.armor,
            resistances=dict(self.stats.resistances),
            crit_chance=self.stats.crit_chance,
            crit_multiplier=self.stats.crit_multiplier,
        )

        # จัดการ buff/debuff
        self.status = StatusEffectManager(self)

        # ---------- Inventory / Equipment ----------
        if Inventory is not None:
            self.inventory = Inventory(size=20)
            # ตัวอย่างของเริ่มต้น
            self.inventory.add_item("potion_small", 5)
            self.inventory.add_item("sword_basic", 1)
        else:
            self.inventory = None

        if Equipment is not None:
            self.equipment = Equipment()
        else:
            self.equipment = None

        # คำนวณ stats จากอุปกรณ์ (ตอนเริ่มเกม)
        self._recalc_stats_from_equipment()

        # ---------- Movement / collision ----------
        self.move_speed = PLAYER_SPEED
        self.collision_rects: list[pygame.Rect] = []

        # ---------- Shoot cooldown ----------
        self.shoot_cooldown = 0.5
        self.shoot_timer = 0.0

        # ---------- Attack animation timer ----------
        self.attack_timer: float = 0.0

        # ----- DEBUG melee hitbox effect -----
        self.debug_attack_rect: pygame.Rect | None = None
        self.debug_attack_timer: float = 0.0
        # ----- DEBUG melee hitbox effect -----

        # ---------- Temporary weapon buff: sword_all_direction ----------
        self.sword_all_dir_timer: float = 0.0
        self.sword_all_dir_prev_main_hand: str | None = None



    # ============================================================
    # Animation loading
    # ============================================================
    def _load_animations(self) -> None:
        states = ["idle", "walk", "attack", "hurt", "dead", "cast"]

        # รองรับ 8 ทิศ
        directions = [
            "down", "left", "right", "up",
            "down_left", "down_right", "up_left", "up_right",
        ]

        for state in states:
            for direction in directions:
                frames = self._load_animation_sequence(state, direction)
                if frames:
                    self.animations[(state, direction)] = frames


    def _load_animation_sequence(self, state: str, direction: str) -> list[pygame.Surface]:
        frames: list[pygame.Surface] = []
        index = 1
        while True:
            rel_path = f"player/{state}/{state}_{direction}_{index:02d}.png"
            try:
                surf = self.game.resources.load_image(rel_path)
            except Exception:
                break
            frames.append(surf)
            index += 1
        return frames
    
    # โหลดแฟรมท่ายิงธนู
    def _load_bow_attack_animations(self) -> None:
        """
        โหลดเฟรม:
        assets/graphics/images/player/attack/attack_arrow_<direction>_01.png ...
        """
        directions = [
            "down", "left", "right", "up",
            "down_left", "down_right", "up_left", "up_right",
        ]

        for direction in directions:
            frames: list[pygame.Surface] = []
            index = 1
            while True:
                rel_path = f"player/attack/attack_arrow_{direction}_{index:02d}.png"
                try:
                    surf = self.game.resources.load_image(rel_path)
                except Exception:
                    break
                frames.append(surf)
                index += 1

            if frames:
                self.bow_attack_animations[direction] = frames


    # ============================================================
    # Equipment / Stats
    # ============================================================
    def _recalc_stats_from_equipment(self) -> None:
        """
        รีเซ็ต stats จาก base แล้วบวกผลจากอุปกรณ์:
        - main_hand (เช่น bow_power_1, sword_basic)
        - armor (เช่น shield)
        """
        # เก็บ ratio HP เดิมไว้
        old_max = self.stats.max_hp if self.stats.max_hp > 0 else 1
        hp_ratio = self.stats.hp / old_max

        # รีเซ็ตจาก base
        self.stats.max_hp = self.base_stats.max_hp
        self.stats.attack = self.base_stats.attack
        self.stats.magic = self.base_stats.magic
        self.stats.armor = self.base_stats.armor
        self.stats.resistances = dict(self.base_stats.resistances)
        self.stats.crit_chance = self.base_stats.crit_chance
        self.stats.crit_multiplier = self.base_stats.crit_multiplier

        # restore HP ตามสัดส่วน
        self.stats.hp = min(self.stats.max_hp, self.stats.max_hp * hp_ratio)

        if self.equipment is None:
            return

        # ----- weapon (main_hand) -----
        weapon = self.equipment.get_item("main_hand")
        if weapon:
            if weapon.id == "sword_basic":
                self.stats.attack += 5
            elif weapon.id == "bow_power_1":
                # ธนูเพิ่มดาเมจ + โอกาสติดคริ
                self.stats.attack += 4
                self.stats.crit_chance += 0.05

            elif weapon.id == "sword_all_direction":
                # ธนูเพิ่มดาเมจ + โอกาสติดคริ
                self.stats.attack += 4
                self.stats.crit_chance += 0.05

            # เผื่ออนาคตมี bow_power_2, bow_power_3
            elif weapon.id.startswith("bow_power_"):
                self.stats.attack += 6
                self.stats.crit_chance += 0.08

        # ----- armor / shield -----
        armor_item = self.equipment.get_item("armor")
        if armor_item:
            if armor_item.id == "shield":
                self.stats.armor += 6
                # self.stats.resistances["physical"] = \
                #     self.stats.resistances.get("physical", 0.0) + 0.1

    
    # ============================================================
    # Temporary weapon buff: sword_all_direction

    def activate_sword_all_direction(self, duration: float = 10.0) -> None:
        """
        เปิดใช้ดาบตี 8 ทิศแบบมีเวลาจำกัด

        - เก็บ main_hand เดิมไว้
        - ใส่ sword_all_direction เป็นอาวุธหลัก
        - นับเวลาถอยหลังด้วย self.sword_all_dir_timer
        """
        if getattr(self, "equipment", None) is None:
            return

        # ถ้ามีบัฟนี้อยู่แล้ว -> แค่รีเฟรชเวลา
        if self.sword_all_dir_timer > 0:
            self.sword_all_dir_timer = duration
            return

        # เก็บอาวุธเดิม (เก็บเป็น item_id ใน Equipment)
        self.sword_all_dir_prev_main_hand = self.equipment.main_hand

        # ใส่ดาบรอบทิศทาง
        self.equipment.main_hand = "sword_all_direction"

        # อัปเดต stats ใหม่ตามอุปกรณ์
        self._recalc_stats_from_equipment()

        # ตั้งเวลา
        self.sword_all_dir_timer = duration

    # ============================================================
    # Update sword_all_direction buff
    # ============================================================
    def _update_sword_all_direction(self, dt: float) -> None:
        """นับถอยหลังบัฟ sword_all_direction และคืนอาวุธเดิมเมื่อหมดเวลา"""
        if self.sword_all_dir_timer <= 0:
            return

        self.sword_all_dir_timer -= dt
        if self.sword_all_dir_timer <= 0:
            self.sword_all_dir_timer = 0.0

            # คืนอาวุธเดิม
            if getattr(self, "equipment", None) is not None:
                self.equipment.main_hand = self.sword_all_dir_prev_main_hand
                self._recalc_stats_from_equipment()

            self.sword_all_dir_prev_main_hand = None


    # ============================================================
    # Collision helper
    # ============================================================
    def set_collision_rects(self, rects: list[pygame.Rect]) -> None:
        self.collision_rects = rects
    
    # circle vs segment
    def set_collision_segments(
        self,
        segments: list[tuple[pygame.Vector2, pygame.Vector2]],
    ) -> None:
        """
        ให้ GameScene ส่งเส้น boundary จาก TileMap มาให้
        """
        self.collision_segments = segments


    # ============================================================
    # Input / movement / animation
    # ============================================================
    def _handle_input(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        move = pygame.Vector2(0, 0)

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move.y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move.x += 1

        if move.length_squared() > 0:
            move = move.normalize()
            self.velocity = move * self.move_speed
            self.facing = move
        else:
            self.velocity.update(0, 0)


        # ใช้ระบบชนกำแพงแบบวงกลม + segment
        self._move_and_collide_circle(dt)



    def _move_and_collide(self, dx: float, dy: float) -> None:
        """
        เลื่อนตัวละครตาม dx, dy แล้วเช็คชนกับ self.collision_rects
        ใช้การแก้ชนแบบทีละแกน (horizontal -> vertical)
        """
        # เผื่อกรณียังไม่ได้ถูกเซ็ตจาก GameScene
        walls = getattr(self, "collision_rects", []) or []

        # ----- แกน X -----
        if dx != 0:
            self.rect.x += int(dx)
            for wall in walls:
                if self.rect.colliderect(wall):
                    if dx > 0:   # เดินมาทางขวา ชนกำแพงด้านขวา
                        self.rect.right = wall.left
                    else:        # เดินมาทางซ้าย
                        self.rect.left = wall.right

        # ----- แกน Y -----
        if dy != 0:
            self.rect.y += int(dy)
            for wall in walls:
                if self.rect.colliderect(wall):
                    if dy > 0:   # เดินลง
                        self.rect.bottom = wall.top
                    else:        # เดินขึ้น
                        self.rect.top = wall.bottom

    
    def _move_and_collide_circle(self, dt: float) -> None:
        """
        ใช้ self.pos (center) + self.radius ชนกับ collision_segments
        ถ้าไม่มี segment จะ fallback ไปใช้ rect-based เดิม
        """
        segments = getattr(self, "collision_segments", []) or []

        # ถ้าไม่มีข้อมูล segment เลย → ใช้ระบบ rect เดิม
        if not segments:
            dx = self.velocity.x * dt
            dy = self.velocity.y * dt
            self._move_and_collide(dx, dy)
            # sync pos จาก rect
            self.pos.update(self.rect.centerx, self.rect.centery)
            return

        # ตำแหน่งที่อยากไป (ก่อนชน)
        desired = self.pos + self.velocity * dt
        new_pos = pygame.Vector2(desired)
        r = self.radius

        # loop 2–3 รอบเผื่อชนหลายเส้นซ้อนกัน
        for _ in range(3):
            moved = False
            for a, b in segments:
                # broad-phase: AABB รอบ segment เพื่อลดจำนวนที่ต้องเช็คจริง
                min_x = min(a.x, b.x) - r
                max_x = max(a.x, b.x) + r
                min_y = min(a.y, b.y) - r
                max_y = max(a.y, b.y) + r

                if not (min_x <= new_pos.x <= max_x and
                        min_y <= new_pos.y <= max_y):
                    continue

                mtv = circle_segment_mtv(new_pos, r, a, b)
                if mtv is not None:
                    new_pos += mtv
                    moved = True

            if not moved:
                break

        self.pos = new_pos
        self.rect.center = (round(self.pos.x), round(self.pos.y))



    def _update_animation_state(self) -> None:
        # ---------- อัปเดตทิศทางจาก vector การหัน (รองรับ 8 ทิศ) ----------
        x, y = self.facing.x, self.facing.y

        # ถ้าไม่ขยับเลย ให้ใช้ทิศเดิม
        if not (x == 0 and y == 0):
            DIAGONAL_THRESHOLD = 0.35  # ค่าประมาณว่า "เอียงพอเป็นทแยง"

            if abs(x) >= DIAGONAL_THRESHOLD and abs(y) >= DIAGONAL_THRESHOLD:
                # ทิศทแยง
                if y < 0:
                    # ขึ้น
                    self.direction = "up_right" if x > 0 else "up_left"
                else:
                    # ลง
                    self.direction = "down_right" if x > 0 else "down_left"
            else:
                # ทิศหลัก 4 ทิศ
                if abs(x) > abs(y):
                    self.direction = "right" if x > 0 else "left"
                else:
                    self.direction = "down" if y >= 0 else "up"

        # ---------- เลือก state ตาม priority ----------
        # 1) dead
        if getattr(self, "is_dead", False) and ("dead", self.direction) in self.animations:
            self.state = "dead"
            return

        # 2) hurt
        if getattr(self, "hurt_timer", 0.0) > 0 and ("hurt", self.direction) in self.animations:
            self.state = "hurt"
            return

        # 3) attack (ใช้ attack_timer เป็นตัวล็อกเวลา)
        if getattr(self, "attack_timer", 0.0) > 0:
            # มีท่าฟันแบบใกล้ (attack_*)
            has_melee = ("attack", self.direction) in self.animations
            # หรือมีท่ายิงธนู (attack_arrow_*)
            has_bow = self.direction in getattr(self, "bow_attack_animations", {})

            if has_melee or has_bow:
                self.state = "attack"
                return


        # 4) walk / idle
        if self.velocity.length_squared() > 0:
            self.state = "walk"
        else:
            self.state = "idle"


    # ฟันได้ทุกทิศ (8 ทิศ) แต่ถ้าไม่มีไฟล์ทิศทแยง
    # จะ fallback ไปใช้ทิศหลักแทน (up/down)

    def _apply_animation(self) -> None:
        state = self.state
        direction = self.direction

        frames: list[pygame.Surface] | None = None

        # mapping ทิศทแยง -> ทิศหลัก (เอาไว้ fallback ถ้าไม่มีไฟล์)
        diag_to_cardinal = {
            "up_left": "up",
            "up_right": "up",
            "down_left": "down",
            "down_right": "down",
        }

        # ---------- กรณีโจมตีด้วยธนู ----------
        if state == "attack" and getattr(self, "equipment", None) is not None:
            weapon = self.equipment.get_item("main_hand")

            if (
                weapon
                and weapon.item_type == "weapon"
                and weapon.id.startswith("bow_")
                and hasattr(self, "bow_attack_animations")
            ):
                # พยายามใช้ทิศตรงก่อน (รวมถึง up_left, down_right, ...)
                frames = self.bow_attack_animations.get(direction)

                # ถ้าไม่มีเฟรมสำหรับทิศทแยง -> ลองใช้ทิศหลักแทน (up/down)
                if frames is None and direction in diag_to_cardinal:
                    fallback_dir = diag_to_cardinal[direction]
                    frames = self.bow_attack_animations.get(fallback_dir)

        # ---------- กรณีปกติ (ทุก state) ----------
        if frames is None:
            frames = self.animations.get((state, direction))

            # ถ้าเป็นทิศทแยงและไม่มีเฟรม -> ลองใช้เฟรมทิศหลักแทน
            if not frames and direction in diag_to_cardinal:
                fallback_dir = diag_to_cardinal[direction]
                frames = self.animations.get((state, fallback_dir))

        if not frames:
            return

        if frames is not self.frames:
            self.set_frames(frames, reset=False)



    # ============================================================
    # Damage / combat
    # ============================================================
    def _get_current_weapon_base_damage(self) -> int:
        """
        base damage สำหรับใช้ยิงธนู/ฟัน
        - มือเปล่า      -> 10
        - sword_basic   -> 15
        - bow_power_1   -> 25
        - sword_all_direction   -> 25
        """
        if getattr(self, "equipment", None) is not None:
            weapon = self.equipment.get_item("main_hand")
            if weapon and weapon.item_type == "weapon":
                if weapon.id == "bow_power_1":
                    return 35
                if weapon.id == "sword_basic":
                    return 15
                if weapon.id == "sword_all_direction":
                    return 25
        return 10
    

    # คำนวณกรอบโจมตีสำหรับฟันระยะใกล้
    def _get_attack_rect(
        self,
        facing: pygame.Vector2 | None = None,
        distance: float = 48.0,
    ) -> pygame.Rect:
        """
        คำนวณกรอบโจมตีสำหรับฟันระยะใกล้
        - ใช้เวกเตอร์ทิศทาง (facing) รองรับทุกมุม (4 หรือ 8 ทิศก็ได้)
        - distance = ขนาดกรอบโจมตี (และเป็นฐานใช้คำนวณระยะจากตัวละคร)
        """

        if facing is None:
            facing = self.facing

        # ถ้าไม่มีทิศชัดเจน (ยืนนิ่ง) ให้สมมติว่าหันลง
        if not isinstance(facing, pygame.Vector2) or facing.length_squared() == 0:
            facing = pygame.Vector2(0, 1)

        # ทำให้เป็นเวกเตอร์หน่วย
        dir_vec = facing.normalize()

        # ขนาด hitbox (สี่เหลี่ยมจัตุรัส)
        size = distance
        attack_rect = pygame.Rect(0, 0, size, size)

        # จุดกลางของ player
        cx, cy = self.rect.center

        # offset จากตัวละคร → center ของ hitbox
        half_body = max(self.rect.width, self.rect.height) * 0.5
        half_hit = size * 0.5
        offset = half_body + half_hit

        attack_rect.centerx = cx + dir_vec.x * offset
        attack_rect.centery = cy + dir_vec.y * offset

        return attack_rect



    # การโจมตีระยะใกล้ (ฟันดาบ / ต่อยมือเปล่า)
    def _melee_slash(self) -> None:
        """
        โจมตีระยะใกล้ (ฟันดาบ / ต่อยมือเปล่า)
        - ใช้ DamagePacket + enemy.take_hit() เหมือน projectile
        - ถ้าใช้อาวุธ sword_all_direction จะฟันครบ 8 ทิศและเรียก SlashEffectNode
          ให้ไปวาดเอฟเฟ็กต์ตามมุมมอง isometric 25°
        """

        # เล่นเสียงฟัน (ถ้ามีโหลดไว้)
        if hasattr(self, "sfx_slash") and self.sfx_slash:
            self.sfx_slash.play()

        # ตั้ง state เป็น attack เพื่อให้ระบบ animation ล็อกท่าฟัน
        self.state = "attack"
        self.attack_timer = 0.25  # ระยะเวลาที่อยู่ในท่าโจมตี

        # ดูว่าในมือมีอาวุธอะไรอยู่
        weapon_id: str | None = None
        if getattr(self, "equipment", None) is not None:
            weapon = self.equipment.get_item("main_hand")
            if weapon and weapon.item_type == "weapon":
                weapon_id = weapon.id

        # ดาเมจพื้นฐานจากอาวุธ/ตัวละคร
        base_damage = self._get_current_weapon_base_damage()

        # สร้าง DamagePacket (เหมือนใช้กับ projectile)
        packet = DamagePacket(
            base=base_damage,
            damage_type="physical",
            scaling_attack=1.0,
        )

        RANGE = 64  # ระยะเอื้อมของดาบ (ฐานใช้คำนวณขนาด/ระยะ hitbox)

        # ============================================================
        # กรณีดาบฟันรอบทิศทาง -> ฟันครบ 8 ทิศ
        # ============================================================
        if weapon_id == "sword_all_direction":
            from pygame.math import Vector2

            # 8 ทิศรอบตัว (ใช้ร่วมกับชื่อ direction สำหรับ SlashEffectNode)
            directions: list[Vector2] = [
                Vector2(0, -1),    # up
                Vector2(1, -1),    # up_right
                Vector2(1, 0),     # right
                Vector2(1, 1),     # down_right
                Vector2(0, 1),     # down
                Vector2(-1, 1),    # down_left
                Vector2(-1, 0),    # left
                Vector2(-1, -1),   # up_left
            ]

            dir_names: list[str] = [
                "up",
                "up_right",
                "right",
                "down_right",
                "down",
                "down_left",
                "left",
                "up_left",
            ]

            attack_rects: list[pygame.Rect] = []

            # จุดกลางของตัวละคร (world space)
            cx, cy = self.rect.center
            size = RANGE * 0.8

            # ระยะจาก center player → center hitbox ของแต่ละทิศ
            offset = max(self.rect.width, self.rect.height) + size

            for dir_vec, slash_dir in zip(directions, dir_names):
                if dir_vec.length_squared() == 0:
                    continue

                dir_norm = dir_vec.normalize()

                # สร้างกรอบสี่เหลี่ยมเป็น hitbox
                attack_rect = pygame.Rect(0, 0, size, size)
                attack_rect.centerx = cx + dir_norm.x * offset
                attack_rect.centery = cy + dir_norm.y * offset

                # ขยายกรอบให้ตีโดนง่ายขึ้น
                attack_rect.inflate_ip(10, 10)
                attack_rects.append(attack_rect)

                # สร้างเอฟเฟ็กต์ฟันตามทิศนั้น ๆ
                # SlashEffectNode จะไปวาดเส้นโค้งตามมุมมอง isometric 25° เอง
                SlashEffectNode(
                    self.game,
                    attack_rect,
                    slash_dir,
                    self.game.all_sprites,
                )

                # ถ้ามีรูปดาบให้วิ่งตามเส้นโค้งร่วมกับเอฟเฟ็กต์
                if getattr(self, "sword_slash_image", None) is not None:
                    SwordSlashArcNode(
                        self.game,                 # game
                        self.rect.center,          # center_pos
                        slash_dir,                 # direction
                        self.sword_slash_image,    # sword_image
                        offset,                    # radius
                        0.20,                      # duration
                        self.game.all_sprites,     # *groups
                    )

            # เช็คว่าศัตรูตัวไหนโดนฟัน (โดนซ้ำหลายทิศก็ให้โดนครั้งเดียว)
            hit_enemies: set[object] = set()
            for enemy in self.game.enemies.sprites():
                for rect in attack_rects:
                    if rect.colliderect(enemy.rect):
                        if enemy not in hit_enemies:
                            enemy.take_hit(self.stats, packet)
                            hit_enemies.add(enemy)
                        break  # ตัวนี้โดนแล้ว ไม่ต้องเช็ค rect อื่นต่อ

        # ============================================================
        # อาวุธอื่น ๆ -> ฟันทิศเดียว (ตามทิศที่ player หัน)
        # ============================================================
        else:
            # ใช้ helper คำนวณกรอบโจมตีในทิศ self.facing
            attack_rect = self._get_attack_rect(distance=RANGE)

            # เลื่อนกรอบตามทิศหลัก (กันกรณี facing ยังเป็น 0,0)
            if abs(self.facing.x) > abs(self.facing.y):
                # ซ้าย–ขวา
                if self.facing.x > 0:
                    attack_rect.x += attack_rect.width   # ขวา
                else:
                    attack_rect.x -= RANGE               # ซ้าย
            else:
                # บน–ล่าง
                if self.facing.y > 0:
                    attack_rect.y += attack_rect.height  # ล่าง
                else:
                    attack_rect.y -= RANGE               # บน

            # ขยายกรอบอีกนิดให้ตีโดนง่าย
            attack_rect.inflate_ip(10, 10)

            # เอฟเฟ็กต์ฟันดาบตามทิศที่ player หัน
            SlashEffectNode(
                self.game,
                attack_rect,
                self.direction,          # "up" / "down" / "left" / "right" / ทแยง
                self.game.all_sprites,
            )

            # =============================
            # ถ้าต้องการแสดงอาวุธที่เอฟเฟ็กต์ฟันดาบ
            # =============================
            # if getattr(self, "sword_slash_image", None) is not None:
            #     SwordSlashArcNode(
            #         self.game,                 # game
            #         self.rect.center,          # center_pos
            #         self.direction,            # direction
            #         self.sword_slash_image,    # sword_image
            #         max(self.rect.width, self.rect.height) + RANGE,    # radius
            #         0.20,                      # duration
            #         self.game.all_sprites,     # *groups
            #     )

            # ตรวจศัตรูที่อยู่ในกรอบ
            for enemy in self.game.enemies.sprites():
                if attack_rect.colliderect(enemy.rect):
                    enemy.take_hit(self.stats, packet)

        # ตั้ง cooldown โจมตี
        self.shoot_timer = self.shoot_cooldown


    def _shoot_projectile(self) -> None:
        # เล่นเสียงยิงธนู
        if hasattr(self, "sfx_bow_shoot"):
            self.sfx_bow_shoot.play()

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

        # ให้ตัวละครเล่นท่า "โจมตี" ช่วงสั้น ๆ (เอาไว้เลือกเฟรม attack_arrow)
        self.state = "attack"
        self.attack_timer = 1.0

        # ตั้ง cooldown การยิง
        self.shoot_timer = self.shoot_cooldown


    def shoot(self) -> None:
        if self.shoot_timer > 0:
            return

        # ดูว่า main_hand เป็นอาวุธแบบไหน
        weapon = None
        if getattr(self, "equipment", None) is not None:
            weapon = self.equipment.get_item("main_hand")

        # ถ้ามี bow_xxx อยู่ที่มือหลัก -> ยิงระยะไกล
        if weapon and weapon.item_type == "weapon" and weapon.id.startswith("bow_"):
            self._shoot_projectile()
        else:
            # ค่าเริ่มต้น = ฟันระยะใกล้ (ดาบ / มือเปล่า)
            self._melee_slash()

    # เมื่อโดนโจมตี
    def take_hit(self, attacker_stats: Stats, damage_packet: DamagePacket) -> DamageResult:
        # modifier จาก status (เช่น buff ลดดาเมจ)
        dmg_mult = self.status.get_multiplier("damage_taken")
        damage_packet.attacker_multiplier *= dmg_mult

        # คำนวณดาเมจ + หัก HP จริง
        result = compute_damage(attacker_stats, self.stats, damage_packet)

        print(
            f"[Player] took {result.final_damage} dmg "
            f"({'CRIT' if result.is_crit else 'normal'}), "
            f"HP: {self.stats.hp}/{self.stats.max_hp}"
        )

        # 🔊 เล่นเสียงโดนตี (ถ้ามีไฟล์)
        if hasattr(self, "sfx_hit"):
            self.sfx_hit.play()

        if result.killed:
            print("[Player] died")
            self.is_dead = True
            self.hurt_timer = 0.0
            # หยุดการเคลื่อนที่
            self.velocity.update(0, 0)
        else:
            # ยังไม่ตาย -> ให้เล่นแอนิเมชันโดนตีสั้น ๆ
            self.hurt_timer = 0.25

        return result


    # ============================================================
    # Update
    # ============================================================
    def update(self, dt: float) -> None:
        # buff/debuff
        self.status.update(dt)

        # นับเวลาบัฟดาบรอบทิศทาง
        self._update_sword_all_direction(dt)

        # นับเวลาถูกโจมตี (ใช้เล่นแอนิเมชัน hurt)
        if getattr(self, "hurt_timer", 0.0) > 0:
            self.hurt_timer -= dt
            if self.hurt_timer < 0:
                self.hurt_timer = 0.0

        # cooldown การยิง
        if self.shoot_timer > 0:
            self.shoot_timer -= dt
            if self.shoot_timer < 0:
                self.shoot_timer = 0

        # ลดเวลาการแสดงท่าโจมตี (attack animation)
        if getattr(self, "attack_timer", 0.0) > 0:
            self.attack_timer -= dt
            if self.attack_timer < 0:
                self.attack_timer = 0.0

        # ถ้าตายแล้ว -> ไม่รับอินพุต ไม่ขยับ
        if getattr(self, "is_dead", False):
            self.velocity.update(0, 0)
        else:
            # อินพุต + การเคลื่อนที่ + แอนิเมชัน
            self._handle_input(dt)

        self._update_animation_state()
        self._apply_animation()

        super().update(dt)

