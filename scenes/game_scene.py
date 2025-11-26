# scenes/game_scene.py
# ฉากเกมจริง (ตอนนี้ยังเป็น mock world)

from __future__ import annotations

import pygame

from .base_scene import BaseScene


class GameScene(BaseScene):
    def __init__(self, game) -> None:
        super().__init__(game)
        self.font = pygame.font.Font(None, 32)

        # TODO: โหลด world/tilemap, player, enemy ฯลฯ
        self.player_pos = pygame.Vector2(400, 300)
        self.player_speed = 220

    def handle_events(self, events) -> None:
        from .pause_scene import PauseScene
        from .inventory_scene import InventoryScene

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.scene_manager.push_scene(PauseScene(self.game))
                elif event.key == pygame.K_i:
                    self.game.scene_manager.push_scene(InventoryScene(self.game))

    def update(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        velocity = pygame.Vector2(0, 0)
        if keys[pygame.K_w]:
            velocity.y -= 1
        if keys[pygame.K_s]:
            velocity.y += 1
        if keys[pygame.K_a]:
            velocity.x -= 1
        if keys[pygame.K_d]:
            velocity.x += 1
        if velocity.length_squared() > 0:
            velocity = velocity.normalize() * self.player_speed * dt
            self.player_pos += velocity

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((30, 100, 50))

        # วาด player เป็นวงกลมสีขาว
        pygame.draw.circle(surface, (240, 240, 240), self.player_pos, 16)

        # HUD text
        text_lines = [
            "Game Scene",
            "WASD - Move",
            "ESC  - Pause",
            "I    - Inventory",
        ]
        for i, t in enumerate(text_lines):
            t_surf = self.font.render(t, True, (10, 10, 10))
            surface.blit(t_surf, (20, 20 + i * 24))
