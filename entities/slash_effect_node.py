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

    # โหมดอัลติ (Ultimate): อลังการงานสร้าง
    # - กวาดกว้างมาก (150 องศา)
    # - เส้นหนาพิเศษ
    # - Spark เยอะ
    _ULTIMATE: Dict[str, Any] = {
        "sweep_deg": 150.0,
        "cross_offset_deg": 8.0,
        "iso_sequence_deg": (18.0, 30.0), # บิดมุมให้ดู 3D จัดๆ
        "overlap_start_frame": 4,
        "num_frames_per_hit": 10,  # เฟรมไม่ต้องเยอะมาก เน้นเร็ว
        "frame_duration": 0.035,   # เร็ว
        "hit2_thickness_boost": 8, # หนาสะใจ
    }

    _STYLE_PRESETS: Dict[str, Dict[str, Any]] = {
        "normal": _DEFAULTS,
        "default": _DEFAULTS,
        "fast": _DIABLO,
        "diablo": _DIABLO,
        "heavy": _SOULSLIKE,
        "soulslike": _SOULSLIKE,
        "souls": _SOULSLIKE,
        "ultimate": _ULTIMATE,
        "spectacular": _ULTIMATE,
    }


    # =========================
    # Precomputed frame cache (แก้กระตุกตอนฟัน)
    # =========================
    # SlashEffectNode มีการ "วาดเส้น + smoothscale + สร้างเฟรม" ตอน __init__ ซึ่งหนักมาก
    # โดยเฉพาะอาวุธที่ฟันรอบทิศทางจะสร้าง 8 โหนดพร้อมกัน (ดูที่ player_node.py)
    # เลยทำ cache เฟรมไว้ตาม (style, direction, radius_bucket, preset หลัก ๆ) แล้ว reuse ในครั้งถัดไป
    _FRAME_CACHE: Dict[tuple, tuple[List[pygame.Surface], float]] = {}
    _FRAME_CACHE_LIMIT: int = 96

    @classmethod
    def _cache_key(
        cls,
        *,
        style_key: str,
        direction: str,
        radius: float,
        sweep_deg_v: float,
        cross_deg_v: float,
        iso1: float,
        iso2: float,
        num_frames: int,
        overlap_start: int,
        thick2: int,
    core_rgb: Tuple[int, int, int],
    glow_rgb: Tuple[int, int, int],
    ) -> tuple:
        # bucket radius เพื่อให้ reuse ได้แม้ตัวเลขเล็กน้อยต่างกัน (ลด cache แตก)
        rb = int(round(radius / 8.0) * 8)
        return (
            style_key,
            direction,
            rb,
            int(round(sweep_deg_v * 10)),
            int(round(cross_deg_v * 10)),
            int(round(iso1 * 10)),
            int(round(iso2 * 10)),
            int(num_frames),
            int(overlap_start),
            int(thick2),
        int(core_rgb[0]), int(core_rgb[1]), int(core_rgb[2]),
        int(glow_rgb[0]), int(glow_rgb[1]), int(glow_rgb[2]),
        )

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
        theme: Dict[str, Tuple[int, int, int]] | None = None,
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

        # ----------------------------
        # 0.5) Theme colors (ปรับโทนสีได้จากฝั่ง caller เช่น PlayerNode)
        #  - ส่ง theme เป็น dict เช่น {"core_rgb": (210,255,255), "glow_rgb": (0,220,255)}
        # ----------------------------
        core_rgb = (210, 255, 255)
        glow_rgb = (0, 220, 255)
        if isinstance(theme, dict):
            core_rgb = tuple(theme.get("core_rgb", core_rgb))  # type: ignore[assignment]
            glow_rgb = tuple(theme.get("glow_rgb", glow_rgb))  # type: ignore[assignment]
        core_rgb = tuple(max(0, min(255, int(v))) for v in core_rgb)  # type: ignore[misc]
        glow_rgb = tuple(max(0, min(255, int(v))) for v in glow_rgb)  # type: ignore[misc]

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
        # Cache: ถ้าผ่านมาครั้งหนึ่งแล้ว จะ reuse เฟรมเดิมทันที (ลดอาการกระตุกมาก)
        # ----------------------------
        cache_key = self._cache_key(
            style_key=style_key,
            direction=self.direction,
            radius=radius,
            sweep_deg_v=sweep_deg_v,
            cross_deg_v=cross_deg_v,
            iso1=iso1,
            iso2=iso2,
            num_frames=num_frames,
            overlap_start=overlap_start,
            thick2=thick2,
        core_rgb=core_rgb,
        glow_rgb=glow_rgb,
        )
        cached = self._FRAME_CACHE.get(cache_key)
        if cached is not None:
            frames, cached_dt = cached
            # IMPORTANT: เฟรมใน cache ต้องถือว่าเป็น 'แม่แบบ' ห้ามแก้ไขใน place
            # AnimatedNode/เอฟเฟ็กต์บางตัวอาจทำ set_alpha / draw ทับบน self.image
            # ถ้าใช้เฟรมจาก cache ตรง ๆ จะทำให้ 'ครั้งแรก' กับ 'ครั้งถัดไป' หน้าตาไม่เหมือนกัน
            frames = [f.copy() for f in frames]
            self.life_time = cached_dt * len(frames)
            super().__init__(frames, cached_dt, False, *groups)
            self.rect = self.image.get_rect(center=player_center)
            return

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
        core_rgb=core_rgb,
        glow_rgb=glow_rgb,
        )
        hit2_frames = self._build_frames(
            p2, width, height,
            num_frames=num_frames,
            seed_offset=1000,
            thickness_boost=thick2,
        core_rgb=core_rgb,
        glow_rgb=glow_rgb,
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

        # ----------------------------
        # Cache store (จำกัดจำนวนเพื่อไม่กินแรมไม่จำเป็น)
        # ----------------------------
        if len(self._FRAME_CACHE) >= self._FRAME_CACHE_LIMIT:
            self._FRAME_CACHE.pop(next(iter(self._FRAME_CACHE)))
        self._FRAME_CACHE[cache_key] = ([f.copy() for f in frames], frame_dt)  # keep cache pristine

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
    def _draw_polygon_strip(
        cls,
        surface: pygame.Surface,
        points: List[Tuple[int, int]],
        color: Tuple[int, int, int, int],
        base_width: float,
        taper_power: float = 1.0,
    ) -> None:
        if len(points) < 2:
            return

        # Prepare vertices
        n = len(points)
        vertices = []
        
        # Calculate normals and widths
        for i in range(n):
            # Calculate direction
            if i < n - 1:
                dx = points[i+1][0] - points[i][0]
                dy = points[i+1][1] - points[i][1]
            else:
                dx = points[i][0] - points[i-1][0]
                dy = points[i][1] - points[i-1][1]
                
            dist = math.hypot(dx, dy)
            if dist == 0:
                nx, ny = 0, 0
            else:
                nx = -dy / dist
                ny = dx / dist

            # Average normal for internal points (smoother joins)
            if 0 < i < n - 1:
                p_dx = points[i][0] - points[i-1][0]
                p_dy = points[i][1] - points[i-1][1]
                p_dist = math.hypot(p_dx, p_dy)
                if p_dist > 0:
                    p_nx = -p_dy / p_dist
                    p_ny = p_dx / p_dist
                    nx = (nx + p_nx) * 0.5
                    ny = (ny + p_ny) * 0.5
                    # Re-normalize
                    n_dist = math.hypot(nx, ny)
                    if n_dist > 0:
                        nx /= n_dist
                        ny /= n_dist

            # Tapering
            prog = i / (n - 1)
            # Head (0) to Tail (1) or vice versa?
            # In arc_points, usually index 0 is start.
            # Let's assume uniform tapering for now based on style
            width_factor = 1.0 - (prog ** taper_power)
            current_width = max(1.0, base_width * width_factor)
            
            px, py = points[i]
            wx = nx * current_width * 0.5
            wy = ny * current_width * 0.5
            
            vertices.append(((px - wx, py - wy), (px + wx, py + wy), current_width))

        # Draw quads + rounds
        r, g, b, a = color
        for i in range(len(vertices) - 1):
            p0_l, p0_r, w0 = vertices[i]
            p1_l, p1_r, w1 = vertices[i+1]
            
            # Draw segment
            pygame.draw.polygon(surface, (r, g, b, a), [p0_l, p1_l, p1_r, p0_r])
            
            # Draw rounded joint at p1 (except last)
            if i < len(vertices) - 2:
                cx = (p1_l[0] + p1_r[0]) * 0.5
                cy = (p1_l[1] + p1_r[1]) * 0.5
                pygame.draw.circle(surface, (r, g, b, a), (cx, cy), w1 * 0.5)
        
        # Start cap
        p0_l, p0_r, w0 = vertices[0]
        cx = (p0_l[0] + p0_r[0]) * 0.5
        cy = (p0_l[1] + p0_r[1]) * 0.5
        pygame.draw.circle(surface, (r, g, b, a), (cx, cy), w0 * 0.5)
        
        # End cap
        pE_l, pE_r, wE = vertices[-1]
        cx = (pE_l[0] + pE_r[0]) * 0.5
        cy = (pE_l[1] + pE_r[1]) * 0.5
        pygame.draw.circle(surface, (r, g, b, a), (cx, cy), wE * 0.5)


    @classmethod
    def _build_frames(
        cls,
        arc_points: List[Tuple[int, int]],
        width: int,
        height: int,
        num_frames: int = 10,
        seed_offset: int = 0,
        thickness_boost: int = 0,
        core_rgb: Tuple[int, int, int] = (210, 255, 255),
        glow_rgb: Tuple[int, int, int] = (0, 220, 255),
    ) -> List[pygame.Surface]:
        if not arc_points or len(arc_points) < 2:
            return [pygame.Surface((width, height), pygame.SRCALPHA)]

        frames: List[pygame.Surface] = []
        n = len(arc_points)

        for fi in range(num_frames):
            t = fi / max(num_frames - 1, 1)
            # Fade out
            fade = 1.0 - cls._ease_out_cubic(t)
            
            surf = pygame.Surface((width, height), pygame.SRCALPHA)

            # --- 1) Glow Pass (Additive-like) ---
            # Wider, softer, alpha fades
            glow_surf = pygame.Surface((width, height), pygame.SRCALPHA)
            
            base_thick = 20.0 + thickness_boost * 1.5
            # Thicken as it fades? or shrink? 
            # Usually shrink slightly
            current_glow_width = base_thick * (1.0 - 0.2 * t)
            
            glow_alpha = int(120 * fade)
            
            cls._draw_polygon_strip(
                glow_surf, 
                arc_points, 
                (*glow_rgb, glow_alpha), 
                base_width=current_glow_width,
                taper_power=1.5
            )

            # Apply Bloom (Scale up and down)
            bloom_scale = 1.15
            bw = max(1, int(width * bloom_scale))
            bh = max(1, int(height * bloom_scale))
            glow_big = pygame.transform.smoothscale(glow_surf, (bw, bh))
            glow_soft = pygame.transform.smoothscale(glow_big, (width, height))
            
            # Blit brightened glow
            surf.blit(glow_soft, (0, 0))
            
            # --- 2) Core Pass (Sharp) ---
            core_thick = 6.0 + thickness_boost
            current_core_width = core_thick * (1.0 - 0.3 * t)
            core_alpha = int(255 * fade)
            
            cls._draw_polygon_strip(
                surf,
                arc_points,
                (*core_rgb, core_alpha),
                base_width=current_core_width,
                taper_power=1.2
            )

            # --- 3) Spark Pass ---
            rng = random.Random(1337 + seed_offset + fi * 97)
            spark_count = int(8 + thickness_boost)
            spread = int(4 + thickness_boost * 1.0)
            
            for _ in range(spark_count):
                idx = rng.randint(0, n - 1)
                px, py = arc_points[idx]
                ox = rng.randint(-spread, spread)
                oy = rng.randint(-spread, spread)
                
                # Varying size
                r = rng.uniform(1.0, 3.5)
                
                # Alpha flash
                a = int(rng.randint(150, 255) * fade)
                
                pygame.draw.circle(surf, (*core_rgb, a), (px + ox, py + oy), r)

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