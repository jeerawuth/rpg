# core/camera.py
from __future__ import annotations

import math
import pygame


class Camera:
    """
    กล้องแบบ smooth + dead zone (ใช้ dt)

    - world_width/world_height  : ขนาด world เป็นพิกเซล
    - screen_width/screen_height: ขนาดหน้าจอ
    - follow_speed              : ความเร็วที่กล้องวิ่งไล่ target (หน่วย ~ ต่อวินาที)
    - deadzone_width/height     : ขนาด box กลางจอที่ target ขยับได้โดยกล้องยังไม่ขยับ
    """

    def __init__(
        self,
        world_width: int,
        world_height: int,
        screen_width: int,
        screen_height: int,
        follow_speed: float = 8.0,
        deadzone_width: int | None = None,
        deadzone_height: int | None = None,
    ) -> None:
        self.world_width = world_width
        self.world_height = world_height
        self.screen_width = screen_width
        self.screen_height = screen_height

        # ตำแหน่งจริงของกล้อง (float)
        self._pos = pygame.Vector2(0.0, 0.0)
        # offset ที่ใช้ตอนวาด (int)
        self.offset = pygame.Vector2(0.0, 0.0)

        # ความเร็วตาม (ค่ามาก = กล้องไล่เร็ว, เล็ก = หนืดนุ่ม)
        self.follow_speed = max(0.01, follow_speed)

        # dead zone
        if deadzone_width is None:
            deadzone_width = screen_width // 3
        if deadzone_height is None:
            deadzone_height = screen_height // 3

        self.deadzone_width = deadzone_width
        self.deadzone_height = deadzone_height

        self._screen_center = pygame.Vector2(
        # ศูนย์กลางจอ
            screen_width / 2,
            screen_height / 2,
        )

    # ---------- helper ----------
    def _clamp_to_world(self) -> None:
        """บังคับไม่ให้กล้องออกนอกขอบ world"""
        max_x = max(0.0, self.world_width - self.screen_width)
        max_y = max(0.0, self.world_height - self.screen_height)
        self._pos.x = max(0.0, min(self._pos.x, max_x))
        self._pos.y = max(0.0, min(self._pos.y, max_y))

    # ---------- main update ----------
    def update(self, target_rect: pygame.Rect, dt: float) -> None:
        """
        target_rect: rect ของ object ที่อยากให้กล้องตาม (เช่น player.rect)
        dt         : delta time (วินาที) จาก game loop
        """

        # ตำแหน่ง target ใน world
        target_center = pygame.Vector2(target_rect.centerx, target_rect.centery)

        # ตำแหน่ง target บนจอ จากกล้องปัจจุบัน
        target_screen = target_center - self._pos

        # ขอบ dead zone
        dz_half_w = self.deadzone_width / 2
        dz_half_h = self.deadzone_height / 2

        dz_left = self._screen_center.x - dz_half_w
        dz_right = self._screen_center.x + dz_half_w
        dz_top = self._screen_center.y - dz_half_h
        dz_bottom = self._screen_center.y + dz_half_h

        desired_pos = pygame.Vector2(self._pos)

        # X: ถ้าออกนอก dead zone ค่อยเลื่อนกล้อง
        if target_screen.x < dz_left:
            shift = dz_left - target_screen.x
            desired_pos.x -= shift
        elif target_screen.x > dz_right:
            shift = target_screen.x - dz_right
            desired_pos.x += shift

        # Y
        if target_screen.y < dz_top:
            shift = dz_top - target_screen.y
            desired_pos.y -= shift
        elif target_screen.y > dz_bottom:
            shift = target_screen.y - dz_bottom
            desired_pos.y += shift

        # ---------- smooth ด้วย dt ----------
        # factor แบบ exponential: independent จาก FPS
        # follow_speed ~ 5–12 กำลังดี
        t = 1.0 - math.exp(-self.follow_speed * dt)
        self._pos += (desired_pos - self._pos) * t

        # clamp ขอบ world
        self._clamp_to_world()

        # อัปเดต offset (ใช้ int ป้องกันวาดแล้วเบลอ/สั่น)
        self.offset.update(round(self._pos.x), round(self._pos.y))
