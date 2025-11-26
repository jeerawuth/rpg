# scenes/options_scene.py
# หน้าตั้งค่า (placeholder)

from __future__ import annotations

import pygame

from .base_scene import BaseScene


class OptionsScene(BaseScene):
    def __init__(self, game) -> None:
        super().__init__(game)
        self.font = pygame.font.Font(None, 32)

    def handle_events(self, events) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    self.game.scene_manager.pop_scene()

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((15, 15, 40))
        w, h = surface.get_size()
        title = self.font.render("Options (placeholder)", True, (255, 255, 255))
        surface.blit(title, title.get_rect(center=(w // 2, h // 3)))

        hint = self.font.render("ESC / BACKSPACE - Back", True, (200, 200, 200))
        surface.blit(hint, hint.get_rect(center=(w // 2, h // 2)))
