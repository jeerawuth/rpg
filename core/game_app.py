# core/game_app.py
# ตัวหลักของเกม: init pygame + main loop

from __future__ import annotations

import pygame

from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, WINDOW_TITLE
from .event_bus import EventBus
from .resource_manager import ResourceManager
from .audio_manager import AudioManager
from .scene_manager import SceneManager


class GameApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.mixer.init()

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE)

        self.clock = pygame.time.Clock()
        self.running = True

        # Core systems
        self.event_bus = EventBus()
        
        # กำหนด scale สำหรับ sprite กับ tile
        self.resources = ResourceManager(
            base_path="assets",
            sprite_scale=0.12,      # scale ตัวละคร / enemy
            tile_scale=1.0,         # tile ขนาดเดิม
            projectile_scale=0.1,   # ธนูเล็กลงตามสเกล
        )

        self.audio = AudioManager(self.resources)
        self.scene_manager = SceneManager(self)

    def quit(self) -> None:
        self.running = False

    def run(self) -> None:
        while self.running:
            dt_ms = self.clock.tick(FPS)
            dt = dt_ms / 1000.0

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False

            # ส่ง event ให้ scene ปัจจุบัน
            self.scene_manager.handle_events(events)
            self.scene_manager.update(dt)

            self.screen.fill((20, 20, 20))
            self.scene_manager.draw(self.screen)

            pygame.display.flip()

        pygame.quit()
