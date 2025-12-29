# entities/slash_effect_node.py
from __future__ import annotations
from typing import List, Tuple
import math
import pygame
import random

from .animated_node import AnimatedNode


class SlashEffectNode(AnimatedNode):
    """
    เอฟเฟ็กต์ฟันดาบแบบส่วนโค้งในมุมมอง isometric 25°

    - รับ attack_rect (ตำแหน่งที่โจมตีใน world space ปกติ)
    - รับ direction ("up", "down", "left", "right", "up_right", ...)
    - สร้างเส้นโค้งรอบตัว player แล้วแปลงเป็น isometric
    - วาดเป็นแสงฟุ้ง ๆ และค่อย ๆ จางหายไปเอง
    """

    # แมป "ทิศที่ผู้เล่นเห็นบนจอ" -> "ช่วงมุมบนวงกลม world" 45 องศามาตรฐาน 8 ทิศ
    # _ARC_DEGS: dict[str, Tuple[float, float]] = {
    #     # 4 ทิศหลัก
    #     "down":       (22.5,  67.5),   # world  45° -> จอ "ลง"
    #     "left":       (112.5, 157.5),  # world 135° -> จอ "ซ้าย"
    #     "up":         (202.5, 247.5),  # world 225° -> จอ "ขึ้น"
    #     "right":      (292.5, 337.5),  # world 315° -> จอ "ขวา"

    #     # 4 ทิศเฉียง
    #     "down_right": (337.5,  22.5),  # world   0° -> จอ "ล่าง-ขวา"
    #     "down_left":  ( 67.5, 112.5),  # world  90° -> จอ "ล่าง-ซ้าย"
    #     "up_left":    (157.5, 202.5),  # world 180° -> จอ "บน-ซ้าย"
    #     "up_right":   (247.5, 292.5),  # world 270° -> จอ "บน-ขวา"
    # }

    # แมป "ทิศที่ผู้เล่นเห็นบนจอ" -> "ช่วงมุมบนวงกลม world"
    # กว้าง 60° ต่อทิศ (กึ่งกลางเท่าเดิม)
    _ARC_DEGS: dict[str, Tuple[float, float]] = {
        # 4 ทิศหลัก (center: 45, 135, 225, 315)
        "down":       (15.0,  75.0),   # world  45° -> จอ "ลง"
        "left":       (95.0, 175.0),  # world 135° -> จอ "ซ้าย"
        "up":         (195.0, 255.0),  # world 225° -> จอ "ขึ้น"
        "right":      (275.0, 355.0),  # world 315° -> จอ "ขวา"

        # 4 ทิศเฉียง (center: 0, 90, 180, 270) 
        # ทำให้เอฟเฟ็กกว้างขึ้น ใส่ offset 10 ซ้ายลด 10 ขวาเพิ่ม 10
        "down_right": (335.0,  25.0),  # world   0° -> จอ "ล่าง-ขวา"
        "down_left":  ( 65.0, 125.0),  # world  90° -> จอ "ล่าง-ซ้าย"
        "up_left":    (155.0, 205.0),  # world 180° -> จอ "บน-ซ้าย"
        "up_right":   (245.0, 295.0),  # world 270° -> จอ "บน-ขวา"
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
    def _ease_out_cubic(t: float) -> float:
        t = max(0.0, min(1.0, t))
        return 1.0 - (1.0 - t) ** 3

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    @staticmethod
    def _clamp01(x: float) -> float:
        return max(0.0, min(1.0, x))

    @classmethod
    def _build_frames(
        cls,
        arc_points: List[Tuple[int, int]],
        width: int,
        height: int,
        num_frames: int = 10,   # เพิ่มความเนียน
    ) -> List[pygame.Surface]:
        if not arc_points or len(arc_points) < 2:
            return [pygame.Surface((width, height), pygame.SRCALPHA)]

        frames: List[pygame.Surface] = []
        n = len(arc_points)

        # สีหลัก (ปรับได้ตามธาตุ/อาวุธ)
        core_rgb = (210, 255, 255)     # แกนสว่าง
        glow_rgb = (0, 220, 255)       # ขอบเรือง

        for fi in range(num_frames):
            t = fi / max(num_frames - 1, 1)
            fade = 1.0 - cls._ease_out_cubic(t)  # จางแบบนุ่ม ๆ

            surf = pygame.Surface((width, height), pygame.SRCALPHA)

            # 1) วาด glow หนา ๆ ก่อน (หลาย pass ให้ดูนุ่ม)
            #    trick: วาดกว้างแล้วทำ soft bloom ด้วย smoothscale
            glow = pygame.Surface((width, height), pygame.SRCALPHA)

            base_thick = int(cls._lerp(18, 6, t))  # เริ่มหนา → บาง
            glow_alpha = int(110 * fade)

            for k in range(n - 1):
                u = k / max(n - 2, 1)          # 0..1 ไปตามความยาว arc
                # taper: หัวหนากว่า หางบางกว่า
                w = max(2, int(base_thick * (1.0 - 0.65 * u)))
                a = int(glow_alpha * (1.0 - 0.35 * u))  # หัวชัดกว่า

                col = (*glow_rgb, a)
                pygame.draw.line(glow, col, arc_points[k], arc_points[k + 1], w)

            # bloom (ขยายแล้วหด) ให้ขอบฟุ้งแบบ “แพง”
            bloom_scale = 1.08
            bw = max(1, int(width * bloom_scale))
            bh = max(1, int(height * bloom_scale))
            glow_big = pygame.transform.smoothscale(glow, (bw, bh))
            glow_soft = pygame.transform.smoothscale(glow_big, (width, height))
            surf.blit(glow_soft, (0, 0))

            # 2) วาด core (คม) ซ้อนทับ
            core_thick = int(cls._lerp(8, 2, t))
            core_alpha = int(220 * fade)

            for k in range(n - 1):
                u = k / max(n - 2, 1)
                w = max(1, int(core_thick * (1.0 - 0.75 * u)))
                a = int(core_alpha * (1.0 - 0.45 * u))
                col = (*core_rgb, a)
                pygame.draw.line(surf, col, arc_points[k], arc_points[k + 1], w)

            # 3) spark เล็ก ๆ ตามแนว arc (สุ่มแบบ deterministic ต่อเฟรม)
            rng = random.Random(1337 + fi * 97)
            spark_count = 10
            for _ in range(spark_count):
                idx = rng.randint(0, n - 1)
                px, py = arc_points[idx]
                # กระจายเล็กน้อยรอบเส้น
                ox = rng.randint(-6, 6)
                oy = rng.randint(-6, 6)
                r = rng.randint(1, 3)
                a = int(rng.randint(90, 170) * fade)
                pygame.draw.circle(surf, (255, 255, 255, a), (px + ox, py + oy), r)

            frames.append(surf)

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
