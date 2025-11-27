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

    # ---------- Utils ----------
    def _resolve(self, *parts: str) -> str:
        """ประกอบ path จาก base_path + parts ต่าง ๆ"""
        return os.path.join(self.base_path, *parts)

    # ---------- Images ----------
    def load_image(self, relative_path: str, colorkey=None) -> pygame.Surface:
        """
        relative_path สามารถเป็นได้หลายแบบ เช่น
            "player/idle_0.png"          -> assets/graphics/images/player/idle_0.png
            "images/player/idle_0.png"   -> assets/graphics/images/player/idle_0.png
            "tiles/overworld_tiles.png"  -> assets/graphics/tiles/overworld_tiles.png
            "images/tiles/overworld_tiles.png"
                                         -> assets/graphics/tiles/overworld_tiles.png  (แก้ให้แล้ว)
        """
        # ใช้ key เป็น path ที่ผู้ใช้ส่งมาเดิม ๆ
        key = relative_path
        if key in self._images:
            return self._images[key]

        # ตัด prefix "assets/" ถ้ามี
        if relative_path.startswith("assets/"):
            relative_path = relative_path[len("assets/"):]

        # ตัด prefix "graphics/" ถ้ามี
        if relative_path.startswith("graphics/"):
            relative_path = relative_path[len("graphics/"):]

        # กรณีพิเศษ: images/tiles/... ให้ map ไปที่ tiles/...
        if relative_path.startswith("images/tiles/"):
            relative_path = "tiles/" + relative_path[len("images/tiles/"):]

        # ตอนนี้ relative_path อาจเป็น:
        #   - "images/xxx.png"
        #   - "tiles/xxx.png"
        #   - "player/idle_0.png" (ไม่มี prefix)
        if relative_path.startswith("images/") or relative_path.startswith("tiles/"):
            # อยู่ใต้ graphics โดยตรง
            full_path = self._resolve("graphics", relative_path)
        else:
            # ไม่มี prefix => ถือว่าเป็นไฟล์ใน graphics/images
            full_path = self._resolve("graphics", "images", relative_path)

        image = pygame.image.load(full_path).convert_alpha()
        if colorkey is not None:
            image.set_colorkey(colorkey)
        self._images[key] = image
        return image

    # ---------- Sounds ----------
    def load_sound(self, relative_path: str) -> pygame.mixer.Sound:
        """
        โหลดเสียงจาก assets/sounds/...

        relative_path ใช้ได้หลายแบบ เช่น
            "explosion.wav"      -> assets/sounds/sfx/explosion.wav
            "sfx/explosion.wav"  -> assets/sounds/sfx/explosion.wav
            "bgm/field.ogg"      -> assets/sounds/bgm/field.ogg
            "sounds/bgm/field.ogg" หรือ "assets/sounds/bgm/field.ogg" ก็ได้
        """
        if relative_path in self._sounds:
            return self._sounds[relative_path]

        path = relative_path

        # ตัด prefix "assets/" ถ้ามี
        if path.startswith("assets/"):
            path = path[len("assets/"):]

        # ตัด prefix "sounds/" ถ้ามี
        if path.startswith("sounds/"):
            path = path[len("sounds/"):]

        # ตอนนี้ path อาจเป็น:
        #   "bgm/xxx.ogg", "sfx/xxx.wav" หรือ "explosion.wav"
        if path.startswith("bgm/") or path.startswith("sfx/"):
            full_path = self._resolve("sounds", path)
        else:
            # ไม่มีโฟลเดอร์ => ใช้ sfx เป็นค่าเริ่มต้น
            full_path = self._resolve("sounds", "sfx", path)

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
            # เดิมเคยใช้ assets/fonts/<name>
            # ถ้าคุณย้ายฟอนต์ไป assets/data/fonts ให้แก้เป็น:
            # full_path = self._resolve("data", "fonts", name)
            full_path = self._resolve("fonts", name)
            font = pygame.font.Font(full_path, size)

        self._fonts[key] = font
        return font
