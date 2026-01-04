# scenes/main_menu_scene.py
# เมนูหลักแบบง่าย ๆ: Start / Options / Exit

from __future__ import annotations

import pygame

from .base_scene import BaseScene
from config.settings import UI_FONT_PATH


class MainMenuScene(BaseScene):
    def __init__(self, game) -> None:
        super().__init__(game)
        self.title_font = self.game.resources.load_font(UI_FONT_PATH, 42)
        self.menu_font = self.game.resources.load_font(UI_FONT_PATH, 25)

    def handle_events(self, events) -> None:
        from .game_scene import GameScene  # import ภายในกันวงกลม
        from .preload_scene import PreloadScene

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    # start game (รอบแรกจะโหลด asset เยอะ ให้ผ่านหน้าโหลดก่อน)
                    self.game.scene_manager.set_scene(
                        PreloadScene(
                            self.game,
                            level_id="level01",
                            next_scene_factory=lambda: GameScene(self.game),
                            items_per_frame=2,
                            title="Loading...",
                            note="กำลังเตรียมทรัพยากรครั้งแรก",
                        )
                    )
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
            "ENTER - เริ่มเกม",
            "O     - ตัวเลือก",
            "ESC   - ออกจากเกม",
        ]
        # Panel สำหรับเมนู (พื้นหลังดำโปร่ง 10% + ตัวหนังสือขาว)
        # วาดบล็อกข้อความแบบ center เอง เพื่อให้สวยและอ่านง่าย
        line_h = self.menu_font.get_height()
        widths = [self.menu_font.size(t)[0] for t in lines]
        block_w = max(widths)
        block_h = len(lines) * line_h + (len(lines) - 1) * 10

        panel = pygame.Rect(0, 0, block_w + 40, block_h + 30)
        panel.center = (w // 2, h // 2 + 10)
        self.draw_panel(surface, panel, alpha=self.HUD_BG_ALPHA)

        y = panel.top + 15
        for t in lines:
            # วาดแบบ center
            t_surf = self.menu_font.render(t, True, self.HUD_TEXT_COLOR)
            rect = t_surf.get_rect(centerx=panel.centerx, y=y)
            # shadow
            s_surf = self.menu_font.render(t, True, self.HUD_SHADOW_COLOR)
            surface.blit(s_surf, (rect.x + 1, rect.y + 1))
            surface.blit(t_surf, rect)
            y += line_h + 10