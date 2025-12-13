# scenes/game_over_scene.py

from __future__ import annotations

import pygame

from .base_scene import BaseScene


class GameOverScene(BaseScene):
    def __init__(self, game, score: int = 0) -> None:
        super().__init__(game)
        self.font_big = pygame.font.Font(None, 64)
        self.font_small = pygame.font.Font(None, 32)
        self.score = score

    def handle_events(self, events) -> None:
        from .main_menu_scene import MainMenuScene

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.game.scene_manager.set_scene(MainMenuScene(self.game))
                elif event.key == pygame.K_ESCAPE:
                    self.game.quit()

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        
        # สร้าง overlay โปร่งแสงมาทับ เพื่อให้เห็นว่าเกมหยุดแล้ว
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        alpha = int(0.4 * 255)  # โปร่งแสง
        overlay.fill((10, 10, 30, alpha))  # (r,g,b,a)

        # วาด overlay ทับฉากเดิม
        surface.blit(overlay, (0, 0))

        w, h = surface.get_size()
        title = self.font_big.render("Game Over", True, self.HUD_TEXT_COLOR)
        surface.blit(title, title.get_rect(center=(w // 2, h // 3)))

        # แสดง score
        # score = self.font_small.render(f"Score: {self.score}", True, self.HUD_TEXT_MUTED)
        # surface.blit(score, score.get_rect(center=(w // 2, h // 2)))

        hint = self.font_small.render("ENTER - Main Menu | ESC - Quit", True, self.HUD_TEXT_MUTED)
        surface.blit(hint, hint.get_rect(center=(w // 2, h // 2)))
