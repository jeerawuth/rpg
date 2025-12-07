# entities/slash_effect_node.py
from __future__ import annotations
from typing import List, Tuple
import math
import pygame

from .animated_node import AnimatedNode


class SlashEffectNode(AnimatedNode):
    """
    เอฟเฟ็กต์ฟันดาบแบบส่วนโค้งในมุมมอง isometric 25°

    - รับ attack_rect (ตำแหน่งที่โจมตีใน world space ปกติ)
    - รับ direction ("up", "down", "left", "right", "up_right", ...)
    - สร้างเส้นโค้งรอบตัว player แล้วแปลงเป็น isometric
    - วาดเป็นแสงฟุ้ง ๆ และค่อย ๆ จางหายไปเอง
    """

    # แมป "ทิศที่ผู้เล่นเห็นบนจอ" -> "ช่วงมุมบนวงกลม world"
    _ARC_DEGS: dict[str, Tuple[float, float]] = {
        # 4 ทิศหลัก
        "down":       (22.5,  67.5),   # world  45° -> จอ "ลง"
        "left":       (112.5, 157.5),  # world 135° -> จอ "ซ้าย"
        "up":         (202.5, 247.5),  # world 225° -> จอ "ขึ้น"
        "right":      (292.5, 337.5),  # world 315° -> จอ "ขวา"

        # 4 ทิศเฉียง
        "down_right": (337.5,  22.5),  # world   0° -> จอ "ล่าง-ขวา"
        "down_left":  ( 67.5, 112.5),  # world  90° -> จอ "ล่าง-ซ้าย"
        "up_left":    (157.5, 202.5),  # world 180° -> จอ "บน-ซ้าย"
        "up_right":   (247.5, 292.5),  # world 270° -> จอ "บน-ขวา"
    }

    _ISO_ANGLE_DEG: float = 25.0
    _ISO_ANGLE_RAD: float = math.radians(_ISO_ANGLE_DEG)
    _ISO_K: float = math.sin(_ISO_ANGLE_RAD)

    def __init__(
        self,
        game,
        attack_rect: pygame.Rect,
        direction: str,
        *groups: pygame.sprite.AbstractGroup,
    ) -> None:
        self.game = game
        self.attack_rect = attack_rect
        self.direction = self._normalize_direction(direction)

        # ----------------------------
        # 1) หาจุดศูนย์กลาง (player)
        # ----------------------------
        player = getattr(self.game, "player", None)
        if player is not None:
            player_center = pygame.Vector2(player.rect.center)
        else:
            player_center = pygame.Vector2(attack_rect.center)

        # ระยะจาก player → center ของ attack_rect สำหรับประมาณรัศมี
        delta = pygame.Vector2(attack_rect.center) - player_center
        radius = delta.length()
        if radius <= 1:
            radius = 64.0
        radius = max(48.0, min(radius, 220.0))

        # ----------------------------
        # 2) สร้างจุดของ "ส่วนโค้ง" ใน world space
        # ----------------------------
        start_deg, end_deg = self._get_arc_deg_for_direction(self.direction)
        world_arc_points = self._build_arc_points(radius, start_deg, end_deg, segments=48)

        # ----------------------------
        # 3) แปลงจุดเป็น isometric 25°
        #    รอบ origin (0,0)
        # ----------------------------
        iso_arc_points = [self._iso_transform(x, y) for (x, y) in world_arc_points]

        # ----------------------------
        # 4) เลื่อนจุดให้มาอยู่บน surface (origin = center)
        # ----------------------------
        surf_points, surf_size = self._to_surface_space(iso_arc_points, margin=16)
        width, height = surf_size

        # ----------------------------
        # 5) สร้างชุดเฟรมสำหรับเอฟเฟ็กต์
        # ----------------------------
        frames: List[pygame.Surface] = self._build_frames(surf_points, width, height)

        frame_duration = 0.04
        self.life_time = frame_duration * len(frames)

        # ✅ เรียก AnimatedNode ด้วยลำดับที่ถูกต้อง
        #    (frames, frame_duration, loop, *groups)
        super().__init__(frames, frame_duration, False, *groups)

        # วาง center ของ effect ทับ player_center (world space)
        self.rect = self.image.get_rect(center=player_center)

    # ============================================================
    # Helper: ทิศ & มุม
    # ============================================================
    @classmethod
    def _normalize_direction(cls, direction: str) -> str:
        direction = (direction or "").lower()
        direction = direction.replace(" ", "_").replace("-", "_")
        return direction

    @classmethod
    def _get_arc_deg_for_direction(cls, direction: str) -> Tuple[float, float]:
        direction = cls._normalize_direction(direction)

        if direction in cls._ARC_DEGS:
            return cls._ARC_DEGS[direction]

        # รองรับชื่อสะกดแปลก ๆ
        if "up" in direction and "right" in direction:
            return cls._ARC_DEGS["up_right"]
        if "up" in direction and "left" in direction:
            return cls._ARC_DEGS["up_left"]
        if "down" in direction and "right" in direction:
            return cls._ARC_DEGS["down_right"]
        if "down" in direction and "left" in direction:
            return cls._ARC_DEGS["down_left"]
        if "up" in direction:
            return cls._ARC_DEGS["up"]
        if "down" in direction:
            return cls._ARC_DEGS["down"]
        if "left" in direction:
            return cls._ARC_DEGS["left"]
        if "right" in direction:
            return cls._ARC_DEGS["right"]

        # default: ฟันลงหน้าจอ
        return cls._ARC_DEGS["down"]

    # ============================================================
    # Helper: สร้างเส้นโค้ง + isometric
    # ============================================================
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
        sx = x - y
        sy = (x + y) * cls._ISO_K
        return sx, sy

    @staticmethod
    def _to_surface_space(
        iso_points: List[Tuple[float, float]],
        margin: int = 16,
    ) -> Tuple[List[Tuple[int, int]], Tuple[int, int]]:
        if not iso_points:
            surf = pygame.Surface((1, 1), pygame.SRCALPHA)
            return [(0, 0)], (1, 1)

        xs = [p[0] for p in iso_points]
        ys = [p[1] for p in iso_points]

        half_w = max(abs(min(xs)), abs(max(xs))) + margin
        half_h = max(abs(min(ys)), abs(max(ys))) + margin

        width = int(half_w * 2)
        height = int(half_h * 2)

        cx = width // 2
        cy = height // 2

        surf_points: List[Tuple[int, int]] = []
        for x, y in iso_points:
            sx = int(round(x + cx))
            sy = int(round(y + cy))
            surf_points.append((sx, sy))

        return surf_points, (width, height)

    @staticmethod
    def _build_frames(
        arc_points: List[Tuple[int, int]],
        width: int,
        height: int,
        num_frames: int = 6,
    ) -> List[pygame.Surface]:
        if not arc_points:
            surf = pygame.Surface((width, height), pygame.SRCALPHA)
            return [surf]

        frames: List[pygame.Surface] = []

        for i in range(num_frames):
            t = i / max(num_frames - 1, 1)

            base_width = max(2, int(10 * (1.0 - t)))
            inner_width = max(1, base_width // 2)

            glow_surface = pygame.Surface((width, height), pygame.SRCALPHA)

            outer_color = (0, 255, 255, int(80 * (1.0 - t)))
            pygame.draw.lines(glow_surface, outer_color, False, arc_points, base_width)

            inner_color = (180, 255, 255, int(200 * (1.0 - t)))
            pygame.draw.lines(glow_surface, inner_color, False, arc_points, inner_width)

            frames.append(glow_surface)

        return frames

    # ============================================================
    # Update
    # ============================================================
    def update(self, dt: float) -> None:
        self.life_time -= dt
        if self.life_time <= 0:
            self.kill()
            return

        super().update(dt)
