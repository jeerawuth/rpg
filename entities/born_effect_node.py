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

    # ✅ cache เฟรมตาม (effect_id, scale)
    _FRAME_CACHE: dict[tuple[str, float], list[pygame.Surface]] = {}

    def __init__(
        self,
        game,
        pos: tuple[int, int],
        *groups,
        effect_id: str = "born",
        frame_duration: float = 0.08,
        lifetime: float = 2.0,
        scale: float = 0.5,
    ) -> None:
        self.game = game
        self.effect_id = effect_id
        self.lifetime = lifetime
        self._timer = lifetime
        self._extra_scale = scale

        cache_key = (self.effect_id, self._extra_scale)
        frames = self._FRAME_CACHE.get(cache_key)

        if frames is None:
            frames = self._load_frames()
            if not frames:
                surf = pygame.Surface((32, 32), pygame.SRCALPHA)
                surf.fill((255, 255, 0))
                frames = [surf]
            self._FRAME_CACHE[cache_key] = frames

        super().__init__(frames, frame_duration, True, *groups)
        self.rect.center = pos

    def _load_frames(self) -> list[pygame.Surface]:
        frames: list[pygame.Surface] = []
        index = 1
        rm = self.game.resources

        while True:
            rel_path = f"effects/{self.effect_id}_{index:02d}.png"
            try:
                surf = rm.load_image(rel_path)
            except Exception:
                break

            if self._extra_scale != 1.0:
                surf = rm._scale_surface(surf, self._extra_scale)

            frames.append(surf)
            index += 1

        return frames

    def update(self, dt: float) -> None:
        self._timer -= dt
        if self._timer <= 0.0:
            self.kill()
            return
        super().update(dt)
