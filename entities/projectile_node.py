# entities/projectile_node.py
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
import weakref

import pygame

from .animated_node import AnimatedNode
from combat.damage_system import DamagePacket

__all__ = ["ProjectileNode"]


# ============================================================
# Comet Trail (Arrow Path VFX)
# ============================================================

@dataclass
class _TrailPoint:
    pos: pygame.Vector2
    age: float


class ArrowCometTrailNode(pygame.sprite.Sprite):
    """หางดาวหาง (comet ribbon) สำหรับลูกธนู (ไม่มีจุดสปาร์ค)

    - ริบบอน “หัวหนา-ท้ายบาง” (taper)
    - core highlight ด้านใน (อ่านวิถีชัด)
    - ไม่มี spark/dots/วงกลมปลาย (ตามที่ไม่ต้องการ)
    - ผูกกับ projectile: projectile หาย -> trail หายเอง
    """

    def __init__(
        self,
        projectile: pygame.sprite.Sprite,
        *groups: pygame.sprite.AbstractGroup,
        life: float = 0.18,
        sample_interval: float = 0.010,
        max_points: int = 26,
        max_thickness: int = 11,
        min_thickness: int = 2,
        glow_passes: int = 2,
        main_rgb: tuple[int, int, int] = (255, 210, 120),
        core_rgb: tuple[int, int, int] = (255, 255, 255),
        alpha_main: int = 165,
        alpha_core: int = 220,
    ) -> None:
        # วาง trail “หลัง” projectile ถ้าโปรเจกต์ใช้ layer
        try:
            self._layer = int(getattr(projectile, "_layer", 0)) - 1
        except Exception:
            pass

        super().__init__(*groups)

        self._target_ref = weakref.ref(projectile)

        self.life = max(0.06, float(life))
        self.sample_interval = max(0.004, float(sample_interval))
        self.max_points = max(8, int(max_points))

        self.max_thickness = max(2, int(max_thickness))
        self.min_thickness = max(1, int(min_thickness))
        self.glow_passes = max(0, int(glow_passes))

        self.main_rgb = main_rgb
        self.core_rgb = core_rgb
        self.alpha_main = max(0, min(255, int(alpha_main)))
        self.alpha_core = max(0, min(255, int(alpha_core)))

        self._timer = 0.0
        self._pts: deque[_TrailPoint] = deque(maxlen=self.max_points)
        self._dirty = True

        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect = self.image.get_rect()

        self._push_point(force=True)

    def _target(self) -> pygame.sprite.Sprite | None:
        return self._target_ref()

    def _get_target_center(self) -> pygame.Vector2 | None:
        t = self._target()
        if t is None or not hasattr(t, "rect"):
            return None
        return pygame.Vector2(t.rect.center)

    def _push_point(self, force: bool = False) -> None:
        c = self._get_target_center()
        if c is None:
            return
        if not force and self._pts:
            if (self._pts[0].pos - c).length_squared() < 1.0:
                return
        self._pts.appendleft(_TrailPoint(pos=c, age=0.0))
        self._dirty = True

    @staticmethod
    def _ease_out(t: float) -> float:
        t = max(0.0, min(1.0, t))
        return 1.0 - (1.0 - t) * (1.0 - t)

    def update(self, dt: float) -> None:
        dt = float(dt)

        t = self._target()
        if t is None or not t.alive():
            self.kill()
            return

        for p in self._pts:
            p.age += dt

        before = len(self._pts)
        while self._pts and self._pts[-1].age >= self.life:
            self._pts.pop()
        if len(self._pts) != before:
            self._dirty = True

        self._timer += dt
        while self._timer >= self.sample_interval:
            self._timer -= self.sample_interval
            self._push_point()

        if len(self._pts) < 2:
            return

        if self._dirty:
            self._rebuild_image()
            self._dirty = False

    def _rebuild_image(self) -> None:
        pts = [p.pos for p in self._pts]
        ages = [p.age for p in self._pts]

        min_x = min(p.x for p in pts)
        min_y = min(p.y for p in pts)
        max_x = max(p.x for p in pts)
        max_y = max(p.y for p in pts)

        pad = self.max_thickness * 2 + 6
        w = int(math.ceil(max_x - min_x)) + pad * 2
        h = int(math.ceil(max_y - min_y)) + pad * 2
        w = max(2, w)
        h = max(2, h)

        ox = min_x - pad
        oy = min_y - pad
        local = [pygame.Vector2(p.x - ox, p.y - oy) for p in pts]

        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        n = len(local)

        def draw_pass(rgb: tuple[int, int, int], alpha_base: int, thickness_mul: float) -> None:
            for i in range(n - 1):
                a_mid = (ages[i] + ages[i + 1]) * 0.5
                k = max(0.0, min(1.0, 1.0 - (a_mid / self.life)))  # 1=new, 0=old
                k = self._ease_out(k)

                thick = self.min_thickness + (self.max_thickness - self.min_thickness) * k
                thick = max(1, int(round(thick * thickness_mul)))

                a = int(alpha_base * (k ** 1.25))
                if a <= 0:
                    continue

                col = (rgb[0], rgb[1], rgb[2], max(0, min(255, a)))
                pygame.draw.line(surf, col, local[i], local[i + 1], thick)

        # glow (หนา + จาง)
        for g in range(self.glow_passes):
            mul = 1.9 + g * 0.7
            a = int(self.alpha_main * (0.20 / (g + 1)))
            draw_pass(self.main_rgb, a, mul)

        # main ribbon
        draw_pass(self.main_rgb, self.alpha_main, 1.0)

        # core highlight (บาง)
        draw_pass(self.core_rgb, self.alpha_core, 0.45)

        self.image = surf
        self.rect = self.image.get_rect(topleft=(int(ox), int(oy)))


