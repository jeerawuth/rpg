# scenes/lobby_scene.py
# ห้องรวมผู้เล่นก่อนเข้าแมตช์ (ตอนนี้ยังเป็น offline mock)

from __future__ import annotations

import pygame

from .base_scene import BaseScene
from config.settings import UI_FONT_PATH


class LobbyScene(BaseScene):
    def __init__(self, game) -> None:
        super().__init__(game)
        self.font = self.game.resources.load_font(UI_FONT_PATH, 32)

    def handle_events(self, events) -> None:
        from .game_scene import GameScene

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    # เข้าเกมจริง (match start)
                    self.game.scene_manager.set_scene(GameScene(self.game))
                elif event.key == pygame.K_ESCAPE:
                    # กำหนดให้ออกจากเกม หรือย้อนกลับไปยังจุดที่่ต้องการ
                    # self.game.scene_manager.pop_scene()
                    self.game.quit()

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((0, 40, 60))
        w, h = surface.get_size()
        title = self.font.render("เสร็จสิ้นภารกิจ", True, self.HUD_TEXT_COLOR)
        # Panel ให้ข้อความอ่านชัดทุกฉาก
        panel = pygame.Rect(0, 0, 520, 140)
        panel.center = (w // 2, h // 2 - 20)
        self.draw_panel(surface, panel, alpha=self.HUD_BG_ALPHA)

        surface.blit(title, title.get_rect(center=(w // 2, h // 3)))

        hint = self.font.render("ENTER - เริ่มเกม | ESC - ออกจากเกม", True, self.HUD_TEXT_MUTED)
        surface.blit(hint, hint.get_rect(center=(w // 2, h // 2)))