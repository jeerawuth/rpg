# core/resource_manager.py
# โหลด/แคชภาพและเสียง

import os
from typing import Dict

import pygame


class ResourceManager:
    def __init__(self, base_path: str = "assets") -> None:
        self.base_path = base_path
        self._images: Dict[str, pygame.Surface] = {}
        self._sounds: Dict[str, pygame.mixer.Sound] = {}
        self._fonts: Dict[tuple, pygame.font.Font] = {}

    def _resolve(self, *parts: str) -> str:
        return os.path.join(self.base_path, *parts)

    # ---------- Images ----------
    def load_image(self, relative_path: str, colorkey=None) -> pygame.Surface:
        if relative_path in self._images:
            return self._images[relative_path]

        full_path = self._resolve("graphics", relative_path)
        image = pygame.image.load(full_path).convert_alpha()
        if colorkey is not None:
            image.set_colorkey(colorkey)
        self._images[relative_path] = image
        return image

    # ---------- Sounds ----------
    def load_sound(self, relative_path: str) -> pygame.mixer.Sound:
        if relative_path in self._sounds:
            return self._sounds[relative_path]

        full_path = self._resolve("sounds", "sfx", relative_path)
        sound = pygame.mixer.Sound(full_path)
        self._sounds[relative_path] = sound
        return sound

    # ---------- Fonts ----------
    def load_font(self, size: int, name: str | None = None) -> pygame.font.Font:
        key = (name, size)
        if key in self._fonts:
            return self._fonts[key]

        if name is None:
            font = pygame.font.Font(None, size)
        else:
            full_path = self._resolve("fonts", name)
            font = pygame.font.Font(full_path, size)

        self._fonts[key] = font
        return font
