# entities/sword_slash_arc_node.py
from __future__ import annotations
from typing import List, Tuple
import math
import pygame


class SwordAfterImageNode(pygame.sprite.Sprite):
    """เงาดาบ/afterimage ที่ค่อย ๆ จางหาย เพื่อทำให้ trail ดูโปรขึ้น"""

    def __init__(
        self,
        image: pygame.Surface,
        center: tuple[float, float],
        *groups: pygame.sprite.AbstractGroup,
        life: float = 0.10,
        start_alpha: int = 140,
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


class SwordSlashArcNode(pygame.sprite.Sprite):
    """
    ดาบวิ่งตามเส้นโค้ง (arc) ในมุมมอง isometric 25°

    - center_pos: จุดศูนย์กลางตัวละคร
    - direction: "up", "down", "left", "right", "up_right", ...
    - sword_image: รูปดาบ (surface โปร่งใส)
    - radius: รัศมีของส่วนโค้ง
    - duration: เวลาเคลื่อนที่ครบเส้นโค้ง
    """

    _ARC_DEGS: dict[str, Tuple[float, float]] = {
        # ทิศหลัก 4 ทิศ
        "down":       (22.5,  67.5),
        "left":       (112.5, 157.5),
        "up":         (202.5, 247.5),
        "right":      (292.5, 337.5),

        # ทิศเฉียง 4 ทิศ
        "down_right": (337.5,  22.5),
        "down_left":  ( 67.5, 112.5),
        "up_left":    (157.5, 202.5),
        "up_right":   (247.5, 292.5),
    }

    def __init__(
        self,
        game,
        center_pos: tuple[int, int],
        direction: str,
        sword_image: pygame.Surface,
        radius: float = 140.0,
        duration: float = 0.25,
        *groups: pygame.sprite.AbstractGroup,
    ) -> None:
        super().__init__(*groups)

        # เก็บ groups ไว้ปล่อย afterimage ในเลเยอร์เดียวกัน
        self._groups_for_trail = groups
        self._trail_timer = 0.0
        self._trail_interval = 0.02

        self.game = game
        self.center = pygame.Vector2(center_pos)
        self.base_image = sword_image.convert_alpha()
        self.duration = max(duration, 0.01)
        self.radius = float(radius)

        self.elapsed = 0.0

        direction = self._normalize_direction(direction)

        # 1) สร้าง arc points ใน world offsets (dx,dy)
        arc_offsets = self._generate_arc_offsets(direction, self.radius)

        # 2) แปลงเป็น isometric offsets
        iso_points = [self._to_isometric_offset(dx, dy) for (dx, dy) in arc_offsets]

        # 3) แปลงเป็นตำแหน่งจริงบนจอ
        self.path: List[Tuple[float, float]] = [
            (self.center.x + sx, self.center.y + sy) for (sx, sy) in iso_points
        ]

        x0, y0 = self.path[0]
        self.image = self.base_image
        self.rect = self.image.get_rect(center=(x0, y0))

    # ----------------------------------------------------
    # Geometry helpers
    # ----------------------------------------------------
    @classmethod
    def _normalize_direction(cls, direction: str) -> str:
        d = direction.strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "upright": "up_right",
            "upleft": "up_left",
            "downright": "down_right",
            "downleft": "down_left",
        }
        return aliases.get(d, d)

    @classmethod
    def _generate_arc_offsets(
        cls,
        direction: str,
        radius: float,
        steps: int = 18,
    ) -> List[Tuple[float, float]]:
        """สร้างจุด arc ใน world offset (dx,dy) รอบ origin"""
        start_deg, end_deg = cls._ARC_DEGS.get(direction, (22.5, 67.5))
        if start_deg > end_deg:
            end_deg += 360.0

        points: List[Tuple[float, float]] = []
        for i in range(steps + 1):
            t = i / steps
            deg = start_deg + (end_deg - start_deg) * t
            rad = math.radians(deg)

            dx = math.cos(rad) * radius
            dy = math.sin(rad) * radius
            points.append((dx, dy))

        return points

    @staticmethod
    def _to_isometric_offset(dx: float, dy: float) -> Tuple[float, float]:
        iso_angle = math.radians(25.0)
        sx = dx - dy
        sy = (dx + dy) * math.sin(iso_angle)
        return (sx, sy)

    # ----------------------------------------------------
    # Update
    # ----------------------------------------------------
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

        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            angle_deg = 0.0
        else:
            angle_deg = -math.degrees(math.atan2(dy, dx))

        rotated = pygame.transform.rotate(self.base_image, angle_deg)

        # --- ปล่อย afterimage ---
        self._trail_timer += dt
        if self._trail_timer >= self._trail_interval:
            self._trail_timer = 0.0
            SwordAfterImageNode(
                rotated,
                (x, y),
                *self._groups_for_trail,
                life=0.08,
                start_alpha=120,
            )

        self.image = rotated
        self.rect = self.image.get_rect(center=(x, y))
