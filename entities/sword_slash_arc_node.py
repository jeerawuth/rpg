# entities/sword_slash_arc_node.py
from __future__ import annotations

from collections import deque
from typing import List, Tuple
import math
import pygame

__all__ = ["SwordAfterImageNode", "SlashRingBeamNode", "SlashArcSegmentNode", "SwordSlashArcNode"]


class SwordAfterImageNode(pygame.sprite.Sprite):
    """เงาดาบ/afterimage ที่ค่อย ๆ จางหาย"""

    def __init__(
        self,
        image: pygame.Surface,
        center: tuple[float, float],
        *groups: pygame.sprite.AbstractGroup,
        life: float = 0.10,
        start_alpha: int = 80,
    ) -> None:
        super().__init__(*groups)
        self.image = image.copy()
        self.rect = self.image.get_rect(center=(center[0], center[1]))
        self.life = max(0.01, float(life))
        self.t = 0.0
        self.start_alpha = max(0, min(255, int(start_alpha)))

    def update(self, dt: float) -> None:
        self.t += dt
        if self.t >= self.life:
            self.kill()
            return
        a = int(self.start_alpha * (1.0 - self.t / self.life))
        self.image.set_alpha(max(0, min(255, a)))


class SlashRingBeamNode(pygame.sprite.Sprite):
    """วงแสง (ring beam) ที่ขยายตัวและจางหาย — ใช้เป็นไฮไลต์ที่ “ปลายดาบ”"""

    def __init__(
        self,
        center: tuple[float, float],
        *groups: pygame.sprite.AbstractGroup,
        life: float = 0.10,
        radius_start: float = 6.0,
        radius_end: float = 22.0,
        thickness: int = 2,
        start_alpha: int = 130,
        glow: bool = True,
    ) -> None:
        super().__init__(*groups)
        self.center = pygame.Vector2(center)
        self.life = max(0.01, float(life))
        self.elapsed = 0.0
        self.r0 = float(radius_start)
        self.r1 = float(radius_end)
        self.thickness = max(1, int(thickness))
        self.a0 = max(0, min(255, int(start_alpha)))
        self.glow = bool(glow)

        pad = 8
        self._max_r = int(math.ceil(max(self.r0, self.r1))) + pad
        size = self._max_r * 2
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(self.center.x, self.center.y))
        self._redraw(0.0)

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    def _redraw(self, t: float) -> None:
        self.image.fill((0, 0, 0, 0))

        r = self._lerp(self.r0, self.r1, t)
        a = int(self._lerp(self.a0, 0.0, t))
        a = max(0, min(255, a))

        cx = self._max_r
        cy = self._max_r

        glow_col = (0, 220, 255, a)
        core_col = (235, 255, 255, min(255, a + 30))

        if self.glow:
            pygame.draw.circle(self.image, (0, 220, 255, max(0, a // 3)), (cx, cy), int(r) + 6, self.thickness + 6)
            pygame.draw.circle(self.image, (0, 220, 255, max(0, a // 2)), (cx, cy), int(r) + 3, self.thickness + 3)

        pygame.draw.circle(self.image, glow_col, (cx, cy), int(r), self.thickness)
        pygame.draw.circle(self.image, core_col, (cx, cy), max(0, int(r) - 1), 1)

    def update(self, dt: float) -> None:
        self.elapsed += dt
        t = self.elapsed / self.life
        if t >= 1.0:
            self.kill()
            return
        t = max(0.0, min(1.0, t))
        self._redraw(t)
        self.rect = self.image.get_rect(center=(self.center.x, self.center.y))


class SlashArcSegmentNode(pygame.sprite.Sprite):
    """เส้นแสงแบบ “segment” ระหว่าง 2 จุด (p0->p1) ที่ค่อย ๆ จาง
    ใช้ทำ trail ต่อเนื่องตามเส้นโค้ง (เบาเครื่อง และเห็นการ “ไล่เส้น” ชัด)
    """

    def __init__(
        self,
        p0: tuple[float, float],
        p1: tuple[float, float],
        *groups: pygame.sprite.AbstractGroup,
        life: float = 0.14,
        start_alpha: int = 150,
        thickness: int = 4,
        glow: bool = True,
        pad: int = 14,
    ) -> None:
        super().__init__(*groups)
        self.p0 = pygame.Vector2(p0)
        self.p1 = pygame.Vector2(p1)
        self.life = max(0.01, float(life))
        self.t = 0.0
        self.a0 = max(0, min(255, int(start_alpha)))
        self.thickness = max(1, int(thickness))
        self.glow = bool(glow)

        minx = min(self.p0.x, self.p1.x) - pad
        miny = min(self.p0.y, self.p1.y) - pad
        maxx = max(self.p0.x, self.p1.x) + pad
        maxy = max(self.p0.y, self.p1.y) + pad

        w = max(1, int(math.ceil(maxx - minx)))
        h = max(1, int(math.ceil(maxy - miny)))

        self._origin = pygame.Vector2(minx, miny)
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(int(minx), int(miny)))

        self._draw(alpha=self.a0)

    def _draw(self, alpha: int) -> None:
        self.image.fill((0, 0, 0, 0))
        a = max(0, min(255, int(alpha)))

        # local coords
        p0 = self.p0 - self._origin
        p1 = self.p1 - self._origin

        glow_col = (0, 220, 255, a)
        core_col = (235, 255, 255, min(255, a + 30))

        if self.glow:
            pygame.draw.line(self.image, (0, 220, 255, max(0, a // 3)), p0, p1, self.thickness + 6)
            pygame.draw.line(self.image, (0, 220, 255, max(0, a // 2)), p0, p1, self.thickness + 3)

        pygame.draw.line(self.image, glow_col, p0, p1, self.thickness)
        pygame.draw.line(self.image, core_col, p0, p1, max(1, self.thickness // 2))

    def update(self, dt: float) -> None:
        self.t += dt
        if self.t >= self.life:
            self.kill()
            return
        alpha = int(self.a0 * (1.0 - self.t / self.life))
        self._draw(alpha)


class SwordSlashArcNode(pygame.sprite.Sprite):
    """ดาบวิ่งตาม “วงกลม 360°” ในมุมมอง isometric 25°
    - แสดงการเคลื่อนที่ชัด: เส้นแสงจะ “ไล่” ตามทางเดิน (segment trail)
    - รองรับ 8 ทิศ: เริ่มที่มุม 0° ของทิศนั้น แล้ววิ่งจนครบ 360°
    """

    _DIR_VEC: dict[str, Tuple[float, float]] = {
        "up": (0.0, -1.0),
        "down": (0.0, 1.0),
        "left": (-1.0, 0.0),
        "right": (1.0, 0.0),
        "up_left": (-1.0, -1.0),
        "up_right": (1.0, -1.0),
        "down_left": (-1.0, 1.0),
        "down_right": (1.0, 1.0),
    }

    # ========== Tunables ==========
    _ISO_DEG: float = 25.0

    # ✅ เปลี่ยนเป็นวงกลมเต็ม
    _SWEEP_DEG: float = 360.0
    _STEPS: int = 84  # ยิ่งมากยิ่งเนียน (84 ~ 4.3° ต่อสเต็ป)

    # เงาดาบ (ให้จาง)
    _TRAIL_INTERVAL: float = 0.016
    _AFTERIMAGE_LIFE: float = 0.070
    _AFTERIMAGE_ALPHA: int = 45

    # Trail เส้นแสงแบบ segment (ต่อเนื่อง)
    _SEG_LIFE: float = 0.18
    _SEG_ALPHA: int = 160
    _SEG_THICKNESS: int = 5

    # Ring highlight (ที่ปลายดาบ)
    _RING_ENABLED: bool = True
    _RING_EVERY_N_SEGMENTS: int = 2  # ยิ่งมากยิ่งน้อยวง
    _RING_LIFE: float = 0.10

    def __init__(
        self,
        game,
        center_pos: tuple[int, int],
        direction: str,
        sword_image: pygame.Surface,
        radius: float = 140.0,
        duration: float = 0.35,  # วงกลมเต็มควรช้ากว่าเดิมเล็กน้อย (แต่ caller ยังส่งได้)
        *groups: pygame.sprite.AbstractGroup,
    ) -> None:
        super().__init__(*groups)

        self.game = game
        self.center = pygame.Vector2(center_pos)
        self.direction = self._normalize_direction(direction)

        self.base_image = sword_image.convert_alpha()
        self.radius = float(radius)
        self.duration = max(0.01, float(duration))
        self.elapsed = 0.0

        self._groups_for_trail: Tuple[pygame.sprite.AbstractGroup, ...] = groups

        self._trail_timer = 0.0
        self._trail_interval = self._TRAIL_INTERVAL

        self._prev_tip: Tuple[float, float] | None = None
        self._seg_count = 0

        dv = self._direction_to_vector(self.direction)
        base_angle = math.atan2(dv.y, dv.x)

        # NOTE: โปรเจกต์นี้เคยกลับด้าน; ใช้ flipped default ให้เข้ากับการฟันในเกมคุณ
        clockwise_on_screen = (not self._preferred_clockwise(dv))

        # ✅ สร้างวงกลมเต็ม: start = base_angle (เหมือน “0° ของทิศนั้น”), end = start +/- 360°
        arc_offsets = self._generate_circle_offsets(
            start_angle=base_angle,
            radius=self.radius,
            steps=self._STEPS,
            clockwise=clockwise_on_screen,
        )

        iso_points = [self._to_isometric_offset(dx, dy, iso_deg=self._ISO_DEG) for (dx, dy) in arc_offsets]
        self.path: List[Tuple[float, float]] = [(self.center.x + sx, self.center.y + sy) for (sx, sy) in iso_points]

        x0, y0 = self.path[0]
        self.image = self.base_image
        self.rect = self.image.get_rect(center=(x0, y0))

    # --------------------
    # Direction helpers
    # --------------------
    @classmethod
    def _normalize_direction(cls, direction: str) -> str:
        d = (direction or "").strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {"upright": "up_right", "upleft": "up_left", "downright": "down_right", "downleft": "down_left"}
        return aliases.get(d, d)

    @classmethod
    def _direction_to_vector(cls, direction: str) -> pygame.Vector2:
        d = cls._normalize_direction(direction)
        vx, vy = cls._DIR_VEC.get(d, (0.0, 1.0))
        v = pygame.Vector2(vx, vy)
        return v.normalize() if v.length_squared() else pygame.Vector2(0, 1)

    @staticmethod
    def _preferred_clockwise(dir_vec: pygame.Vector2) -> bool:
        x, y = dir_vec.x, dir_vec.y
        if abs(x) >= abs(y):
            return x >= 0.0
        return y >= 0.0

    # --------------------
    # Geometry
    # --------------------
    @staticmethod
    def _generate_circle_offsets(
        start_angle: float,
        radius: float,
        steps: int,
        clockwise: bool = True,
    ) -> List[Tuple[float, float]]:
        """สร้างจุดวงกลมเต็ม 360° ใน world offset
        - start_angle คือ “0° ของทิศนั้น”
        - clockwise=True => ไล่มุมเพิ่ม (บน pygame coords จะเห็นเป็นหมุนตามเข็ม)
        """
        steps = max(8, int(steps))
        sign = 1.0 if clockwise else -1.0
        pts: List[Tuple[float, float]] = []
        for i in range(steps + 1):
            t = i / steps
            a = start_angle + sign * (2.0 * math.pi) * t
            pts.append((math.cos(a) * radius, math.sin(a) * radius))
        return pts

    @staticmethod
    def _to_isometric_offset(dx: float, dy: float, iso_deg: float = 25.0) -> Tuple[float, float]:
        iso_angle = math.radians(float(iso_deg))
        sx = dx - dy
        sy = (dx + dy) * math.sin(iso_angle)
        return (sx, sy)

    # --------------------
    # Update
    # --------------------
    def update(self, dt: float) -> None:
        self.elapsed += dt
        if self.elapsed >= self.duration or len(self.path) <= 1:
            self.kill()
            return

        t = self.elapsed / self.duration
        max_index = len(self.path) - 1

        pos_f = t * max_index
        i = int(pos_f)
        j = min(i + 1, max_index)
        local_t = pos_f - i

        x1, y1 = self.path[i]
        x2, y2 = self.path[j]
        x = x1 + (x2 - x1) * local_t
        y = y1 + (y2 - y1) * local_t

        # tangent rotation
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            angle_deg = 0.0
        else:
            angle_deg = -math.degrees(math.atan2(dy, dx))

        rotated = pygame.transform.rotate(self.base_image, angle_deg)

        # trail timer
        self._trail_timer += dt
        if self._trail_timer >= self._trail_interval:
            self._trail_timer = 0.0

            # afterimage (จาง)
            SwordAfterImageNode(
                rotated,
                (x, y),
                *self._groups_for_trail,
                life=self._AFTERIMAGE_LIFE,
                start_alpha=self._AFTERIMAGE_ALPHA,
            )

            # tip position (ahead along motion)
            tip_x, tip_y = x, y
            mag = math.hypot(dx, dy)
            if mag > 1e-3:
                ux = dx / mag
                uy = dy / mag
                tip_offset = 20.0
                tip_x = x + ux * tip_offset
                tip_y = y + uy * tip_offset

            # ✅ เส้นทาง “ไล่” เป็นเส้นโค้ง: spawn segment จาก prev_tip -> tip
            if self._prev_tip is not None:
                SlashArcSegmentNode(
                    self._prev_tip,
                    (tip_x, tip_y),
                    *self._groups_for_trail,
                    life=self._SEG_LIFE,
                    start_alpha=self._SEG_ALPHA,
                    thickness=self._SEG_THICKNESS,
                    glow=True,
                )
                self._seg_count += 1

                # ring highlight (เป็นจุด ๆ ไม่รก)
                if self._RING_ENABLED and (self._seg_count % self._RING_EVERY_N_SEGMENTS == 0):
                    SlashRingBeamNode(
                        (tip_x, tip_y),
                        *self._groups_for_trail,
                        life=self._RING_LIFE,
                        radius_start=6.0,
                        radius_end=22.0,
                        thickness=2,
                        start_alpha=120,
                        glow=True,
                    )

            self._prev_tip = (tip_x, tip_y)

        self.image = rotated
        self.rect = self.image.get_rect(center=(x, y))
