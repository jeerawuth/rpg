# scenes/main_menu_scene.py
# เมนูหลักแบบง่าย ๆ: Start / Options / Exit

from __future__ import annotations

import pygame

from .base_scene import BaseScene


class MainMenuScene(BaseScene):
    def __init__(self, game) -> None:
        super().__init__(game)
        self.title_font = pygame.font.Font(None, 72)
        self.menu_font = pygame.font.Font(None, 36)

    def handle_events(self, events) -> None:
        from .game_scene import GameScene  # import ภายในกันวงกลม

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    # start game
                    self.game.scene_manager.set_scene(GameScene(self.game))
                elif event.key == pygame.K_o:
                    from .options_scene import OptionsScene
                    self.game.scene_manager.push_scene(OptionsScene(self.game))
                elif event.key == pygame.K_ESCAPE:
                    self.game.quit()

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()
        surface.fill((10, 10, 30))

        title_surf = self.title_font.render("My 2D Action RPG", True, (255, 255, 255))
        surface.blit(title_surf, title_surf.get_rect(center=(w // 2, h // 3)))

        lines = [
            "ENTER - Start Game",
            "O     - Options",
            "ESC   - Exit",
        ]
        for i, text in enumerate(lines):
            t_surf = self.menu_font.render(text, True, (200, 200, 200))
            surface.blit(t_surf, t_surf.get_rect(center=(w // 2, h // 2 + i * 40)))
