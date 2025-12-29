# entities/slash_effect_node.py
from __future__ import annotations
from typing import List, Tuple, Dict, Any
import math
import pygame
import random

from .animated_node import AnimatedNode


class SlashEffectNode(AnimatedNode):
    """
    Slash effect (PRO style, 8-direction) — แก้เฉพาะไฟล์นี้เท่านั้น

    ✅ Signature เดิมยังใช้ได้:
        SlashEffectNode(game, attack_rect, direction, *groups)

    ✅ เพิ่ม "รูปแบบ" โดยส่งค่าแบบ keyword-only:
        SlashEffectNode(game, attack_rect, direction, *groups, style="diablo")
        SlashEffectNode(game, attack_rect, direction, *groups, style="soulslike")
        (ค่าเริ่มต้น = "normal" = แบบปัจจุบัน)

    แนวทางที่เกมระดับโลกนิยม:
    - สร้าง arc จาก "direction vector" (ไม่ฮาร์ดโค้ดตารางมุม) เพื่อให้ซ้าย/ขวาธรรมชาติ
    - ทำ 2 hit ซ้อนกันให้เป็น X:
        hit1 clockwise + center_offset (+)
        hit2 counterclockwise + center_offset (-) + overlap
    - world เป็น isometric 25° ได้ แต่ "เอฟเฟ็กต์" สามารถ stylize ด้วย iso angle / sweep / timing ได้
    """

    # =========================
    # Presets (ปรับได้)
    # =========================
    # ค่าเริ่มต้น (normal) = แบบปัจจุบันของคุณ
    _DEFAULTS: Dict[str, Any] = {
        "sweep_deg": 92.0,
        "cross_offset_deg": 12.0,
        "iso_sequence_deg": (20.0, 25.0),
        "overlap_start_frame": 4,
        "num_frames_per_hit": 10,
        "frame_duration": 0.04,
        "hit2_thickness_boost": 3,
    }

    # โหมดเร็ว (Diablo-like): เร็ว/ลื่น/แฟลชมากขึ้น
    # - เฟรมต่อ hit น้อยลง + frame_duration ต่ำลง
    # - sweep กว้างขึ้นเล็กน้อย ให้รู้สึก "กวาดเร็ว"
    # - overlap เร็วขึ้น ให้ X เกิดเร็ว
    _DIABLO: Dict[str, Any] = {
        "sweep_deg": 100.0,
        "cross_offset_deg": 14.0,
        "iso_sequence_deg": (22.0, 26.0),
        "overlap_start_frame": 3,
        "num_frames_per_hit": 8,
        "frame_duration": 0.033,
        "hit2_thickness_boost": 2,
    }

    # โหมดหนัก (Soulslike): หนัก/หน่วง/มีน้ำหนัก
    # - เฟรมต่อ hit มากขึ้น + frame_duration สูงขึ้นเล็กน้อย
    # - sweep แคบลง ให้รู้สึก "คมและตั้งใจ"
    # - hit2 หนาขึ้นให้รู้สึกกระแทก
    _SOULSLIKE: Dict[str, Any] = {
        "sweep_deg": 86.0,
        "cross_offset_deg": 10.0,
        "iso_sequence_deg": (20.0, 25.0),
        "overlap_start_frame": 5,
        "num_frames_per_hit": 12,
        "frame_duration": 0.045,
        "hit2_thickness_boost": 5,
    }

    _STYLE_PRESETS: Dict[str, Dict[str, Any]] = {
        "normal": _DEFAULTS,
        "default": _DEFAULTS,
        "fast": _DIABLO,
        "diablo": _DIABLO,
        "heavy": _SOULSLIKE,
        "soulslike": _SOULSLIKE,
        "souls": _SOULSLIKE,
    }

    # =========================
    # Direction mapping (8 ทิศ)
    # =========================
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

    def __init__(
        self,
        game,
        attack_rect: pygame.Rect,
        direction: str,
        *groups: pygame.sprite.AbstractGroup,
        style: str = "normal",
        # เผื่ออยาก override ทีละค่า (ไม่จำเป็นต้องใช้)
        sweep_deg: float | None = None,
        cross_offset_deg: float | None = None,
        iso_sequence_deg: Tuple[float, float] | None = None,
        overlap_start_frame: int | None = None,
        num_frames_per_hit: int | None = None,
        frame_duration: float | None = None,
        hit2_thickness_boost: int | None = None,
    ) -> None:
        self.game = game
        self.attack_rect = attack_rect
        self.direction = self._normalize_direction(direction)

        # ----------------------------
        # 0) เลือก preset ตาม style
        # ----------------------------
        style_key = (style or "normal").strip().lower()
        preset = dict(self._STYLE_PRESETS.get(style_key, self._DEFAULTS))

        # apply overrides (ถ้า user ส่งมา)
        if sweep_deg is not None:
            preset["sweep_deg"] = float(sweep_deg)
        if cross_offset_deg is not None:
            preset["cross_offset_deg"] = float(cross_offset_deg)
        if iso_sequence_deg is not None:
            preset["iso_sequence_deg"] = tuple(map(float, iso_sequence_deg))  # type: ignore
        if overlap_start_frame is not None:
            preset["overlap_start_frame"] = int(overlap_start_frame)
        if num_frames_per_hit is not None:
            preset["num_frames_per_hit"] = int(num_frames_per_hit)
        if frame_duration is not None:
            preset["frame_duration"] = float(frame_duration)
        if hit2_thickness_boost is not None:
            preset["hit2_thickness_boost"] = int(hit2_thickness_boost)

        # clamp/guard
        sweep_deg_v = float(preset["sweep_deg"])
        sweep_deg_v = max(40.0, min(140.0, sweep_deg_v))

        cross_deg_v = float(preset["cross_offset_deg"])
        cross_deg_v = max(0.0, min(35.0, cross_deg_v))

        iso_seq = preset["iso_sequence_deg"]
        iso1 = float(iso_seq[0])
        iso2 = float(iso_seq[1])

        overlap_start = max(0, int(preset["overlap_start_frame"]))
        num_frames = max(4, int(preset["num_frames_per_hit"]))
        frame_dt = max(0.016, float(preset["frame_duration"]))  # >= 60fps step
        thick2 = max(0, int(preset["hit2_thickness_boost"]))

        # ----------------------------
        # 1) center ของ effect = center ของ player (เดิม)
        # ----------------------------
        player = getattr(self.game, "player", None)
        if player is not None:
            player_center = pygame.Vector2(player.rect.center)
        else:
            player_center = pygame.Vector2(attack_rect.center)

        # ระยะจาก player → center ของ attack_rect (คงแนวเดิม)
        delta = pygame.Vector2(attack_rect.center) - player_center
        radius = delta.length()
        if radius <= 1:
            radius = 64.0
        radius = max(48.0, min(radius, 220.0))

        # ----------------------------
        # 2) หา base_angle จาก direction vector (หัวใจของความ “ธรรมชาติ”)
        # ----------------------------
        dir_vec = self._direction_to_vector(self.direction)
        base_angle = math.atan2(dir_vec.y, dir_vec.x)  # radians

        # ----------------------------
        # 3) สร้าง arc 2 hit จากเวกเตอร์
        # ----------------------------
        sweep_rad = math.radians(sweep_deg_v)
        cross_rad = math.radians(cross_deg_v)

        # hit1: clockwise (ตามเข็ม)
        world_pts_1 = self._build_arc_from_angle(
            radius=radius,
            center_angle=base_angle + cross_rad,
            sweep=sweep_rad,
            segments=48,
            clockwise=True,
        )

        # hit2: counterclockwise (ทวนเข็ม)
        world_pts_2 = self._build_arc_from_angle(
            radius=radius,
            center_angle=base_angle - cross_rad,
            sweep=sweep_rad,
            segments=48,
            clockwise=False,
        )

        # ----------------------------
        # 4) isometric transform ต่อ hit (stylize)
        # ----------------------------
        iso_pts_1 = self._iso_transform_points(world_pts_1, iso1)
        iso_pts_2 = self._iso_transform_points(world_pts_2, iso2)

        # รวมเพื่อหา surface ขนาดเดียว
        width, height = self._surface_size_for_sets([iso_pts_1, iso_pts_2], margin=24)

        p1 = self._to_surface_space_fixed(iso_pts_1, width, height)
        p2 = self._to_surface_space_fixed(iso_pts_2, width, height)

        # ----------------------------
        # 5) สร้างเฟรมแต่ละ hit แล้วซ้อนทับ timeline เพื่อให้ X ชัด
        # ----------------------------
        hit1_frames = self._build_frames(
            p1, width, height,
            num_frames=num_frames,
            seed_offset=0,
            thickness_boost=0,
        )
        hit2_frames = self._build_frames(
            p2, width, height,
            num_frames=num_frames,
            seed_offset=1000,
            thickness_boost=thick2,
        )

        total_frames = max(len(hit1_frames), overlap_start + len(hit2_frames))

        frames: List[pygame.Surface] = []
        for g in range(total_frames):
            base = pygame.Surface((width, height), pygame.SRCALPHA)

            if 0 <= g < len(hit1_frames):
                base.blit(hit1_frames[g], (0, 0))

            g2 = g - overlap_start
            if 0 <= g2 < len(hit2_frames):
                base.blit(hit2_frames[g2], (0, 0))

            frames.append(base)

        self.life_time = frame_dt * len(frames)
        super().__init__(frames, frame_dt, False, *groups)
        self.rect = self.image.get_rect(center=player_center)

    # ============================================================
    # Direction helpers
    # ============================================================
    @classmethod
    def _normalize_direction(cls, direction: str) -> str:
        d = (direction or "").lower().replace(" ", "_").replace("-", "_")
        aliases = {
            "upright": "up_right",
            "upleft": "up_left",
            "downright": "down_right",
            "downleft": "down_left",
        }
        return aliases.get(d, d)

    @classmethod
    def _direction_to_vector(cls, direction: str) -> pygame.Vector2:
        d = cls._normalize_direction(direction)
        vx, vy = cls._DIR_VEC.get(d, (0.0, 1.0))  # default down
        v = pygame.Vector2(vx, vy)
        if v.length_squared() == 0:
            return pygame.Vector2(0, 1)
        return v.normalize()

    # ============================================================
    # Arc builders (vector-based)
    # ============================================================
    @staticmethod
    def _build_arc_from_angle(
        radius: float,
        center_angle: float,
        sweep: float,
        segments: int = 48,
        clockwise: bool = True,
    ) -> List[Tuple[float, float]]:
        half = sweep * 0.5
        pts: List[Tuple[float, float]] = []

        if clockwise:
            a0 = center_angle + half
            a1 = center_angle - half
        else:
            a0 = center_angle - half
            a1 = center_angle + half

        for i in range(segments + 1):
            t = i / segments
            a = a0 + (a1 - a0) * t
            x = radius * math.cos(a)
            y = radius * math.sin(a)
            pts.append((x, y))

        return pts

    @staticmethod
    def _iso_transform_points(world_pts: List[Tuple[float, float]], iso_deg: float) -> List[Tuple[float, float]]:
        k = math.sin(math.radians(iso_deg))
        return [(x - y, (x + y) * k) for (x, y) in world_pts]

    @staticmethod
    def _surface_size_for_sets(
        sets: List[List[Tuple[float, float]]],
        margin: int = 24,
    ) -> Tuple[int, int]:
        xs: List[float] = []
        ys: List[float] = []
        for pts in sets:
            if not pts:
                continue
            xs.extend([p[0] for p in pts])
            ys.extend([p[1] for p in pts])

        if not xs or not ys:
            return (1, 1)

        half_w = max(abs(min(xs)), abs(max(xs))) + margin
        half_h = max(abs(min(ys)), abs(max(ys))) + margin
        return (max(1, int(half_w * 2)), max(1, int(half_h * 2)))

    @staticmethod
    def _to_surface_space_fixed(
        iso_points: List[Tuple[float, float]],
        width: int,
        height: int,
    ) -> List[Tuple[int, int]]:
        if not iso_points:
            return [(0, 0)]
        cx = width // 2
        cy = height // 2
        return [(int(round(x + cx)), int(round(y + cy))) for (x, y) in iso_points]

    # ============================================================
    # Visual (taper + bloom + spark)
    # ============================================================
    @staticmethod
    def _ease_out_cubic(t: float) -> float:
        t = max(0.0, min(1.0, t))
        return 1.0 - (1.0 - t) ** 3

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    @classmethod
    def _build_frames(
        cls,
        arc_points: List[Tuple[int, int]],
        width: int,
        height: int,
        num_frames: int = 10,
        seed_offset: int = 0,
        thickness_boost: int = 0,
    ) -> List[pygame.Surface]:
        if not arc_points or len(arc_points) < 2:
            return [pygame.Surface((width, height), pygame.SRCALPHA)]

        frames: List[pygame.Surface] = []
        n = len(arc_points)

        core_rgb = (210, 255, 255)
        glow_rgb = (0, 220, 255)

        for fi in range(num_frames):
            t = fi / max(num_frames - 1, 1)
            fade = 1.0 - cls._ease_out_cubic(t)

            surf = pygame.Surface((width, height), pygame.SRCALPHA)

            # Glow
            glow = pygame.Surface((width, height), pygame.SRCALPHA)
            base_thick = int(cls._lerp(18, 6, t)) + thickness_boost
            glow_alpha = int(110 * fade)

            for k in range(n - 1):
                u = k / max(n - 2, 1)
                w = max(2, int(base_thick * (1.0 - 0.65 * u)))
                a = int(glow_alpha * (1.0 - 0.35 * u))
                pygame.draw.line(glow, (*glow_rgb, a), arc_points[k], arc_points[k + 1], w)

            # Bloom
            bloom_scale = 1.08
            bw = max(1, int(width * bloom_scale))
            bh = max(1, int(height * bloom_scale))
            glow_big = pygame.transform.smoothscale(glow, (bw, bh))
            glow_soft = pygame.transform.smoothscale(glow_big, (width, height))
            surf.blit(glow_soft, (0, 0))

            # Core
            core_thick = int(cls._lerp(8, 2, t)) + max(0, thickness_boost // 2)
            core_alpha = int(220 * fade)

            for k in range(n - 1):
                u = k / max(n - 2, 1)
                w = max(1, int(core_thick * (1.0 - 0.75 * u)))
                a = int(core_alpha * (1.0 - 0.45 * u))
                pygame.draw.line(surf, (*core_rgb, a), arc_points[k], arc_points[k + 1], w)

            # Spark
            rng = random.Random(1337 + seed_offset + fi * 97)
            spark_count = 12 if thickness_boost else 10
            spread = 7 if thickness_boost else 6
            for _ in range(spark_count):
                idx = rng.randint(0, n - 1)
                px, py = arc_points[idx]
                ox = rng.randint(-spread, spread)
                oy = rng.randint(-spread, spread)
                r = rng.randint(1, 3)
                a = int(rng.randint(90, 180) * fade)
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
