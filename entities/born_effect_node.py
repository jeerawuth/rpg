# entities/born_effect_node.py
from __future__ import annotations

import pygame

from .animated_node import AnimatedNode


class BornEffectNode(AnimatedNode):
    """
    เอฟเฟกต์แจ้งเตือนตำแหน่งเกิดศัตรู
    โหลดรูปจาก assets/graphics/images/effects/born_01.png, born_02.png, ...
    แล้วเล่น loop ตาม lifetime
    """

    def __init__(
        self,
        game,
        pos: tuple[int, int],
        *groups,
        effect_id: str = "born",
        frame_duration: float = 0.08,
        lifetime: float = 2.0,
        scale: float = 0.5,     # ขยาย/ย่อจากขนาดที่ ResourceManager ให้มา
    ) -> None:
        self.game = game
        self.effect_id = effect_id
        self.lifetime = lifetime
        self._timer = lifetime
        self._extra_scale = scale

        frames = self._load_frames()

        if not frames:
            surf = pygame.Surface((32, 32), pygame.SRCALPHA)
            surf.fill((255, 255, 0))
            frames = [surf]

        # ส่ง frames ให้ AnimatedNode
        super().__init__(frames, frame_duration, True, *groups)

        self.rect.center = pos

    # ------------------------------------------------------------
    # โหลดเฟรมจาก ResourceManager
    # ------------------------------------------------------------
    def _load_frames(self) -> list[pygame.Surface]:
        frames: list[pygame.Surface] = []
        index = 1
        rm = self.game.resources

        while True:
            rel_path = f"effects/{self.effect_id}_{index:02d}.png"
            try:
                surf = rm.load_image(rel_path)  # 👉 ได้รูปที่โดน sprite_scale แล้ว
            except Exception:
                break

            # ถ้าอยากให้ born_effect ใหญ่/เล็กกว่า sprite ปกติ
            if self._extra_scale != 1.0:
                # ใช้ helper เดิมของ ResourceManager ซ้ำได้เลย
                surf = rm._scale_surface(surf, self._extra_scale)

            frames.append(surf)
            index += 1

        return frames

    # ------------------------------------------------------------
    # update
    # ------------------------------------------------------------
    def update(self, dt: float) -> None:
        self._timer -= dt
        if self._timer <= 0.0:
            self.kill()
            return

        super().update(dt)
