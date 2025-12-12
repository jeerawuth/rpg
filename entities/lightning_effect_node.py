# entities/lightning_effect_node.py
from __future__ import annotations
import random
import pygame

class LightningEffectNode(pygame.sprite.Sprite):
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
        self.duration = max(0.05, duration)
        self.timer = self.duration

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
        self._base_surface = self._build(w, h, local_start, local_end, thickness, jitter)
        self.image.blit(self._base_surface, (0, 0))

    def _build(self, w, h, a, b, thickness, jitter):
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        core = (255, 220, 120)
        glow = (255, 180, 40)

        pts = []
        steps = 8
        for i in range(steps + 1):
            t = i / steps
            p = a.lerp(b, t)
            if 0 < i < steps:
                p.x += random.randint(-jitter, jitter)
                p.y += random.randint(-jitter, jitter)
            pts.append((int(p.x), int(p.y)))

        pygame.draw.lines(surf, glow, False, pts, thickness + 3)
        pygame.draw.lines(surf, core, False, pts, thickness)
        return surf

    def update(self, dt: float) -> None:
        self.timer -= dt
        if self.timer <= 0:
            self.kill()
            return
        alpha = int(255 * (self.timer / self.duration))
        self.image = self._base_surface.copy()
        self.image.set_alpha(alpha)
