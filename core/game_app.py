# core/game_app.py
# ตัวหลักของเกม: init pygame + main loop

from __future__ import annotations

import pygame

from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, WINDOW_TITLE, FULLSCREEN
from .event_bus import EventBus
from .resource_manager import ResourceManager
from .audio_manager import AudioManager
from .scene_manager import SceneManager


class GameApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.mixer.init()

        flags = 0
        if FULLSCREEN:
            # ใช้ FULLSCREEN | SCALED เพื่อให้ปรับความละเอียดตามจอที่รองรับอัตโนมัติ
            flags = pygame.FULLSCREEN | pygame.SCALED
        
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        pygame.display.set_caption(WINDOW_TITLE)

        self.clock = pygame.time.Clock()
        self.running = True

        # Core systems
        self.event_bus = EventBus()
        
        # กำหนด scale สำหรับ sprite กับ tile
        self.resources = ResourceManager(
            base_path="assets",
            sprite_scale=0.25,   # ขนาดตัวละคร / enemy
            tile_scale=1.0,      # ขนาด tile
            projectile_scale=0.2,  # ลูกธนู
            item_scale=0.2,        # ค่าเริ่มต้นของ items ทุกชนิด
            item_scale_overrides={
                # ทำให้ bow_power เล็กลงหน่อย (เช่น 50% ของไฟล์)
                "items/bow_power": 0.2,
                # ทำให้ bow_power เล็กลงหน่อย (เช่น 50% ของไฟล์)
                "items/potion_small": 0.1,
                # ขนาดไอเท็มโล่
                "items/shield": 0.2,
                # ขนาดไอเท็มฟันรอบทิศทาง
                "items/sword_all_direction": 0.2,
            },
        )

        self.audio = AudioManager(self.resources)
        self.scene_manager = SceneManager(self)

    def quit(self) -> None:
        self.running = False

    def add_log(self, text: str) -> None:
        """
        Delegate log message to the current scene if it supports it.
        """
        scene = getattr(self.scene_manager, "current_scene", None)
        if scene and hasattr(scene, "message_log"):
            scene.message_log.add(text)
        else:
            # Fallback print if no scene or no message_log
            print(f"[LOG] {text}")

    def run(self) -> None:
        while self.running:
            dt_ms = self.clock.tick(FPS)
            dt = dt_ms / 1000.0

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False

            # ส่ง event ให้ AudioManager (intro->loop, pending start หลัง fade)
            self.audio.handle_events(events)

            # ส่ง event ให้ scene ปัจจุบัน
            self.scene_manager.handle_events(events)
            self.scene_manager.update(dt)

            self.screen.fill((20, 20, 20))
            self.scene_manager.draw(self.screen)

            pygame.display.flip()

        pygame.quit()
