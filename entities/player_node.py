# entities/player_node.py
from __future__ import annotations

import pygame

from .animated_node import AnimatedNode
from combat.damage_system import Stats, DamagePacket, DamageResult, compute_damage
from combat.status_effect_system import StatusEffectManager
from config.settings import PLAYER_SPEED
from .projectile_node import ProjectileNode

# optional imports (เผื่อยังไม่มีระบบ inventory/equipment)
try:
    from items.inventory import Inventory
    from items.equipment import Equipment
except ImportError:
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

        # ---------- SFX (ใช้ ResourceManager โหลดเสียง) ----------
        self.sfx_slash = self.game.resources.load_sound("sfx/slash.wav")
        self.sfx_bow_shoot = self.game.resources.load_sound("sfx/bow_shoot.wav")

        # ใช้ slash.wav เป็นเสียงเก็บไอเท็มด้วย
        self.sfx_item_pickup = self.sfx_slash

        self.sfx_slash.set_volume(0.7)
        self.sfx_bow_shoot.set_volume(0.7)
        # ถ้าอยากให้ตอนเก็บของเบากว่านิดนึงก็ได้ เช่น:
        # self.sfx_item_pickup.set_volume(0.5)


        # ---------- Animation state ----------
        self.animations: dict[tuple[str, str], list[pygame.Surface]] = {}
        self.state: str = "idle"      # idle / walk / attack / hurt / dead / cast
        self.direction: str = "down"  # down / left / right / up

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

        # ตั้งตำแหน่งเริ่มต้น
        self.rect.center = pos

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
        self.shoot_cooldown = 0.8
        self.shoot_timer = 0.0

        # ---------- Attack animation timer ----------
        self.attack_timer: float = 0.0

    # ============================================================
    # Animation loading
    # ============================================================
    def _load_animations(self) -> None:
        states = ["idle", "walk", "attack", "hurt", "dead", "cast"]
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
        directions = ["down", "left", "right", "up"]

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
    # Collision helper
    # ============================================================
    def set_collision_rects(self, rects: list[pygame.Rect]) -> None:
        self.collision_rects = rects

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

        # ใช้ระบบชนกำแพง แทนการเลื่อนตรง ๆ
        dx = self.velocity.x * dt
        dy = self.velocity.y * dt
        self._move_and_collide(dx, dy)


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


    def _update_animation_state(self) -> None:
        # อัปเดตทิศทางพื้นฐานจาก vector การหัน
        x, y = self.facing.x, self.facing.y
        if abs(x) > abs(y):
            self.direction = "right" if x > 0 else "left"
        else:
            self.direction = "down" if y >= 0 else "up"

        # ถ้ายังอยู่ในช่วงเล่น animation โจมตี และมีเฟรม attack อยู่ ให้ล็อก state = "attack"
        if getattr(self, "attack_timer", 0.0) > 0 and ("attack", self.direction) in self.animations:
            self.state = "attack"
            return

        # ปกติ: เดิน / ยืน
        if self.velocity.length_squared() > 0:
            self.state = "walk"
        else:
            self.state = "idle"


    def _apply_animation(self) -> None:
        state = self.state
        direction = self.direction

        frames: list[pygame.Surface] | None = None

        # ถ้าเป็นท่าโจมตี ให้เช็คก่อนว่าถือธนูอยู่ไหม
        if state == "attack" and getattr(self, "equipment", None) is not None:
            weapon = self.equipment.get_item("main_hand")

            if (
                weapon
                and weapon.item_type == "weapon"
                and weapon.id.startswith("bow_")
                and hasattr(self, "bow_attack_animations")
            ):
                # ถ้ามีเฟรมท่ายิงธนูสำหรับทิศนี้ ให้ใช้แทนท่าฟัน
                frames = self.bow_attack_animations.get(direction)

        # ถ้าไม่ได้ถือธนู หรือไม่มีเฟรมธนู -> ใช้เฟรมปกติ
        if frames is None:
            frames = self.animations.get((state, direction))

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
        """
        if getattr(self, "equipment", None) is not None:
            weapon = self.equipment.get_item("main_hand")
            if weapon and weapon.item_type == "weapon":
                if weapon.id == "bow_power_1":
                    return 25
                if weapon.id == "sword_basic":
                    return 15
        return 10

    def _melee_slash(self) -> None:
        """
        โจมตีระยะใกล้ (ฟันดาบ / ต่อยมือเปล่า)
        ใช้ DamagePacket + enemy.take_hit() เหมือน projectile
        """

        # เล่นเสียงฟัน
        if hasattr(self, "sfx_slash"):
            self.sfx_slash.play()
        # ตั้ง state เป็น attack เพื่อเล่น animation ถ้ามี
        self.state = "attack"
        # ล็อกสถานะโจมตีช่วงสั้น ๆ เพื่อให้เห็นท่าฟันครบ
        self.attack_timer = 0.25

        base_damage = self._get_current_weapon_base_damage()

        packet = DamagePacket(
            base=base_damage,
            damage_type="physical",
            scaling_attack=1.0,
        )

        # สร้าง hitbox ด้านหน้าตัวละคร
        attack_rect = self.rect.copy()
        RANGE = 32  # ระยะเอื้อมของดาบ

        if abs(self.facing.x) > abs(self.facing.y):
            # ซ้าย–ขวา
            if self.facing.x > 0:
                attack_rect.x += attack_rect.width  # ขวา
            else:
                attack_rect.x -= RANGE              # ซ้าย
        else:
            # บน–ล่าง
            if self.facing.y > 0:
                attack_rect.y += attack_rect.height  # ล่าง
            else:
                attack_rect.y -= RANGE               # บน

        # ขยายกรอบให้ใหญ่ขึ้นหน่อย
        attack_rect.inflate_ip(10, 10)

        # เช็คทุก enemy ว่าโดนฟันไหม
        for enemy in self.game.enemies.sprites():
            if attack_rect.colliderect(enemy.rect):
                enemy.take_hit(self.stats, packet)

        # cooldown โจมตี
        self.shoot_timer = self.shoot_cooldown

    # def _shoot_projectile(self) -> None:
        
        
    #     # เล่นเสียงยิงธนู
    #     if hasattr(self, "sfx_bow_shoot"):
    #         self.sfx_bow_shoot.play()
    #     direction = self.facing
    #     if direction.length_squared() == 0:
    #         direction = pygame.Vector2(1, 0)

    #     base_damage = self._get_current_weapon_base_damage()

    #     packet = DamagePacket(
    #         base=base_damage,
    #         damage_type="physical",
    #         scaling_attack=0.8,
    #     )

    #     ProjectileNode(
    #         self,
    #         self.rect.center,
    #         direction,
    #         450,
    #         packet,
    #         1.5,
    #         self.projectile_group,
    #         self.game.all_sprites,
    #     )

    #     self.shoot_timer = self.shoot_cooldown

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
        self.attack_timer = 0.25

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
        dmg_mult = self.status.get_multiplier("damage_taken")
        damage_packet.attacker_multiplier *= dmg_mult

        result = compute_damage(attacker_stats, self.stats, damage_packet)

        print(
            f"[Player] took {result.final_damage} dmg "
            f"({'CRIT' if result.is_crit else 'normal'}), "
            f"HP: {self.stats.hp}/{self.stats.max_hp}"
        )

        if result.killed:
            print("[Player] died")

        return result


    # ============================================================
    # Update
    # ============================================================
    def update(self, dt: float) -> None:
        # buff/debuff
        self.status.update(dt)

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

        # อินพุต + การเคลื่อนที่ + แอนิเมชัน
        self._handle_input(dt)
        self._update_animation_state()
        self._apply_animation()

        super().update(dt)