# ============================================================
# Projectile
# ============================================================

class ProjectileNode(AnimatedNode):
    """
    กระสุนแบบ 'ลูกธนู' ที่มีแอนิเมชัน และหมุนตามทิศทาง (8 ทิศ)

    - owner          : ใครเป็นคนยิง (ต้องมี .game และ .stats)
    - damage_packet  : ใช้ตอนคำนวณดาเมจใน on_projectile_hit

    ✅ เพิ่ม: trail_theme (keyword-only) ให้ player_node คุมสีได้
        ProjectileNode(..., trail_theme="arcane" | "plasma" | "crimson" | ...)
    """

    # ธีมสีสำหรับ trail (แก้เพิ่มได้ในอนาคต แต่ไม่จำเป็นต้องแก้ถ้าคุมจาก player_node)
    _TRAIL_THEMES: dict[str, tuple[tuple[int,int,int], tuple[int,int,int], int, int]] = {
        "gold":     ((255, 210, 120), (255, 255, 255), 165, 220),
        "arcane":   ((180, 120, 255), (255, 255, 255), 175, 230),  # purple
        "plasma":   ((120, 230, 255), (255, 255, 255), 170, 230),  # cyan
        "crimson":  ((255, 110,  80), (255, 245, 235), 175, 230),  # red
        "holy":     ((255, 225, 140), (255, 255, 255), 170, 230),  # warm gold
        "toxic":    ((140, 255, 160), (255, 255, 255), 160, 220),  # green
        "storm":    (( 70, 255, 255), (255, 255, 255), 170, 230),  # teal
        # aliases
        "purple":   ((180, 120, 255), (255, 255, 255), 175, 230),
        "red":      ((255, 110,  80), (255, 245, 235), 175, 230),
        "blue":     ((120, 230, 255), (255, 255, 255), 170, 230),
        "cyan":     ((120, 230, 255), (255, 255, 255), 170, 230),
        "green":    ((140, 255, 160), (255, 255, 255), 160, 220),
    }

    def __init__(
        self,
        owner,
        pos: tuple[int, int],
        direction: pygame.Vector2,
        speed: float,
        damage_packet: DamagePacket,
        projectile_id: str = "arrow",
        lifetime: float = 1.5,
        *groups,
        trail_theme: str | None = None,
        homing: bool = False,
        homing_turn_rate: float = 4.0, # degrees per frame approx (or factor)
    ) -> None:
        # ---------- เก็บข้อมูลพื้นฐาน ----------
        self.owner = owner
        self.damage_packet = damage_packet

        self.speed = speed
        self.lifetime = lifetime
        self.age = 0.0
        self.projectile_id = projectile_id
        self.position = pygame.Vector2(pos)

        # Homing parameters
        self.homing = homing
        self.homing_turn_rate = homing_turn_rate
        self.homing_delay = 0.15  # วิ่งตรงก่อนแป๊บนึงค่อยเลี้ยว
        self.target: pygame.sprite.Sprite | None = None

        # เก็บ theme จาก caller (player_node)
        self.trail_theme = (trail_theme.strip().lower() if isinstance(trail_theme, str) and trail_theme.strip() else None)

        # กันทิศทาง (0, 0)
        if direction.length_squared() == 0:
            direction = pygame.Vector2(1, 0)
        self.direction = direction.normalize()

        # คำนวณมุมจากทิศทาง และ snap เป็น 8 ทิศ (step ละ 45°)
        self._update_angle()

        # ---------- โหลดเฟรม (จะถูกหมุนแล้ว) ----------
        # โหลดมาเก็บไว้ก่อน แล้วค่อย rotate ตามมุม real-time
        self.raw_frames = self._load_raw_frames()
        self._rotate_frames()

        frame_duration = 0.06
        loop = True

        super().__init__(self.frames, frame_duration, loop, *groups)

        self.rect.center = self.position

        # ✅ attach comet trail (arrow only)
        self._maybe_attach_comet_trail(groups)

    def _update_angle(self) -> None:
        dx, dy = self.direction.x, self.direction.y
        raw_angle = math.degrees(math.atan2(dy, dx))
        if not self.homing:
            # Snap 8 ทิศถ้าไม่ใช่ homing (แบบเดิม)
            snapped_angle = round(raw_angle / 45.0) * 45.0
            self._angle = snapped_angle
        else:
            # ถ้า homing ให้หมุนเนียนๆ
            self._angle = raw_angle

    def _load_raw_frames(self) -> list[pygame.Surface]:
        """โหลดเฟรมต้นฉบับ (ยังไม่หมุน)"""
        frames: list[pygame.Surface] = []
        resources = self.owner.game.resources

        index = 1
        while True:
            candidates = [
                f"projectiles/{self.projectile_id}/{self.projectile_id}_{index:02d}.png",
                f"projectiles/arrow/{self.projectile_id}_{index:02d}.png",
                f"projectiles/{self.projectile_id}_{index:02d}.png",
            ]
            
            base_frame = None
            for path in candidates:
                try:
                    base_frame = resources.load_image(path)
                    break
                except Exception:
                    continue
            
            if base_frame is None:
                break
            
            frames.append(base_frame)
            index += 1

        if not frames:
            # placeholder
            w, h = 24, 6
            base_frame = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(base_frame, (250, 230, 80), base_frame.get_rect())
            frames.append(base_frame)
            
        return frames

    def _rotate_frames(self) -> None:
        """สร้าง self.frames จาก self.raw_frames โดยหมุนตาม self._angle"""
        self.frames = []
        for f in self.raw_frames:
            rotated = pygame.transform.rotate(f, -self._angle)
            self.frames.append(rotated)
        
        # update current image in AnimatedNode
        if hasattr(self, "image") and hasattr(self, "frame_index"):
            idx = int(self.frame_index) % len(self.frames)
            self.image = self.frames[idx]
            # rect update center
            center = self.rect.center
            self.rect = self.image.get_rect()
            self.rect.center = center

    # ------------------------------------------------------------------
    # VFX auto attach
    # ------------------------------------------------------------------
    def _maybe_attach_comet_trail(self, groups) -> None:
        pid = (self.projectile_id or "").lower().strip()
        if pid not in ("arrow", "arrow2"):
            return

        # ถ้า caller ส่ง theme มา -> แสดงแน่
        theme = self.trail_theme

        # ถ้าไม่ส่ง theme มา -> fallback ตาม weapon_id เดิม (bow_power_1/2)
        weapon_id = None
        if theme is None:
            try:
                eq = getattr(self.owner, "equipment", None)
                if eq is not None:
                    wpn = eq.get_item("main_hand")
                    if wpn is not None:
                        weapon_id = getattr(wpn, "id", None)
            except Exception:
                weapon_id = None

            if weapon_id == "bow_power_2":
                theme = "arcane"
            elif weapon_id == "bow_power_1":
                theme = "gold"
            else:
                return  # ไม่ใช่ธนูที่ต้องมี trail

        pal = self._TRAIL_THEMES.get(theme, self._TRAIL_THEMES["gold"])
        main_rgb, core_rgb, a_main, a_core = pal

        # เลือก group สำหรับ render (โดยทั่วไป group สุดท้ายคือ all_sprites)
        render_group = None
        if groups:
            render_group = groups[-1]
        if render_group is None and hasattr(self.owner, "game"):
            render_group = getattr(self.owner.game, "all_sprites", None)
        if render_group is None:
            return

        # arrow2 อาจอยากให้ดูแรงขึ้นนิด (แต่ยังคุมด้วย theme ได้)
        max_thick = 12 if pid == "arrow2" else 11
        life = 0.20 if pid == "arrow2" else 0.18

        ArrowCometTrailNode(
            self,
            render_group,
            life=life,
            sample_interval=0.010,
            max_points=28 if pid == "arrow2" else 26,
            max_thickness=max_thick,
            min_thickness=2,
            glow_passes=2,
            main_rgb=main_rgb,
            core_rgb=core_rgb,
            alpha_main=a_main,
            alpha_core=a_core,
        )

    # ------------------------------------------------------------------
    # Legacy frame load (ถูกแทนที่ด้วย _load_raw_frames + _rotate_frames)
    # เก็บไว้เผื่อ backward compat แต่ในที่นี้เรา override __init__ แล้ว
    # ------------------------------------------------------------------
    def _load_frames(self) -> list[pygame.Surface]:
        return []

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.age += dt
        if self.age >= self.lifetime:
            self.kill()
            return

        # ----- Homing Logic -----
        if self.homing and self.age > self.homing_delay:
            # Find target if none
            if self.target is None or not self.target.alive():
                enemies = getattr(self.owner.game, "enemies", None)
                if enemies:
                    # Find closest
                    closest = None
                    min_dist_sq = 99999999.0
                    my_pos = self.position
                    for e in enemies:
                        if getattr(e, "is_dead", False):
                            continue
                        d_sq = (pygame.Vector2(e.rect.center) - my_pos).length_squared()
                        if d_sq < min_dist_sq:
                            min_dist_sq = d_sq
                            closest = e
                    
                    if min_dist_sq < 600 * 600: # ระยะตรวจจับ
                        self.target = closest

            # Steer towards target
            if self.target and self.target.alive():
                to_target = pygame.Vector2(self.target.rect.center) - self.position
                if to_target.length_squared() > 0:
                    desired = to_target.normalize()
                    # Lerp direction
                    # rate ยิ่งมากยิ่งเลี้ยวเร็ว
                    steer_strength = self.homing_turn_rate * dt * 5.0
                    new_dir = self.direction.lerp(desired, min(1.0, steer_strength))
                    if new_dir.length_squared() > 0:
                        self.direction = new_dir.normalize()
                        
                        # Update visual rotation
                        old_angle = self._angle
                        self._update_angle()
                        if abs(self._angle - old_angle) > 1.0:
                            self._rotate_frames()

        self.position += self.direction * self.speed * dt
        self.rect.center = (int(self.position.x), int(self.position.y))

        super().update(dt)
