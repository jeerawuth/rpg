# entities/slash_effect_node.py
from __future__ import annotations
from typing import List
import pygame

from .animated_node import AnimatedNode


class SlashEffectNode(AnimatedNode):
    def __init__(
        self,
        game,
        attack_rect: pygame.Rect,
        direction: str,
        *groups,
    ) -> None:
        self.game = game
        self.direction = direction  # "up" / "down" / "left" / "right"

        # ----- โหลดเฟรมของเอฟเฟกต์ -----
        frames: List[pygame.Surface] = []

        index = 1
        while True:
            # คุณต้องมีไฟล์พวกนี้เช่น:
            # assets/graphics/images/effects/slash_down_01.png
            # assets/graphics/images/effects/slash_down_02.png ...
            rel_path = f"effects/slash_{direction}_{index:02d}.png"
            try:
                surf = self.game.resources.load_image(rel_path)
            except Exception:
                break
            frames.append(surf)
            index += 1

        # ถ้ายังไม่มี asset จริง ใช้สี่เหลี่ยมโปร่งใสแบบ debug แทน
        if not frames:
            surf = pygame.Surface(attack_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(surf, (255, 255, 0, 120), surf.get_rect(), 2)
            frames = [surf]

        # ตั้งค่า duration ของแต่ละเฟรม
        frame_duration = 0.05

        # NOTE: AnimatedNode.__init__(frames, frame_duration, loop, *groups)
        super().__init__(frames, frame_duration, False, *groups)

        # จัดตำแหน่งให้เฟรมครอบ attack_rect
        self.rect = self.image.get_rect(center=attack_rect.center)

        # ใช้เวลาชีวิตเท่ากับจำนวนเฟรม * frame_duration
        self.life_time = frame_duration * len(frames)

    def update(self, dt: float) -> None:
        self.life_time -= dt
        if self.life_time <= 0:
            self.kill()
            return

        super().update(dt)
