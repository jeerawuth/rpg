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
        theme: dict | None = None,
        life: float = 0.10,
        radius_start: float = 6.0,
        radius_end: float = 22.0,
        thickness: int = 2,
        start_alpha: int = 130,
        glow: bool = True,
    ) -> None:
        super().__init__(*groups)
        self.center = pygame.Vector2(center)

        # Theme colors
        _theme = theme or {}
        self._core_rgb = tuple(_theme.get("core_rgb", (235, 255, 255)))
        self._glow_rgb = tuple(_theme.get("glow_rgb", (0, 220, 255)))
        self._core_rgb = tuple(max(0, min(255, int(v))) for v in self._core_rgb)
        self._glow_rgb = tuple(max(0, min(255, int(v))) for v in self._glow_rgb)

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

        glow_col = (*self._glow_rgb, a)
        core_col = (*self._core_rgb, min(255, a + 30))

        if self.glow:
            pygame.draw.circle(self.image, (*self._glow_rgb, max(0, a // 3)), (cx, cy), int(r) + 6, self.thickness + 6)
            pygame.draw.circle(self.image, (*self._glow_rgb, max(0, a // 2)), (cx, cy), int(r) + 3, self.thickness + 3)

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
        theme: dict | None = None,
        life: float = 0.14,
        start_alpha: int = 150,
        thickness: int = 4,
        glow: bool = True,
        pad: int = 14,
    ) -> None:
        super().__init__(*groups)
        self.p0 = pygame.Vector2(p0)
        self.p1 = pygame.Vector2(p1)
        # Theme colors
        _theme = theme or {}
        self._core_rgb = tuple(_theme.get("core_rgb", (235, 255, 255)))
        self._glow_rgb = tuple(_theme.get("glow_rgb", (0, 220, 255)))
        self._core_rgb = tuple(max(0, min(255, int(v))) for v in self._core_rgb)
        self._glow_rgb = tuple(max(0, min(255, int(v))) for v in self._glow_rgb)

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

        glow_col = (*self._glow_rgb, a)
        core_col = (*self._core_rgb, min(255, a + 30))

        if self.glow:
            # Lines
            pygame.draw.line(self.image, (*self._glow_rgb, max(0, a // 3)), p0, p1, self.thickness + 6)
            pygame.draw.line(self.image, (*self._glow_rgb, max(0, a // 2)), p0, p1, self.thickness + 3)
            
            # Rounded caps/joints (circles)
            pygame.draw.circle(self.image, (*self._glow_rgb, max(0, a // 3)), (int(p0.x), int(p0.y)), (self.thickness + 6) // 2)
            pygame.draw.circle(self.image, (*self._glow_rgb, max(0, a // 3)), (int(p1.x), int(p1.y)), (self.thickness + 6) // 2)

            pygame.draw.circle(self.image, (*self._glow_rgb, max(0, a // 2)), (int(p0.x), int(p0.y)), (self.thickness + 3) // 2)
            pygame.draw.circle(self.image, (*self._glow_rgb, max(0, a // 2)), (int(p1.x), int(p1.y)), (self.thickness + 3) // 2)

        pygame.draw.line(self.image, glow_col, p0, p1, self.thickness)
        # Main body caps
        pygame.draw.circle(self.image, glow_col, (int(p0.x), int(p0.y)), self.thickness // 2)
        pygame.draw.circle(self.image, glow_col, (int(p1.x), int(p1.y)), self.thickness // 2)

        pygame.draw.line(self.image, core_col, p0, p1, max(1, self.thickness // 2))

    def update(self, dt: float) -> None:
        self.t += dt
        if self.t >= self.life:
            self.kill()
            return
        alpha = int(self.a0 * (1.0 - self.t / self.life))
        self._draw(alpha)


class SwordSlashArcNode(pygame.sprite.Sprite):
    """
    PRO VERSION: High-quality sword slash effect using polygon trails.
    - Continuous geometry (no gaps)
    - Variable width (tapered tail)
    - Gradient alpha (fades out)
    - Additive blending for glow
    """

    # ========== Constants ==========
    _DIR_VEC: dict[str, tuple[float, float]] = {
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
    _SWEEP_DEG: float = 360.0
    _STEPS: int = 60  # Smoother steps

    # Visuals
    _TRAIL_LENGTH: int = 60     # Increased for smoother curve (was 14)
    _WIDTH_HEAD: float = 50.0   # Slightly wider head
    _WIDTH_TAIL: float = 1.0
    _SUB_STEPS: int = 4         # Sample 4 times per frame for high resolution

    def __init__(
        self,
        game,
        center_pos: tuple[int, int],
        direction: str,
        sword_image: pygame.Surface,
        radius: float = 140.0,
        duration: float = 0.25,
        *groups: pygame.sprite.AbstractGroup,
        theme: dict | None = None,
        target: pygame.sprite.Sprite | None = None,
    ) -> None:
        super().__init__(*groups)

        self.game = game
        self.center = pygame.Vector2(center_pos)
        self.target = target

        # Theme colors
        self._theme = theme or {}
        self._core_rgb = tuple(self._theme.get("core_rgb", (255, 255, 255)))
        self._glow_rgb = tuple(self._theme.get("glow_rgb", (0, 255, 255)))
        
        # Ensure RGB range
        self._core_rgb = tuple(max(0, min(255, int(v))) for v in self._core_rgb)
        self._glow_rgb = tuple(max(0, min(255, int(v))) for v in self._glow_rgb)

        self.direction = self._normalize_direction(direction)
        
        # Prepare sword sprite (visual only, floats at tip)
        self.base_image = sword_image.convert_alpha()
        # Tint logic
        tint_rgb = tuple(self._theme.get("sword_tint_rgb", self._glow_rgb))
        if tint_rgb != (0, 220, 255):
             tinted = self.base_image.copy()
             tint_surf = pygame.Surface(tinted.get_size(), pygame.SRCALPHA)
             tint_surf.fill((*tint_rgb, 255))
             tinted.blit(tint_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
             self.base_image = tinted

        self.radius = float(radius)
        self.duration = max(0.01, float(duration))
        self.elapsed = 0.0

        # Pre-calculate the arc path (relative offsets)
        dv = self._direction_to_vector(self.direction)
        base_angle = math.atan2(dv.y, dv.x)
        
        # 360 degree arc
        arc_offsets = self._generate_circle_offsets(
            start_angle=base_angle,
            radius=self.radius,
            steps=self._STEPS,
            clockwise=True,
        )
        self.iso_offsets = [self._to_isometric_offset(dx, dy, iso_deg=self._ISO_DEG) for (dx, dy) in arc_offsets]

        # Trail storage: List of (x, y, angle_deg)
        self.trail_points: deque[tuple[float, float, float]] = deque(maxlen=self._TRAIL_LENGTH)
        
        # Initial position
        start_x, start_y, _, _, start_angle = self._sample(0.0)
        
        # Initialize trail with starting point
        for _ in range(self._TRAIL_LENGTH):
            self.trail_points.append((start_x, start_y, start_angle))

        # Sprite image surface
        size = int(self.radius * 2.6 + 200)
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(start_x, start_y))
        
        # Relative drawing center
        self.draw_offset = pygame.Vector2(size // 2, size // 2)

    # ... Helper methods same as before ...
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
    def _generate_circle_offsets(start_angle, radius, steps, clockwise=True):
        steps = max(8, int(steps))
        sign = 1.0 if clockwise else -1.0
        pts = []
        for i in range(steps + 1):
            t = i / steps
            a = start_angle + sign * (2.0 * math.pi) * t
            pts.append((math.cos(a) * radius, math.sin(a) * radius))
        return pts

    @staticmethod
    def _to_isometric_offset(dx, dy, iso_deg=25.0):
        iso_angle = math.radians(float(iso_deg))
        sx = dx - dy
        sy = (dx + dy) * math.sin(iso_angle)
        return (sx, sy)

    def _sample(self, at_elapsed: float) -> tuple[float, float, float, float, float]:
        max_index = len(self.iso_offsets) - 1
        t = at_elapsed / self.duration
        t = max(0.0, min(1.0, t))

        pos_f = t * max_index
        i = int(pos_f)
        j = min(i + 1, max_index)
        local_t = pos_f - i

        ox1, oy1 = self.iso_offsets[i]
        ox2, oy2 = self.iso_offsets[j]
        
        ox = ox1 + (ox2 - ox1) * local_t
        oy = oy1 + (oy2 - oy1) * local_t

        if self.target and self.target.alive():
            cx, cy = self.target.rect.center
        else:
            cx, cy = self.center

        x = cx + ox
        y = cy + oy

        dx = ox2 - ox1
        dy = oy2 - oy1

        angle_deg = 0.0 if (dx == 0 and dy == 0) else -math.degrees(math.atan2(dy, dx))
        return x, y, dx, dy, angle_deg

    def update(self, dt: float) -> None:
        # Sub-step for high resolution trail
        sub_dt = dt / self._SUB_STEPS
        
        for _ in range(self._SUB_STEPS):
            self.elapsed += sub_dt
            if self.elapsed >= self.duration:
                self.kill()
                return

            x, y, dx, dy, angle_deg = self._sample(self.elapsed)
            self.trail_points.append((x, y, angle_deg))

        # --- Draw Logic ---
        
        # Update sprite position based on latest sample
        if self.target and self.target.alive():
            center_x, center_y = self.target.rect.center
        else:
            center_x, center_y = self.center
        self.rect.center = (center_x, center_y)
        
        # Clear image
        self.image.fill((0, 0, 0, 0))
        
        world_cx, world_cy = self.rect.center
        offset_x = self.draw_offset.x - world_cx
        offset_y = self.draw_offset.y - world_cy

        # 1. Draw Trail (Polygon Strip)
        points_len = len(self.trail_points)
        if points_len >= 2:
            vertices = []
            
            # Generate vertices
            for i, (px, py, pang) in enumerate(self.trail_points):
                progress = i / (points_len - 1)
                
                # Smoother tapering (sine or ease out)
                # width = tail + (head - tail) * progress^2
                width = self._WIDTH_TAIL + (self._WIDTH_HEAD - self._WIDTH_TAIL) * (progress ** 1.5)
                
                rad = math.radians(-pang + 90)
                wx = math.cos(rad) * width * 0.5
                wy = math.sin(rad) * width * 0.5
                
                sx = px + offset_x
                sy = py + offset_y
                
                vertices.append(((sx - wx, sy - wy), (sx + wx, sy + wy), width))

            # Draw quads + rounded joints
            for pass_idx in range(2): 
                for i in range(len(vertices) - 1):
                    p0_left, p0_right, w0 = vertices[i]
                    p1_left, p1_right, w1 = vertices[i+1]
                    
                    prog = i / (points_len - 1)
                    # Reduce max alpha further to 80 (~30%) as requested
                    alpha = int(80 * prog)
                    
                    if pass_idx == 0: # Glow (softer, wider)
                         color = (*self._glow_rgb, max(0, int(alpha * 0.4)))
                         # Draw polygon
                         pygame.draw.polygon(self.image, color, [p0_left, p1_left, p1_right, p0_right])
                         # Draw rounded joint at p1
                         p1_center = ((p1_left[0]+p1_right[0])/2, (p1_left[1]+p1_right[1])/2)
                         pygame.draw.circle(self.image, color, p1_center, w1 * 0.5)

                    else: # Core (sharper)
                        color = (*self._core_rgb, alpha)
                        pygame.draw.polygon(self.image, color, [p0_left, p1_left, p1_right, p0_right])
                        # Draw rounded joint at p1
                        p1_center = ((p1_left[0]+p1_right[0])/2, (p1_left[1]+p1_right[1])/2)
                        pygame.draw.circle(self.image, color, p1_center, w1 * 0.5)
                        
        # 2. Draw Sword Sprite
        # Use last sampled values
        rotated_sword = pygame.transform.rotate(self.base_image, angle_deg)
        r_rect = rotated_sword.get_rect(center=(x + offset_x, y + offset_y))
        self.image.blit(rotated_sword, r_rect)

        # 3. Flash at tip
        tip_x = x + offset_x
        tip_y = y + offset_y
        flash_color = (*self._core_rgb, 200)
        pygame.draw.circle(self.image, flash_color, (tip_x, tip_y), 5)
        
        # Extra flash line
        fl = 40
        pygame.draw.line(self.image, (*self._glow_rgb, 150), (tip_x - fl, tip_y), (tip_x + fl, tip_y), 2)
        pygame.draw.line(self.image, (*self._glow_rgb, 150), (tip_x, tip_y - fl), (tip_x, tip_y + fl), 2)