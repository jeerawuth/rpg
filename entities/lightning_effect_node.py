# entities/lightning_effect_node.py
from __future__ import annotations

import math
import random
import pygame


class LightningEffectNode(pygame.sprite.Sprite):
    """
    เอฟเฟ็กต์สายฟ้าแบบไม่ใช้ไฟล์ภาพ (procedural):
    - มี glow หลายชั้น + core สีขาวด้านใน
    - ปลายสายฟ้าทรงเรียว (taper)
    - มีแขนงแตก (branching) + spark เล็ก ๆ ใกล้ปลาย
    - มี flicker เล็กน้อยระหว่างอายุเอฟเฟ็กต์ แต่ยังคง API เดิม
    """

    def __init__(
        self,
        start_pos: tuple[int, int],
        end_pos: tuple[int, int],
        *groups: pygame.sprite.Group,
        duration: float = 0.18,
        thickness: int = 3,
        jitter: int = 10,
        padding: int = 24,
    ) -> None:
        super().__init__(*groups)

        self.start = pygame.Vector2(start_pos)
        self.end = pygame.Vector2(end_pos)
        self.duration = max(0.05, float(duration))
        self.timer = self.duration

        # เก็บไว้ใช้ตอนสร้างเฟรม
        self._base_thickness = max(1, int(thickness))
        self._base_jitter = max(1, int(jitter))

        # คำนวณพื้นที่ผ้าใบพอดี ๆ
        min_x = min(self.start.x, self.end.x) - padding
        min_y = min(self.start.y, self.end.y) - padding
        max_x = max(self.start.x, self.end.x) + padding
        max_y = max(self.start.y, self.end.y) + padding

        self.origin = pygame.Vector2(min_x, min_y)
        w = int(max(2, max_x - min_x))
        h = int(max(2, max_y - min_y))

        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(int(min_x), int(min_y)))

        local_start = self.start - self.origin
        local_end = self.end - self.origin

        # ทำเป็นหลายเฟรมเพื่อให้ flicker ดูสมจริงขึ้น (ยังเป็น effect เดิม ไม่กระทบเกมเพลย์)
        self._frame_interval = 0.04  # วิ ต่อเฟรม
        self._frame_elapsed = 0.0
        self._frames = self._build_frames(
            w, h, local_start, local_end, self._base_thickness, self._base_jitter, n_frames=3
        )
        self._frame_index = 0

        # เฟรมแรก
        self._base_surface = self._frames[self._frame_index]
        self.image.blit(self._base_surface, (0, 0))

    # -----------------------------
    # core rendering
    # -----------------------------
    def _build_frames(self, w, h, a, b, thickness, jitter, n_frames: int = 3):
        frames: list[pygame.Surface] = []
        for _ in range(max(1, n_frames)):
            frames.append(self._build(w, h, a, b, thickness, jitter))
        return frames

    def _build(self, w, h, a, b, thickness, jitter):
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        # ความยาวใช้กำหนดจำนวนจุด/ระดับ jitter ให้เหมาะสม
        vec = pygame.Vector2(b) - pygame.Vector2(a)
        length = max(1.0, vec.length())
        steps = int(max(8, min(26, length / 28)))  # ยิ่งยาวยิ่งมีจุดมากขึ้น

        pts = self._generate_main_path(a, b, jitter=jitter, steps=steps)

        # ---------- สี (glow + core) ----------
        # เลเยอร์ด้านนอก (glow) อ่อน ๆ
        glow_far = (255, 180, 40, 55)
        glow_mid = (255, 210, 80, 95)
        glow_near = (255, 235, 140, 150)

        # ตัวสายฟ้าด้านใน + core ขาว
        bolt_yellow = (255, 235, 170, 230)
        core_white = (255, 255, 255, 255)

        # ---------- วาดเส้นหลัก (ใช้ taper) ----------
        # ทำปลายเล็กลง: start หนากว่า end
        t0 = thickness + 7
        t1 = max(1, int(thickness * 0.65))

        self._draw_tapered_polyline(surf, pts, t0, max(1, int(t1 * 0.7)), glow_far)
        self._draw_tapered_polyline(surf, pts, thickness + 4, max(1, int(t1 * 0.6)), glow_mid)
        self._draw_tapered_polyline(surf, pts, thickness + 2, max(1, int(t1 * 0.55)), glow_near)

        # main bolt
        self._draw_tapered_polyline(surf, pts, thickness + 1, max(1, int(t1 * 0.5)), bolt_yellow)
        # inner core
        self._draw_tapered_polyline(surf, pts, max(1, thickness - 1), 1, core_white)

        # ---------- แขนงแตก (branching) ----------
        self._draw_branches(
            surf,
            pts,
            base_thickness=thickness,
            base_jitter=jitter,
            length=length,
        )

        # ---------- spark ใกล้ปลาย ----------
        self._draw_sparks(surf, pygame.Vector2(pts[-1]), core_white, glow_mid)

        return surf

    def _generate_main_path(self, a, b, jitter: int, steps: int):
        a = pygame.Vector2(a)
        b = pygame.Vector2(b)
        d = b - a
        length = max(1.0, d.length())
        dirv = d / length

        # เวกเตอร์ตั้งฉาก
        normal = pygame.Vector2(-dirv.y, dirv.x)

        pts: list[tuple[int, int]] = []
        for i in range(steps + 1):
            t = i / steps
            p = a.lerp(b, t)

            # taper ให้ jitter มากช่วงกลาง น้อยช่วงปลาย
            mid_peak = 1.0 - abs(2.0 * t - 1.0)  # 0 ที่ปลาย, 1 ที่กลาง
            mid_peak = mid_peak ** 0.7

            if 0 < i < steps:
                # offset ตามแนวตั้งฉากเป็นหลัก
                off_n = random.uniform(-1.0, 1.0) * jitter * mid_peak
                # ขยับตามแนวเส้นเล็กน้อย (ช่วยให้ดูเป็นฟ้าผ่าจริง ๆ)
                off_d = random.uniform(-1.0, 1.0) * (jitter * 0.18) * mid_peak
                p += normal * off_n + dirv * off_d

            pts.append((int(p.x), int(p.y)))

        return pts

    def _draw_tapered_polyline(
        self,
        surf: pygame.Surface,
        pts: list[tuple[int, int]],
        thickness_start: int,
        thickness_end: int,
        color: tuple[int, int, int, int],
    ) -> None:
        if len(pts) < 2:
            return

        n_seg = len(pts) - 1
        for i in range(n_seg):
            t = i / max(1, n_seg - 1)
            # taper จาก start -> end
            w = int(round(thickness_start + (thickness_end - thickness_start) * t))
            w = max(1, w)
            pygame.draw.line(surf, color, pts[i], pts[i + 1], w)

    def _draw_branches(
        self,
        surf: pygame.Surface,
        main_pts: list[tuple[int, int]],
        base_thickness: int,
        base_jitter: int,
        length: float,
    ) -> None:
        if len(main_pts) < 5:
            return

        # จำนวนแขนงตามความยาว
        max_branches = 1 if length < 180 else 2 if length < 360 else 3
        n_branches = random.randint(1, max_branches)

        # สีแขนงให้จางลงนิด
        branch_glow = (255, 210, 90, 90)
        branch_core = (255, 255, 255, 210)

        # เลือกจุดเริ่มแขนง (หลีกเลี่ยงใกล้ปลายมากเกินไป)
        candidate = list(range(2, len(main_pts) - 3))
        random.shuffle(candidate)

        for idx in candidate[:n_branches]:
            p0 = pygame.Vector2(main_pts[idx])
            p1 = pygame.Vector2(main_pts[idx + 1])
            d = p1 - p0
            if d.length_squared() < 1:
                continue

            dirv = d.normalize()

            # หมุนออกด้านข้างแบบสุ่ม (±)
            sign = -1 if random.random() < 0.5 else 1
            angle = sign * random.uniform(20, 55)
            dir_rot = dirv.rotate(angle)

            branch_len = length * random.uniform(0.14, 0.26)
            end = p0 + dir_rot * branch_len

            steps = int(max(4, min(10, branch_len / 35)))
            pts = self._generate_main_path(p0, end, jitter=int(base_jitter * 0.55), steps=steps)

            # แขนงเล็กกว่าเส้นหลัก
            t0 = max(2, int(base_thickness * 0.9))
            t1 = 1

            self._draw_tapered_polyline(surf, pts, t0 + 3, t1, branch_glow)
            self._draw_tapered_polyline(surf, pts, t0 + 1, t1, (255, 235, 170, 170))
            self._draw_tapered_polyline(surf, pts, max(1, t0 - 1), 1, branch_core)

            # spark เล็ก ๆ ที่ปลายแขนง
            self._draw_sparks(surf, pygame.Vector2(pts[-1]), branch_core, branch_glow, n=random.randint(1, 2))

    def _draw_sparks(
        self,
        surf: pygame.Surface,
        pos: pygame.Vector2,
        core_color: tuple[int, int, int, int],
        glow_color: tuple[int, int, int, int],
        n: int = 3,
    ) -> None:
        # spark เป็นเส้นสั้น ๆ กระจายรอบปลาย ช่วยให้ดู "แตกกระจาย"
        for _ in range(n):
            ang = random.uniform(0, 360)
            length = random.uniform(10, 22)
            end = pos + pygame.Vector2(length, 0).rotate(ang)

            # glow ก่อน
            pygame.draw.line(surf, glow_color, (int(pos.x), int(pos.y)), (int(end.x), int(end.y)), 2)
            # core
            pygame.draw.line(surf, core_color, (int(pos.x), int(pos.y)), (int(end.x), int(end.y)), 1)

    # -----------------------------
    # update
    # -----------------------------
    def update(self, dt: float) -> None:
        self.timer -= dt
        if self.timer <= 0:
            self.kill()
            return

        # flicker: สลับเฟรมทุก ๆ _frame_interval เล็กน้อย
        self._frame_elapsed += dt
        if self._frame_elapsed >= self._frame_interval and len(self._frames) > 1:
            self._frame_elapsed %= self._frame_interval
            # สลับแบบสุ่มเล็กน้อยให้เหมือนฟ้าผ่า
            self._frame_index = (self._frame_index + 1) % len(self._frames)
            self._base_surface = self._frames[self._frame_index]

        # fade out
        alpha = int(255 * (self.timer / self.duration))
        alpha = max(0, min(255, alpha))

        self.image = self._base_surface.copy()
        self.image.set_alpha(alpha)
