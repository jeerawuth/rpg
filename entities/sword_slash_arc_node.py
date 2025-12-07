# entities/sword_slash_arc_node.py
from __future__ import annotations
from typing import List, Tuple
import math
import pygame

from .slash_effect_node import SlashEffectNode   # reuse mapping + iso-transform


class SwordSlashArcNode(pygame.sprite.Sprite):
    """
    ดาบวิ่งตามเส้นโค้ง (arc) ในมุมมอง isometric 25°
    - ใช้ร่วมกับ SlashEffectNode ได้: SlashEffectNode ทำแสงโค้ง, ตัวนี้ทำดาบวิ่ง
    """

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

        # 1) เอาช่วงมุมของทิศนั้น ๆ จาก SlashEffectNode
        start_deg, end_deg = SlashEffectNode._get_arc_deg_for_direction(direction)

        # 2) สร้างจุดบนเส้นโค้งใน world space (x, y)
        world_arc_points = SlashEffectNode._build_arc_points(
            radius=radius,
            start_deg=start_deg,
            end_deg=end_deg,
            segments=48,
        )

        # 3) แปลงจุดเป็น isometric → (sx, sy)
        iso_points: List[Tuple[float, float]] = [
            SlashEffectNode._iso_transform(x, y)
            for (x, y) in world_arc_points
        ]

        # 4) แปลงเป็นตำแหน่งบนจอ โดย offset ด้วย center_pos ของ player
        self.path: List[Tuple[float, float]] = [
            (self.center.x + sx, self.center.y + sy)
            for (sx, sy) in iso_points
        ]

        # เริ่มต้นที่จุดแรก
        x0, y0 = self.path[0]
        self.image = self.base_image
        self.rect = self.image.get_rect(center=(x0, y0))

    # ----------------------------------------------------
    # อัปเดตตำแหน่ง / มุมของดาบตามเวลา (dt)
    # ----------------------------------------------------
    def update(self, dt: float) -> None:
        self.elapsed += dt
        if self.elapsed >= self.duration:
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
            angle_deg = 0
        else:
            # pygame: แกน y คว่ำ เลยต้องใส่ - หน้า atan2
            angle_deg = -math.degrees(math.atan2(dy, dx))

        rotated = pygame.transform.rotate(self.base_image, angle_deg)
        self.image = rotated
        self.rect = self.image.get_rect(center=(x, y))
