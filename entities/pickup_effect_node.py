
from __future__ import annotations
import pygame
from .animated_node import AnimatedNode

class PickupEffectNode(AnimatedNode):
    """
    Shows a pickup effect (using 'hit' animation frames).
    Plays once and then destroys itself.
    """
    _FRAME_CACHE: dict[tuple[str, float], list[pygame.Surface]] = {}

    def __init__(
        self,
        game,
        pos: tuple[int, int],
        *groups,
        effect_id: str = "pickup",  # Default to 'pickup' sequence
        frame_duration: float = 0.05,
        scale: float = 0.5,
        target: pygame.sprite.Sprite | None = None, # Optional target to follow
    ) -> None:
        self.game = game
        self.effect_id = effect_id
        self._extra_scale = scale
        self.target = target

        cache_key = (self.effect_id, self._extra_scale)
        frames = self._FRAME_CACHE.get(cache_key)

        if frames is None:
            frames = self._load_frames()
            if not frames:
                # Fallback yellow square
                surf = pygame.Surface((32, 32), pygame.SRCALPHA)
                surf.fill((255, 255, 100, 150))
                frames = [surf]
            self._FRAME_CACHE[cache_key] = frames

        super().__init__(frames, frame_duration, False, *groups)  # loop=False
        self.rect.center = pos

    def _load_frames(self) -> list[pygame.Surface]:
        frames: list[pygame.Surface] = []
        index = 1
        rm = self.game.resources

        while True:
            # Try to load hit_01.png, hit_02.png...
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
        super().update(dt)
        if self.target and self.target.alive():
             self.rect.center = self.target.rect.center
        
        if self.finished:
            self.kill()
