# entities/arrow_trail_effect_node.py
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
import weakref
import pygame

__all__ = ["ArrowCometTrailNode"]


@dataclass
class _TrailPoint:
    pos: pygame.Vector2
    age: float


class ArrowCometTrailNode(pygame.sprite.Sprite):
    """
    Trail หางดาวหางสำหรับลูกธนู (comet ribbon)
    - หน้าหนา/ท้ายบาง (taper)
    - มี core highlight ด้านใน
    - ไม่สร้าง spark/dots ที่ปลาย
    - ผูกกับ projectile: projectile หาย -> trail หาย
    """

    def __init__(
        self,
        projectile: pygame.sprite.Sprite,
        *groups: pygame.sprite.AbstractGroup,
        life: float = 0.18,
        sample_interval: float = 0.010,   # เก็บจุด ~100Hz (เนียน)
        max_points: int = 24,
        max_thickness: int = 8,
        min_thickness: int = 2,
        glow_passes: int = 2,
        # โทนสีแบบเกมแอคชัน: warm-gold (เหมือน projectile แรง)
        main_color: tuple[int, int, int] = (255, 210, 120),
        core_color: tuple[int, int, int] = (255, 255, 255),
        alpha_main: int = 160,
        alpha_core: int = 210,
    ) -> None:
        # พยายามให้ trail อยู่ “หลัง” projectile ถ้า group รองรับ layer
        try:
            self._layer = int(getattr(projectile, "_layer", 0)) - 1
        except Exception:
            pass

        super().__init__(*groups)

        self._target_ref = weakref.ref(projectile)
        self.life = max(0.05, float(life))
        self.sample_interval = max(0.001, float(sample_interval))
        self.max_points = max(6, int(max_points))

        self.max_thickness = max(2, int(max_thickness))
        self.min_thickness = max(1, int(min_thickness))
        self.glow_passes = max(0, int(glow_passes))

        self.main_color = main_color
        self.core_color = core_color
        self.alpha_main = max(0, min(255, int(alpha_main)))
        self.alpha_core = max(0, min(255, int(alpha_core)))

        self._timer = 0.0
        self._pts: deque[_TrailPoint] = deque(maxlen=self.max_points)

        # image/rect เริ่มต้น
        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect = self.image.get_rect()

        # เก็บจุดแรกทันที
        self._push_point()

    def _target(self) -> pygame.sprite.Sprite | None:
        return self._target_ref()

    def _get_target_center(self) -> pygame.Vector2 | None:
        t = self._target()
        if t is None:
            return None
        if not hasattr(t, "rect"):
            return None
        return pygame.Vector2(t.rect.center)

    def _push_point(self) -> None:
        c = self._get_target_center()
        if c is None:
            return
        # ถ้าจุดล่าสุดใกล้มาก ไม่ต้องยัดเพิ่ม (กันสั่น)
        if self._pts:
            if (self._pts[0].pos - c).length_squared() < 0.5:
                return
        self._pts.appendleft(_TrailPoint(pos=c, age=0.0))

    @staticmethod
    def _ease_out(t: float) -> float:
        # smooth taper
        t = max(0.0, min(1.0, t))
        return 1.0 - (1.0 - t) * (1.0 - t)

    def update(self, dt: float) -> None:
        dt = float(dt)

        # ถ้า projectile หาย -> trail หาย
        t = self._target()
        if t is None or not t.alive():
            self.kill()
            return

        # age ทุกจุด
        for p in self._pts:
            p.age += dt

        # ลบจุดที่เก่าเกิน life
        while self._pts and self._pts[-1].age >= self.life:
            self._pts.pop()

        # sample เพิ่ม
        self._timer += dt
        while self._timer >= self.sample_interval:
            self._timer -= self.sample_interval
            self._push_point()

        if len(self._pts) < 2:
            return

        self._rebuild_image()

    def _rebuild_image(self) -> None:
        # เตรียม list จุดจาก “ใหม่ -> เก่า”
        pts = [p.pos for p in self._pts]
        ages = [p.age for p in self._pts]

        # bounding box
        min_x = min(p.x for p in pts)
        min_y = min(p.y for p in pts)
        max_x = max(p.x for p in pts)
        max_y = max(p.y for p in pts)

        pad = self.max_thickness * 2 + 6
        w = int(math.ceil(max_x - min_x)) + pad * 2
        h = int(math.ceil(max_y - min_y)) + pad * 2
        if w < 2 or h < 2:
            w = h = 2

        # สร้าง surface ใหม่ (เล็กที่สุดเท่าที่ต้องใช้)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        # แปลงเป็น local coords
        ox = min_x - pad
        oy = min_y - pad
        local = [pygame.Vector2(p.x - ox, p.y - oy) for p in pts]

        # วาดเป็นหลายพาส: glow -> main -> core
        # โทน alpha/taper อิงอายุ (age=0 เด่นสุด)
        n = len(local)

        def draw_pass(color_rgb, alpha_base, thickness_mul: float) -> None:
            for i in range(n - 1):
                a_mid = (ages[i] + ages[i + 1]) * 0.5
                k = max(0.0, min(1.0, 1.0 - (a_mid / self.life)))  # 1=new, 0=old
                k = self._ease_out(k)

                thick = self.min_thickness + (self.max_thickness - self.min_thickness) * k
                thick = max(1, int(round(thick * thickness_mul)))

                a = int(alpha_base * (k ** 1.25))
                if a <= 0 or thick <= 0:
                    continue

                col = (color_rgb[0], color_rgb[1], color_rgb[2], max(0, min(255, a)))
                pygame.draw.line(surf, col, local[i], local[i + 1], thick)

        # glow นุ่ม ๆ (หนากว่า/จางกว่า)
        for g in range(self.glow_passes):
            mul = 1.8 + g * 0.6
            a = int(self.alpha_main * (0.22 / (g + 1)))
            draw_pass(self.main_color, a, mul)

        # main ribbon
        draw_pass(self.main_color, self.alpha_main, 1.0)

        # core highlight (บางกว่า/สว่างกว่า)
        draw_pass(self.core_color, self.alpha_core, 0.45)

        self.image = surf
        self.rect = self.image.get_rect(topleft=(int(ox), int(oy)))
