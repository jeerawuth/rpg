# entities/sword_slash_arc_node.py
from __future__ import annotations
from typing import List, Tuple
import math
import pygame


class SwordSlashArcNode(pygame.sprite.Sprite):
    """
    ดาบวิ่งตามเส้นโค้ง (arc) ในมุมมอง isometric 25°

    - รับ center_pos = จุดศูนย์กลางตัวละครบนจอ (world space ปกติ)
    - direction = "up", "down", "left", "right", "up_right", ...
    - sword_image = รูปดาบ (surface โปร่งใส)
    - radius = รัศมีของส่วนโค้ง
    - duration = เวลาเคลื่อนที่ครบเส้นโค้ง
    """

    # mapping ทิศที่ผู้เล่นเห็นบนจอ -> ช่วงองศาบนวงกลม world (degree)
    _ARC_DEGS: dict[str, Tuple[float, float]] = {
        # ทิศหลัก 4 ทิศ
        "down":       (22.5,  67.5),   # world  45°  -> จอ "ลง"
        "left":       (112.5, 157.5),  # world 135° -> จอ "ซ้าย"
        "up":         (202.5, 247.5),  # world 225° -> จอ "ขึ้น"
        "right":      (292.5, 337.5),  # world 315° -> จอ "ขวา"

        # ทิศเฉียง 4 ทิศ
        "down_right": (337.5,  22.5),  # world   0° -> จอ "ล่าง-ขวา"
        "down_left":  ( 67.5, 112.5),  # world  90° -> จอ "ล่าง-ซ้าย"
        "up_left":    (157.5, 202.5),  # world 180° -> จอ "บน-ซ้าย"
        "up_right":   (247.5, 292.5),  # world 270° -> จอ "บน-ขวา",
    }

    _ISO_ANGLE_DEG: float = 25.0
    _ISO_ANGLE_RAD: float = math.radians(_ISO_ANGLE_DEG)
    _ISO_K: float = math.sin(_ISO_ANGLE_RAD)

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

        self.game = game
        self.center = pygame.Vector2(center_pos)
        self.base_image = sword_image.convert_alpha()
        self.duration = max(duration, 0.01)
        self.elapsed = 0.0

        dir_name = self._normalize_direction(direction)
        start_deg, end_deg = self._get_arc_deg_for_direction(dir_name)

        # 1) สร้างจุดบนเส้นโค้งใน world space (x, y)
        world_arc_points = self._build_arc_points(
            radius=radius,
            start_deg=start_deg,
            end_deg=end_deg,
            segments=48,
        )

        # 2) แปลงเป็นจุดบนระนาบ isometric 25° รอบ origin (0,0)
        iso_points: List[Tuple[float, float]] = [
            self._iso_transform(x, y) for (x, y) in world_arc_points
        ]

        # 3) แปลงเป็นตำแหน่งจริงบนจอ โดยอิงจาก center_pos ของ player
        self.path: List[Tuple[float, float]] = [
            (self.center.x + sx, self.center.y + sy) for (sx, sy) in iso_points
        ]

        # เริ่มต้นที่จุดแรก
        x0, y0 = self.path[0]
        self.image = self.base_image
        self.rect = self.image.get_rect(center=(x0, y0))

    # ----------------------------------------------------
    # Geometry helpers
    # ----------------------------------------------------
    @classmethod
    def _normalize_direction(cls, direction: str) -> str:
        d = (direction or "").lower()
        d = d.replace(" ", "_").replace("-", "_")
        return d

    @classmethod
    def _get_arc_deg_for_direction(cls, direction: str) -> Tuple[float, float]:
        d = cls._normalize_direction(direction)

        if d in cls._ARC_DEGS:
            return cls._ARC_DEGS[d]

        # รองรับรูปแบบสะกดอื่น ๆ
        if "up" in d and "right" in d:
            return cls._ARC_DEGS["up_right"]
        if "up" in d and "left" in d:
            return cls._ARC_DEGS["up_left"]
        if "down" in d and "right" in d:
            return cls._ARC_DEGS["down_right"]
        if "down" in d and "left" in d:
            return cls._ARC_DEGS["down_left"]
        if "up" in d:
            return cls._ARC_DEGS["up"]
        if "down" in d:
            return cls._ARC_DEGS["down"]
        if "left" in d:
            return cls._ARC_DEGS["left"]
        if "right" in d:
            return cls._ARC_DEGS["right"]

        # default: ฟันลงหน้าจอ
        return cls._ARC_DEGS["down"]

    @classmethod
    def _build_arc_points(
        cls,
        radius: float,
        start_deg: float,
        end_deg: float,
        segments: int = 48,
    ) -> List[Tuple[float, float]]:
        pts: List[Tuple[float, float]] = []

        if end_deg < start_deg:
            end_deg += 360.0

        for i in range(segments + 1):
            a_deg = start_deg + (end_deg - start_deg) * i / segments
            a_rad = math.radians(a_deg)
            x = radius * math.cos(a_rad)
            y = radius * math.sin(a_rad)
            pts.append((x, y))

        return pts

    @classmethod
    def _iso_transform(cls, x: float, y: float) -> Tuple[float, float]:
        # world (x, y) -> isometric 25°
        sx = x - y
        sy = (x + y) * cls._ISO_K
        return sx, sy

    # ----------------------------------------------------
    # Update: ขยับดาบไปตาม path + หมุนตามทิศทาง
    # ----------------------------------------------------
    def update(self, dt: float) -> None:
        self.elapsed += dt
        if self.elapsed >= self.duration or len(self.path) <= 1:
            self.kill()
            return

        # t วิ่งจาก 0 → 1 ตามเวลา
        t = self.elapsed / self.duration

        max_index = len(self.path) - 1
        pos_f = t * max_index          # ค่าลอยตัว
        i = int(pos_f)                 # index ซ้าย
        j = min(i + 1, max_index)      # index ขวา
        local_t = pos_f - i            # สัดส่วนระหว่างสองจุด

        x1, y1 = self.path[i]
        x2, y2 = self.path[j]

        # interpolate ตำแหน่ง
        x = x1 + (x2 - x1) * local_t
        y = y1 + (y2 - y1) * local_t

        # ทิศทางของเส้นโค้ง (tangent) → มุมของดาบ
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            angle_deg = 0.0
        else:
            # pygame: แกน y คว่ำ เลยต้องใส่ - หน้า atan2
            angle_deg = -math.degrees(math.atan2(dy, dx))

        rotated = pygame.transform.rotate(self.base_image, angle_deg)
        self.image = rotated
        self.rect = self.image.get_rect(center=(x, y))
