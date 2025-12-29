# entities/lightning_effect_node.py
from __future__ import annotations

import math
import random
import pygame


class LightningEffectNode(pygame.sprite.Sprite):
    """
    LightningEffectNode (PRO VFX, procedural — no image files)

    เป้าหมาย (ตามเกมชั้นนำ):
    - “Core ขาว” + “สีขอบ” แบบสเปกตรัม (cyan→violet) ให้ดูแพงกว่าไฟฟ้าฟ้าขาวธรรมดา
    - Glow หลายชั้น + bloom นุ่ม ๆ
    - แตกแขนง (branch) + spark
    - มี “travel pulse” วิ่งไปตามเส้น เพื่อให้เห็น “ทิศทาง/การเคลื่อนที่” ชัดเจน
    - Flicker แบบไฟฟ้าจริง (ไม่ใช่แค่สลับเฟรมเฉย ๆ)
    - มี impact flash เล็ก ๆ ที่ปลาย (อ่านปลายทางชัดขึ้น)

    ✅ API เดิมยังใช้ได้:
        LightningEffectNode(start_pos, end_pos, *groups, duration=..., thickness=..., jitter=..., padding=...)

    ✅ เพิ่มแบบไม่กระทบของเดิม (keyword-only):
        theme="arcane" | "storm" | "holy" | "plasma"
    """

    # ---------- Preset palettes (RGBA) ----------
    _THEMES: dict[str, dict[str, tuple[int, int, int, int]]] = {
        # แนว “AAA/Arcane” : cyan + violet fringe (นิยมมากในเกมสมัยใหม่)
        "arcane": {
            "glow_far":  (115,  70, 255,  45),   # violet haze
            "glow_mid":  ( 60, 190, 255,  85),   # cyan
            "glow_near": (190, 245, 255, 145),   # near-white cyan
            "bolt_edge": (140, 120, 255, 210),   # violet edge
            "bolt_main": (120, 230, 255, 235),   # cyan main
            "core":      (255, 255, 255, 255),   # white core
            "impact":    (210, 255, 255, 200),
            "spark":     (255, 255, 255, 210),
        },
        # แนว “Storm” : teal/cyan แต่ดุดันขึ้น
        "storm": {
            "glow_far":  ( 20, 120, 255,  40),
            "glow_mid":  (  0, 210, 255,  85),
            "glow_near": (180, 255, 255, 140),
            "bolt_edge": ( 70, 160, 255, 205),
            "bolt_main": ( 70, 255, 255, 235),
            "core":      (255, 255, 255, 255),
            "impact":    (200, 255, 255, 200),
            "spark":     (255, 255, 255, 205),
        },
        # แนว “Holy/Gold lightning” : เหมือนสายฟ้าศักดิ์สิทธิ์ (นิยมใน soulslike บางเกม)
        "holy": {
            "glow_far":  (255, 175,  35,  40),
            "glow_mid":  (255, 215,  85,  85),
            "glow_near": (255, 245, 165, 150),
            "bolt_edge": (255, 220, 130, 220),
            "bolt_main": (255, 245, 185, 240),
            "core":      (255, 255, 255, 255),
            "impact":    (255, 245, 205, 210),
            "spark":     (255, 255, 255, 210),
        },
        # แนว “Plasma” : ม่วงชมพูแรง ๆ
        "plasma": {
            "glow_far":  (255,  60, 210,  38),
            "glow_mid":  (200,  80, 255,  80),
            "glow_near": (255, 200, 255, 140),
            "bolt_edge": (255, 140, 255, 215),
            "bolt_main": (230, 160, 255, 235),
            "core":      (255, 255, 255, 255),
            "impact":    (255, 220, 255, 200),
            "spark":     (255, 255, 255, 205),
        },
    }

    def __init__(
        self,
        start_pos: tuple[int, int],
        end_pos: tuple[int, int],
        *groups: pygame.sprite.Group,
        duration: float = 0.18,
        thickness: int = 6,
        jitter: int = 10,
        padding: int = 24,
        theme: str = "arcane",
        seed: int | None = None,
    ) -> None:
        super().__init__(*groups)

        self.start = pygame.Vector2(start_pos)
        self.end = pygame.Vector2(end_pos)

        self.duration = max(0.02, float(duration))
        self.timer = self.duration

        self._base_thickness = max(1, int(thickness))
        self._base_jitter = max(0, int(jitter))

        self._rng = random.Random(seed if seed is not None else random.randint(0, 10_000_000))

        theme_key = (theme or "arcane").strip().lower()
        self._pal = self._THEMES.get(theme_key, self._THEMES["arcane"])

        # bounding box (surface local space)
        min_x = min(self.start.x, self.end.x) - padding
        min_y = min(self.start.y, self.end.y) - padding
        max_x = max(self.start.x, self.end.x) + padding
        max_y = max(self.start.y, self.end.y) + padding
        w = int(max(2, max_x - min_x))
        h = int(max(2, max_y - min_y))

        self.origin = pygame.Vector2(min_x, min_y)

        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(int(min_x), int(min_y)))

        local_start = self.start - self.origin
        local_end = self.end - self.origin

        # --------- Animation frames ---------
        # travel pulse: ทำให้ดูเหมือนพลังไฟฟ้าวิ่งไปตามเส้น (ช่วยอ่านทิศทาง)
        self._frame_interval = 0.032
        self._frame_elapsed = 0.0
        self._frame_index = 0

        n_frames = 5
        self._frames = self._build_frames(
            w, h, local_start, local_end,
            thickness=self._base_thickness + 4,
            jitter=self._base_jitter,
            n_frames=n_frames,
        )

        self._base_surface = self._frames[self._frame_index]
        self.image.blit(self._base_surface, (0, 0))

    # -----------------------------
    # core rendering
    # -----------------------------
    def _build_frames(self, w, h, a, b, thickness, jitter, n_frames: int = 5):
        frames: list[pygame.Surface] = []
        n = max(1, int(n_frames))
        # phase 0->1 สำหรับ pulse วิ่งจาก start -> end
        for i in range(n):
            phase = i / n
            frames.append(self._build(w, h, a, b, thickness, jitter, pulse_phase=phase))
        return frames

    def _build(self, w, h, a, b, thickness, jitter, pulse_phase: float):
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        # colors
        glow_far = self._pal["glow_far"]
        glow_mid = self._pal["glow_mid"]
        glow_near = self._pal["glow_near"]
        bolt_edge = self._pal["bolt_edge"]
        bolt_main = self._pal["bolt_main"]
        core = self._pal["core"]
        
        # path
        pts = self._generate_main_path(a, b, jitter=jitter, steps=16)

        # 1) big haze glow (wide)
        self._draw_tapered_polyline(surf, pts, thickness + 17, max(2, int(thickness * 1.4)), glow_far)
        self._draw_tapered_polyline(surf, pts, thickness + 12, max(2, int(thickness * 1.2)), glow_mid)
        self._draw_tapered_polyline(surf, pts, thickness + 7,  max(2, int(thickness * 0.95)), glow_near)

        # 2) edge + main + core
        self._draw_tapered_polyline(surf, pts, thickness + 4, max(1, int(thickness * 0.55)), bolt_edge)
        self._draw_tapered_polyline(surf, pts, thickness + 2, max(1, int(thickness * 0.45)), bolt_main)
        self._draw_tapered_polyline(surf, pts, max(1, thickness - 1), 1, core)

        # 3) travel pulse (extra bright chunk) — ทำให้เห็น “วิ่ง”
        self._draw_travel_pulse(
            surf,
            pts,
            phase=pulse_phase,
            pulse_len=0.22,
            thickness=max(2, thickness + 3),
            col=core,
        )
        self._draw_travel_pulse(
            surf,
            pts,
            phase=pulse_phase,
            pulse_len=0.22,
            thickness=max(3, thickness + 7),
            col=glow_near,
        )

        # 4) branches + sparks
        length = (b - a).length()
        self._draw_branches(surf, pts, base_thickness=thickness, base_jitter=jitter, length=length)

        return surf

    # -----------------------------
    # path generation
    # -----------------------------
    def _generate_main_path(self, a: pygame.Vector2, b: pygame.Vector2, jitter: int, steps: int = 16):
        steps = max(6, int(steps))
        pts: list[tuple[int, int]] = []

        d = b - a
        length = d.length()
        if length <= 1e-3:
            return [(int(a.x), int(a.y)), (int(b.x), int(b.y))]

        # perpendicular for jitter
        n = pygame.Vector2(-d.y, d.x)
        if n.length_squared() > 0:
            n = n.normalize()

        for i in range(steps + 1):
            t = i / steps
            p = a.lerp(b, t)

            # jitter magnitude taper: more in the middle
            mid = 1.0 - abs(2.0 * t - 1.0)  # 0 at ends, 1 at center
            mag = jitter * (0.35 + 0.75 * mid)

            off = (self._rng.uniform(-mag, mag)) * n
            p2 = p + off

            pts.append((int(p2.x), int(p2.y)))

        # ensure exact ends
        pts[0] = (int(a.x), int(a.y))
        pts[-1] = (int(b.x), int(b.y))
        return pts

    # -----------------------------
    # drawing primitives
    # -----------------------------
    def _draw_tapered_polyline(
        self,
        surf: pygame.Surface,
        pts: list[tuple[int, int]],
        thick_start: int,
        thick_end: int,
        color: tuple[int, int, int, int],
    ) -> None:
        if len(pts) < 2:
            return
        thick_start = max(1, int(thick_start))
        thick_end = max(1, int(thick_end))

        n = len(pts) - 1
        for i in range(n):
            t = i / max(1, n - 1)
            w = int(thick_start + (thick_end - thick_start) * t)
            w = max(1, w)
            pygame.draw.line(surf, color, pts[i], pts[i + 1], w)

    def _draw_travel_pulse(
        self,
        surf: pygame.Surface,
        pts: list[tuple[int, int]],
        phase: float,
        pulse_len: float,
        thickness: int,
        col: tuple[int, int, int, int],
    ) -> None:
        if len(pts) < 4:
            return
        phase = max(0.0, min(1.0, phase))
        pulse_len = max(0.08, min(0.6, float(pulse_len)))

        n = len(pts)
        center = phase * (n - 1)
        half = pulse_len * (n - 1) * 0.5

        i0 = int(max(0, math.floor(center - half)))
        i1 = int(min(n - 1, math.ceil(center + half)))
        if i1 - i0 < 2:
            return

        # gaussian-ish alpha falloff
        for i in range(i0, i1):
            u = (i - center) / max(1e-6, half)
            fall = math.exp(-3.2 * (u * u))
            a = int(col[3] * fall)
            if a <= 0:
                continue
            c = (col[0], col[1], col[2], a)
            pygame.draw.line(surf, c, pts[i], pts[i + 1], max(1, int(thickness * fall)))

    # -----------------------------
    # branching + sparks
    # -----------------------------
    def _draw_branches(self, surf: pygame.Surface, main_pts: list[tuple[int, int]], base_thickness: int, base_jitter: int, length: float):
        # จำนวนแขนงตามความยาว (เพิ่มให้ชัดแบบเกมแอคชัน)
        # สูตรนี้ให้แขนงมากขึ้นแบบสมเหตุผลและไม่หนักเครื่อง
        n_branches = max(1, int(length / 65.0))
        n_branches = min(n_branches, 6)
        if length > 140 and self._rng.random() < 0.60:
            n_branches += 1
        n_branches = min(n_branches, 7)
        if n_branches <= 0:
            return

        branch_glow = self._pal["glow_mid"]
        branch_core = self._pal["core"]

        for _ in range(n_branches):
            idx = self._rng.randint(2, max(2, len(main_pts) - 4))
            p0 = pygame.Vector2(main_pts[idx])

            # direction of main segment near this point
            dir_main = pygame.Vector2(main_pts[idx + 1]) - pygame.Vector2(main_pts[idx - 1])
            if dir_main.length_squared() == 0:
                dir_main = pygame.Vector2(1, 0)
            else:
                dir_main = dir_main.normalize()

            # ✅ ทำให้แขนง “มุมแหลม” และชี้ไปทางเป้าหมายมากขึ้น
            # ใช้ทิศไปยังปลายสายฟ้าเป็นฐาน แล้วเบี่ยงมุมเล็กน้อย (ไม่ใช้ normal ตั้งฉาก)
            end_main = pygame.Vector2(main_pts[-1])
            to_target = end_main - p0
            if to_target.length_squared() == 0:
                to_target = dir_main
            else:
                to_target = to_target.normalize()

            # เบี่ยงมุมเล็กน้อยให้ดูแตกแขนง แต่ยังเป็นมุมแหลม (±10..±28 องศา)
            ang = self._rng.uniform(10.0, 28.0)
            if self._rng.random() < 0.5:
                ang *= -1.0
            branch_dir = to_target.rotate(ang)

            # ✅ แขนงสั้นลง (ดูเป็นธรรมชาติ ไม่เด้งออกด้านข้าง)
            branch_len = self._rng.uniform(14.0, 30.0) + (0.05 * min(300.0, length))

            end = p0 + branch_dir * branch_len

            steps = int(max(4, min(8, branch_len / 7.5)))
            pts = self._generate_main_path(p0, end, jitter=int(base_jitter * 0.65), steps=steps)

            t0 = max(2, int(base_thickness * 0.95))
            t1 = 1

            self._draw_tapered_polyline(surf, pts, t0 + 11, t1, (branch_glow[0], branch_glow[1], branch_glow[2], max(0, branch_glow[3] - 20)))
            self._draw_tapered_polyline(surf, pts, t0 + 6, t1, branch_glow)
            self._draw_tapered_polyline(surf, pts, max(1, t0 - 1), 1, branch_core)
    # -----------------------------
    # update
    # -----------------------------
    def update(self, dt: float) -> None:
        self.timer -= dt
        if self.timer <= 0:
            self.kill()
            return

        # frame cycling (pulse) + flicker
        self._frame_elapsed += dt
        if self._frame_elapsed >= self._frame_interval:
            self._frame_elapsed %= self._frame_interval
            self._frame_index = (self._frame_index + 1) % len(self._frames)
            self._base_surface = self._frames[self._frame_index]

        # fade curve: flash fast, decay smooth
        u = self.timer / self.duration  # 1 -> 0
        u = max(0.0, min(1.0, u))
        # quick initial flash feel: keep bright early
        fade = (u ** 0.85)
        # subtle flicker
        flicker = 0.88 + 0.12 * math.sin((1.0 - u) * 18.0) + self._rng.uniform(-0.06, 0.06)
        flicker = max(0.65, min(1.15, flicker))

        alpha = int(255 * fade * flicker)
        alpha = max(0, min(255, alpha))

        self.image = self._base_surface.copy()
        self.image.set_alpha(alpha)
