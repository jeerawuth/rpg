# world/tilemap.py
"""
| index | ความหมาย           | mapping ที่คุณตั้ง      |
| ----: | ------------------ | ------------------ |
|     0 | พื้นด้านบน (top)      | 1                  |
|     1 | ด้านข้างกำแพง (front)| 2                  |
|     2 | ขอบเฉียงซ้ายบน       | 3                  |
|     3 | ขอบเฉียงขวาบน       | 4                  |
|     4 | บล็อกเต็ม / เงาอื่น ๆ  | 5 (เผื่อใช้ต่อ)        |
"""

from __future__ import annotations

from typing import List

import pygame

from .level_data import LevelData
from core.resource_manager import ResourceManager


class TileMap:
    def __init__(self, level_data: LevelData, resources: ResourceManager) -> None:
        self.level_data = level_data
        self.resources = resources

        self.tile_size = level_data.tile_size
        self.width = level_data.width
        self.height = level_data.height

        # ✅ เพิ่มสองบรรทัดนี้สำหรับกล้อง
        self.pixel_width = self.width * self.tile_size
        self.pixel_height = self.height * self.tile_size

        # โหลด tileset: assets/graphics/tiles/<tileset>
        self.tileset = self.resources.load_image(
            f"tiles/{level_data.tileset}"
        )

        self.tiles_per_row = self.tileset.get_width() // self.tile_size
        self.tiles_per_col = self.tileset.get_height() // self.tile_size
        self.num_tiles = self.tiles_per_row * self.tiles_per_col

        # surface ของ map ทั้งแผ่น
        self.surface = pygame.Surface(
            (self.width * self.tile_size, self.height * self.tile_size),
            pygame.SRCALPHA,
        )

        # rect สำหรับชน
        self.collision_rects: List[pygame.Rect] = []

        self._build()

    # ---------- internal ----------
    def _get_tile_image(self, tile_index: int) -> pygame.Surface | None:
        """
        tile_index: 0-based
        - ถ้า index น้อยกว่า 0 หรือมากเกินจำนวน tile จะ fallback ไป tile 0
          หรือ return None ถ้าไม่มี tile เลย
        """
        if self.num_tiles <= 0:
            return None

        if tile_index < 0 or tile_index >= self.num_tiles:
            # ป้องกัน error: ใช้ tile แรกแทน
            tile_index = 0

        col = tile_index % self.tiles_per_row
        row = tile_index // self.tiles_per_row
        x = col * self.tile_size
        y = row * self.tile_size
        rect = pygame.Rect(x, y, self.tile_size, self.tile_size)
        return self.tileset.subsurface(rect)

    def _build_layer(self, layer_name: str) -> None:
        grid = self.level_data.layers.get(layer_name)
        if not grid:
            return

        for y, row in enumerate(grid):
            for x, value in enumerate(row):
                # convention:
                #   < 0  = ช่องว่าง ไม่วาด
                #   >= 0 = index ของ tile (0-based)
                if value < 0:
                    continue

                tile_image = self._get_tile_image(value)
                if tile_image is None:
                    continue

                self.surface.blit(
                    tile_image, (x * self.tile_size, y * self.tile_size)
                )

    def _build_collision(self) -> None:
        grid = self.level_data.layers.get("collision")
        if not grid:
            return

        for y, row in enumerate(grid):
            for x, value in enumerate(row):
                if value == 0:
                    continue
                rect = pygame.Rect(
                    x * self.tile_size,
                    y * self.tile_size,
                    self.tile_size,
                    self.tile_size,
                )
                self.collision_rects.append(rect)

    def _build(self) -> None:
        # วาด layer "ground" (ถ้าอยากมี layer อื่นก็เรียกเพิ่ม)
        self._build_layer("ground")
        self._build_collision()

    # ---------- public ----------
    def draw(
        self,
        surface: pygame.Surface,
        camera_offset: pygame.Vector2 | None = None,
    ) -> None:
        if camera_offset is None:
            camera_offset = pygame.Vector2(0, 0)

        surface.blit(self.surface, (-camera_offset.x, -camera_offset.y))
