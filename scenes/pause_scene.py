# scenes/pause_scene.py
# Pause overlay

from __future__ import annotations

import pygame

from .base_scene import BaseScene
from config.settings import UI_FONT_PATH


class PauseScene(BaseScene):
    def __init__(self, game) -> None:
        super().__init__(game)
        self.title_font = self.game.resources.load_font(UI_FONT_PATH, 42)
        self.menu_font = self.game.resources.load_font(UI_FONT_PATH, 25)

    def handle_events(self, events) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_p):
                    # กลับไป game scene (pop ตัวเองออก)
                    self.game.scene_manager.pop_scene()

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        # วาด overlay ทับของ game scene ที่อยู่ข้างใต้
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        alpha = int(0.3 * 255)  # โปร่งแสง
        overlay.fill((10, 10, 30, alpha))  # (r,g,b,a)
        surface.blit(overlay, (0, 0))

        w, h = surface.get_size()
        title_surf = self.title_font.render("Paused", True, self.HUD_TEXT_COLOR)
        surface.blit(title_surf, title_surf.get_rect(center=(w // 2, h // 3)))

        lines = [
            "ESC / P - Resume",
        ]
        for i, t in enumerate(lines):
            t_surf = self.menu_font.render(t, True, self.HUD_TEXT_MUTED)
            surface.blit(t_surf, t_surf.get_rect(center=(w // 2, h // 2 + i * 32)))
