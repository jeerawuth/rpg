# core/resource_manager.py
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
        projectile_scale: float | None = None,
        item_scale: float | None = None,
        item_scale_overrides: Dict[str, float] | None = None,
    ) -> None:
        """
        sprite_scale        : scale สำหรับตัวละคร / enemy / UI ฯลฯ
        tile_scale          : scale สำหรับ tileset (พื้น / map)
        projectile_scale    : scale สำหรับ projectiles (ลูกธนู, ลูกไฟ ฯลฯ)
        item_scale          : scale สำหรับ items (ของตกพื้น, ไอคอนในโลก)
        item_scale_overrides:
            dict สำหรับกำหนด scale ราย prefix ของ path เช่น
                {
                    "items/bow_power": 0.5,
                    "items/shield": 0.8,
                }
            จะถูกจับคู่กับ relative_path ที่เริ่มด้วย prefix นั้น
        """
        self.base_path = base_path

        self.sprite_scale = sprite_scale
        self.tile_scale = tile_scale
        self.projectile_scale = projectile_scale if projectile_scale is not None else sprite_scale
        self.item_scale = item_scale if item_scale is not None else sprite_scale
        self.item_scale_overrides = item_scale_overrides or {}

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
    # Images (sprites + tiles + projectiles + items)
    # ------------------------------------------------------------------
    def load_image(self, relative_path: str, colorkey=None) -> pygame.Surface:
        """
        relative_path ตัวอย่าง:

        - "player/idle/idle_down_01.png"
            -> assets/graphics/images/player/idle/idle_down_01.png   (sprite)

        - "tiles/overworld_tiles.png"
            -> assets/graphics/tiles/overworld_tiles.png             (tile)

        - "images/tiles/overworld_tiles.png"
            -> map อัตโนมัติไป tiles/overworld_tiles.png
               -> assets/graphics/tiles/overworld_tiles.png         (tile)

        - "projectiles/arrow_01.png"
            -> assets/graphics/images/projectiles/arrow_01.png      (projectile)

        - "items/bow_power_01.png"
            -> assets/graphics/images/items/bow_power_01.png        (item)
        """
        key = relative_path
        if key in self._images:
            return self._images[key]

        # --- Normalize path ---
        if relative_path.startswith("assets/"):
            relative_path = relative_path[len("assets/"):]

        if relative_path.startswith("graphics/"):
            relative_path = relative_path[len("graphics/"):]

        # แก้กรณี Tiled อ้าง "images/tiles/xxx"
        if relative_path.startswith("images/tiles/"):
            relative_path = "tiles/" + relative_path[len("images/tiles/"):]

        # --- Determine type ---
        is_tile = relative_path.startswith("tiles/") or "/tiles/" in relative_path
        is_projectile = relative_path.startswith("projectiles/") or "/projectiles/" in relative_path
        is_item = relative_path.startswith("items/") or "/items/" in relative_path

        # --- Choose scale ---
        if is_tile:
            scale = self.tile_scale
        elif is_projectile:
            scale = self.projectile_scale
        elif is_item:
            # เริ่มจากค่า default ของ item ทั้งหมด
            scale = self.item_scale

            # หา override ราย prefix
            for prefix, override_scale in self.item_scale_overrides.items():
                # prefix เช่น "items/bow_power" จะ match:
                #   "items/bow_power_01.png"
                if relative_path.startswith(prefix):
                    scale = override_scale
                    break
        else:
            scale = self.sprite_scale

        # --- Build full path under assets/graphics/... ---
        if relative_path.startswith("images/") or relative_path.startswith("tiles/"):
            full_path = self._resolve("graphics", relative_path)
        else:
            # ไม่มี prefix -> ถือว่าอยู่ใต้ graphics/images
            full_path = self._resolve("graphics", "images", relative_path)

        image = pygame.image.load(full_path).convert_alpha()
        if colorkey is not None:
            image.set_colorkey(colorkey)

        # apply scale
        image = self._scale_surface(image, scale)

        self._images[key] = image
        return image

    # ------------------------------------------------------------------
    # Sounds
    # ------------------------------------------------------------------
    def load_sound(self, relative_path: str) -> pygame.mixer.Sound:
        """
        relative_path เช่น "sfx/hit.wav" -> assets/sounds/sfx/hit.wav
        """
        key = relative_path
        if key in self._sounds:
            return self._sounds[key]

        # ตัด prefix assets/ ถ้ามี
        if relative_path.startswith("assets/"):
            relative_path = relative_path[len("assets/"):]

        # ตัด prefix sounds/ ถ้ามี (จะต่อเพิ่มใหม่อยู่ดี)
        if relative_path.startswith("sounds/"):
            relative_path = relative_path[len("sounds/"):]

        full_path = self._resolve("sounds", relative_path)
        sound = pygame.mixer.Sound(full_path)
        self._sounds[key] = sound
        return sound

    # ------------------------------------------------------------------
    # Fonts
    # ------------------------------------------------------------------
    def load_font(self, relative_path: Optional[str], size: int) -> pygame.font.Font:
        """
        relative_path = None -> ใช้ default font ของ pygame
        relative_path = "fonts/myfont.ttf" -> assets/data/fonts/myfont.ttf
        """
        key = (relative_path, size)
        if key in self._fonts:
            return self._fonts[key]

        if relative_path is None:
            font = pygame.font.Font(None, size)
        else:
            path = relative_path
            if path.startswith("assets/"):
                path = path[len("assets/"):]
            if path.startswith("data/"):
                path = path[len("data/"):]
            full_path = self._resolve("data", path)
            font = pygame.font.Font(full_path, size)

        self._fonts[key] = font
        return font
