# core/resource_manager.py
# โหลด/แคชภาพและเสียง + รองรับการ scale sprite / tile

from __future__ import annotations

import os
from typing import Dict, Tuple, Optional

import pygame


class ResourceManager:
    def __init__(
        self,
        base_path: str = "assets",
        sprite_scale: float = 1.0,
        tile_scale: float = 1.0,
        projectile_scale: float | None = None,   # 👈 เพิ่มตรงนี้
    ) -> None:
        """
        sprite_scale     : scale สำหรับตัวละคร / enemy / UI ฯลฯ
        tile_scale       : scale สำหรับ tileset (พื้น / map)
        projectile_scale : scale สำหรับ projectiles (เช่น ธนู)
                           ถ้าไม่กำหนด (None) จะใช้ค่าเดียวกับ sprite_scale
        """
        self.base_path = base_path
        self.sprite_scale = sprite_scale
        self.tile_scale = tile_scale
        self.projectile_scale = projectile_scale if projectile_scale is not None else sprite_scale

        self._images: Dict[str, pygame.Surface] = {}
        self._sounds: Dict[str, pygame.mixer.Sound] = {}
        self._fonts: Dict[Tuple[Optional[str], int], pygame.font.Font] = {}

    # ------------------------------------------------------------------
    # Utils
    # ------------------------------------------------------------------
    def _resolve(self, *parts: str) -> str:
        return os.path.join(self.base_path, *parts)

    def _scale_surface(self, surf: pygame.Surface, scale: float) -> pygame.Surface:
        if scale == 1.0:
            return surf
        w, h = surf.get_size()
        new_size = (int(w * scale), int(h * scale))
        if new_size[0] <= 0 or new_size[1] <= 0:
            return surf
        return pygame.transform.smoothscale(surf, new_size)

    # ------------------------------------------------------------------
    # Images (sprites + tiles + projectiles)
    # ------------------------------------------------------------------
    def load_image(self, relative_path: str, colorkey=None) -> pygame.Surface:
        """
        relative_path ใช้ได้หลายแบบ เช่น

        - "player/idle/idle_down_01.png"
            -> assets/graphics/images/player/idle/idle_down_01.png  (sprite)

        - "tiles/overworld_tiles.png"
            -> assets/graphics/tiles/overworld_tiles.png            (tile)

        - "images/tiles/overworld_tiles.png"
            -> map อัตโนมัติไป tiles/overworld_tiles.png
               -> assets/graphics/tiles/overworld_tiles.png        (tile)

        - "projectiles/arrow_01.png"
            -> assets/graphics/images/projectiles/arrow_01.png     (projectile)
        """
        key = relative_path
        if key in self._images:
            return self._images[key]

        # ตัด prefix "assets/" ถ้ามี
        if relative_path.startswith("assets/"):
            relative_path = relative_path[len("assets/"):]

        # ตัด prefix "graphics/" ถ้ามี
        if relative_path.startswith("graphics/"):
            relative_path = relative_path[len("graphics/"):]

        # แก้กรณี Tiled อ้าง "images/tiles/xxx"
        if relative_path.startswith("images/tiles/"):
            relative_path = "tiles/" + relative_path[len("images/tiles/"):]

        # --- เลือก scale ตามประเภทไฟล์ ---
        is_tile = relative_path.startswith("tiles/") or "/tiles/" in relative_path
        is_projectile = relative_path.startswith("projectiles/") or "/projectiles/" in relative_path

        if is_tile:
            scale = self.tile_scale
        elif is_projectile:
            scale = self.projectile_scale
        else:
            scale = self.sprite_scale

        # สร้าง full_path ใต้ assets/graphics/...
        if relative_path.startswith("images/") or relative_path.startswith("tiles/"):
            full_path = self._resolve("graphics", relative_path)
        else:
            # ไม่มี prefix => ถือว่าอยู่ใต้ graphics/images
            full_path = self._resolve("graphics", "images", relative_path)

        image = pygame.image.load(full_path).convert_alpha()
        if colorkey is not None:
            image.set_colorkey(colorkey)

        # scale ตามประเภทที่เลือกด้านบน
        image = self._scale_surface(image, scale)

        self._images[key] = image
        return image

    # ... (ส่วน load_sound / load_font เดิมของคุณอยู่ต่อด้านล่างเหมือนเดิม) ...


    # ------------------------------------------------------------------
    # Sounds
    # ------------------------------------------------------------------
    def load_sound(self, relative_path: str) -> pygame.mixer.Sound:
        """
        โหลดเสียงจาก assets/sounds/...

        relative_path ตัวอย่าง:
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

    # ------------------------------------------------------------------
    # Fonts
    # ------------------------------------------------------------------
    def load_font(self, size: int, name: Optional[str] = None) -> pygame.font.Font:
        key = (name, size)
        if key in self._fonts:
            return self._fonts[key]

        if name is None:
            font = pygame.font.Font(None, size)
        else:
            # ถ้าคุณย้ายฟอนต์ไป assets/data/fonts ให้แก้บรรทัดนี้
            # full_path = self._resolve("data", "fonts", name)
            full_path = self._resolve("fonts", name)
            font = pygame.font.Font(full_path, size)

        self._fonts[key] = font
        return font
