# core/audio_manager.py
# จัดการ BGM / SFX อย่างง่าย

import pygame

from .resource_manager import ResourceManager


class AudioManager:
    def __init__(self, resources: ResourceManager) -> None:
        self.resources = resources
        self._current_bgm: str | None = None

    # ---------- BGM ----------
    def play_bgm(self, music_file: str, loop: bool = True, volume: float = 0.7) -> None:
        if self._current_bgm == music_file:
            return

        pygame.mixer.music.stop()
        full_path = self.resources._resolve("sounds", "music", music_file)
        pygame.mixer.music.load(full_path)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(-1 if loop else 0)
        self._current_bgm = music_file

    def stop_bgm(self) -> None:
        pygame.mixer.music.stop()
        self._current_bgm = None

    # ---------- SFX ----------
    def play_sfx(self, sfx_file: str, volume: float = 1.0) -> None:
        sound = self.resources.load_sound(sfx_file)
        sound.set_volume(volume)
        sound.play()
