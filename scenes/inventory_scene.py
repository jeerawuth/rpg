# scenes/inventory_scene.py
# หน้าจัดการ inventory (ตอนนี้ยังเป็น placeholder)

from __future__ import annotations

import pygame

from .base_scene import BaseScene


class InventoryScene(BaseScene):
    def __init__(self, game) -> None:
        super().__init__(game)
        self.font = pygame.font.Font(None, 32)

    def handle_events(self, events) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_i):
                    self.game.scene_manager.pop_scene()

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((20, 20, 20, 230))
        surface.blit(overlay, (0, 0))

        w, h = surface.get_size()
        title = self.font.render("Inventory (placeholder)", True, (255, 255, 255))
        surface.blit(title, title.get_rect(center=(w // 2, h // 3)))

        hint = self.font.render("ESC / I - Close", True, (200, 200, 200))
        surface.blit(hint, hint.get_rect(center=(w // 2, h // 2)))
