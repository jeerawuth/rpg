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
        title = self.font.render("Options (placeholder)", True, self.HUD_TEXT_COLOR)
        surface.blit(title, title.get_rect(center=(w // 2, h // 3)))

        lines = ["ESC / BACKSPACE - Back"]
        # วาดข้อความพร้อมแผงหลัง (มาตรฐาน HUD)
        # วางไว้กลางจอ
        line_h = self.font.get_height()
        block_w = max(self.font.size(t)[0] for t in lines)
        block_h = line_h
        panel = pygame.Rect(0, 0, block_w + 40, block_h + 26)
        panel.center = (w // 2, h // 2)
        self.draw_panel(surface, panel, alpha=self.HUD_BG_ALPHA)

        self.draw_text(surface, lines[0], (panel.left + 20, panel.top + 13 - line_h // 2), self.font, color=self.HUD_TEXT_COLOR, shadow=True)
