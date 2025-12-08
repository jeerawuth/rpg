# world/tilemap.py
"""
TileMap แบบหลายเลเยอร์ + รองรับกล้อง + มี collision_rects

| index | ความหมาย           | mapping ที่คุณตั้ง      |
| ----: | ------------------ | ------------------------ |
|     0 | พื้นด้านบน (top)      | 1                      |
|     1 | ด้านข้างกำแพง (front)| 2                      |
|     2 | ขอบเฉียงซ้ายบน       | 3                      |
|     3 | ขอบเฉียงขวาบน       | 4                      |
|     4 | บล็อกเต็ม / เงาอื่น ๆ  | 5 (เผื่อใช้ต่อ)        |

convention:
- ใน level_data.layers["ชื่อเลเยอร์"] จะเก็บเป็น grid 2D:
    < 0  = ช่องว่าง ไม่วาด
    >= 0 = index ของ tile (0-based) ใน tileset
- layer "collision" ใช้ 0 = ว่าง, >0 = มี collision
"""

from __future__ import annotations

from typing import List

import pygame

from .level_data import LevelData
from core.resource_manager import ResourceManager


class TileMap:
    """
    จัดการวาด tilemap จาก LevelData + ResourceManager

    รองรับเลเยอร์หลายแบบ เช่น:
    - ground     : พื้นหลัก
    - detail     : รายละเอียดพื้น/ขอบ/เงา
    - decor      : ของตกแต่งเล็ก ๆ
    - foreground : ของที่อยู่หน้าตัวละคร (จะมีเมธอด draw_foreground แยก)
    - collision  : ใช้ชนอย่างเดียว ไม่วาด
    """

    # ลำดับการวาดเลเยอร์หลัก (จากหลังมาหน้า)
    DEFAULT_DRAW_ORDER = ["ground", "detail", "decor"]

    def __init__(self, level_data: LevelData, resources: ResourceManager) -> None:
        self.level_data = level_data
        self.resources = resources

        self.tile_size = level_data.tile_size

        # ใช้ขนาดจากเลเยอร์จริง (ถ้ามี ground) เพื่อกัน bug height/width ไม่ตรง JSON
        ref_grid = level_data.layers.get("ground")
        if ref_grid:
            self.height = len(ref_grid)
            self.width = len(ref_grid[0]) if ref_grid[0] else level_data.width
        else:
            self.width = level_data.width
            self.height = level_data.height

        # ขนาด world เป็นพิกเซล (ใช้กับ camera)
        self.pixel_width = self.width * self.tile_size
        self.pixel_height = self.height * self.tile_size

        # โหลด tileset: assets/graphics/tiles/<tileset>
        self.tileset: pygame.Surface = self.resources.load_image(
            f"tiles/{level_data.tileset}"
        )

        self.tiles_per_row = self.tileset.get_width() // self.tile_size
        self.tiles_per_col = self.tileset.get_height() // self.tile_size
        self.num_tiles = self.tiles_per_row * self.tiles_per_col

        # surface ของ map ทั้งแผ่น (เพื่อความเข้ากันได้กับโค้ดเก่า)
        self.surface = pygame.Surface(
            (self.pixel_width, self.pixel_height),
            pygame.SRCALPHA,
        )

        # rect สำหรับชน (แบบเดิม)
        self.collision_rects: List[pygame.Rect] = []

        # เส้น boundary สำหรับชนแบบ circle vs segment
        # list[tuple[pygame.Vector2, pygame.Vector2]]
        self.collision_segments: list[tuple[pygame.Vector2, pygame.Vector2]] = []

        # เก็บ reference ไปที่เลเยอร์ทั้งหมด
        self.layers = self.level_data.layers


        # สร้างลิสต์ลำดับการวาดจาก DEFAULT_DRAW_ORDER + เลเยอร์อื่น ๆ
        self.draw_order: List[str] = []
        for name in self.DEFAULT_DRAW_ORDER:
            if name in self.layers:
                self.draw_order.append(name)

        # เลเยอร์อื่นที่ไม่ใช่ collision / foreground และยังไม่อยู่ใน draw_order
        for name in self.layers.keys():
            if name not in self.draw_order and name not in ("collision", "foreground"):
                self.draw_order.append(name)

        # build พื้นฐาน (สร้างพื้นลง surface + collision_rects)
        self._build()

    # ---------- internal helpers ----------

    def _get_tile_image(self, tile_index: int) -> pygame.Surface | None:
        """
        tile_index: 0-based
        - ถ้า index น้อยกว่า 0 หรือมากเกินจำนวน tile จะ fallback ไป tile 0
          หรือ return None ถ้าไม่มี tile เลย
        """
        if self.num_tiles <= 0:
            return None

        if tile_index < 0 or tile_index >= self.num_tiles:
            # ป้องกัน index เกิน: ใช้ tile แรกแทน
            tile_index = 0

        col = tile_index % self.tiles_per_row
        row = tile_index // self.tiles_per_row
        x = col * self.tile_size
        y = row * self.tile_size
        rect = pygame.Rect(x, y, self.tile_size, self.tile_size)
        return self.tileset.subsurface(rect)

    def _build_layer_to_surface(self, layer_name: str) -> None:
        """
        วาดทั้งเลเยอร์ลง self.surface (ใช้ครั้งเดียวตอน _build)
        """
        grid = self.layers.get(layer_name)
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

                self.surface.blit(tile_image, (x * self.tile_size, y * self.tile_size))

    def _draw_layer(
        self,
        surface: pygame.Surface,
        layer_name: str,
        camera_offset: pygame.Vector2 | None = None,
    ) -> None:
        """
        วาดเลเยอร์ชื่อ layer_name ลงบน surface ตามตำแหน่งกล้อง (camera_offset)
        """
        grid = self.layers.get(layer_name)
        if not grid:
            return

        if camera_offset is None:
            camera_offset = pygame.Vector2(0, 0)

        tile_size = self.tile_size

        # ใช้ขนาดจริงของเลเยอร์นี้ (กัน list index out of range)
        map_height = len(grid)
        map_width = len(grid[0]) if map_height > 0 else 0

        screen_w, screen_h = surface.get_size()

        # คำนวณช่วง tile ที่มองเห็น (เพื่อไม่ให้ loop ทั้งแผนที่ทุกเฟรม)
        start_x = max(int(camera_offset.x // tile_size), 0)
        start_y = max(int(camera_offset.y // tile_size), 0)
        end_x = min(int((camera_offset.x + screen_w) // tile_size) + 1, map_width)
        end_y = min(int((camera_offset.y + screen_h) // tile_size) + 1, map_height)

        for y in range(start_y, end_y):
            row = grid[y]
            
            for x in range(start_x, end_x):
                value = row[x]

                if value < 0:
                    continue

                tile_image = self._get_tile_image(value)
                if tile_image is None:
                    continue

                draw_x = x * tile_size - camera_offset.x
                draw_y = y * tile_size - camera_offset.y

                surface.blit(tile_image, (draw_x, draw_y))

    # จัดการกับการชน ทั้ง rect และ segment
    def _build_collision(self) -> None:
        self.collision_rects.clear()
        self.collision_segments.clear()

        grid = self.layers.get("collision")
        if not grid:
            return

        height_c = len(grid)
        width_c = len(grid[0]) if height_c > 0 else 0

        # ----- คำนวณขนาด cell ของ collision จากขนาดแมพจริง -----
        # self.width, self.height คือจำนวน tile ของ art (64x36)
        # self.tile_size คือขนาด tile ของ art (16)
        map_pixel_w = self.width * self.tile_size
        map_pixel_h = self.height * self.tile_size

        cell_w = map_pixel_w / width_c    # ถ้า collision 128 ช่อง → 1024/128 = 8
        cell_h = map_pixel_h / height_c   # 576/72 = 8 (ควรเท่ากัน)

        # ถ้าคุณแน่ใจว่า cell เป็นสี่เหลี่ยมจัตุรัสก็ใช้ตัวเดียวได้
        cell_size = cell_w  # หรือ min(cell_w, cell_h)

        # ---------- 1) (optional) สร้าง rect สำหรับระบบอื่น ----------
        for y, row in enumerate(grid):
            for x, value in enumerate(row):
                if value == 0:
                    continue
                rect = pygame.Rect(
                    int(x * cell_size),
                    int(y * cell_size),
                    int(cell_size),
                    int(cell_size),
                )
                self.collision_rects.append(rect)

        # ---------- 2) marching-squares เพื่อสร้าง segments ----------
        def corner_value(cx: int, cy: int) -> int:
            if 0 <= cy < height_c and 0 <= cx < width_c:
                return 1 if grid[cy][cx] != 0 else 0
            return 0

        segments: list[tuple[pygame.Vector2, pygame.Vector2]] = []

        for y in range(height_c):
            for x in range(width_c):
                v0 = corner_value(x,     y)
                v1 = corner_value(x + 1, y)
                v2 = corner_value(x + 1, y + 1)
                v3 = corner_value(x,     y + 1)

                pts: list[tuple[int, pygame.Vector2]] = []

                bx = x * cell_size
                by = y * cell_size

                # ขอบบน (0)
                if v0 != v1:
                    pts.append((0, pygame.Vector2(bx + cell_size / 2, by)))
                # ขอบขวา (1)
                if v1 != v2:
                    pts.append((1, pygame.Vector2(bx + cell_size, by + cell_size / 2)))
                # ขอบล่าง (2)
                if v2 != v3:
                    pts.append((2, pygame.Vector2(bx + cell_size / 2, by + cell_size)))
                # ขอบซ้าย (3)
                if v3 != v0:
                    pts.append((3, pygame.Vector2(bx, by + cell_size / 2)))

                if not pts:
                    continue

                pts.sort(key=lambda item: item[0])
                pts_only = [p for _, p in pts]

                if len(pts_only) == 2:
                    segments.append((pts_only[0], pts_only[1]))
                elif len(pts_only) == 4:
                    segments.append((pts_only[0], pts_only[1]))
                    segments.append((pts_only[2], pts_only[3]))

        self.collision_segments = segments



    def _build(self) -> None:
        """
        ทำงานครั้งเดียวตอนสร้าง TileMap
        - วาด layer "ground" ลง self.surface (เพื่อความเข้ากันได้กับโค้ดเดิม)
        - สร้าง collision_rects
        """
        if "ground" in self.layers:
            self._build_layer_to_surface("ground")
        self._build_collision()

    # ---------- public API ----------

    def draw(
        self,
        surface: pygame.Surface,
        camera_offset: pygame.Vector2 | None = None,
    ) -> None:
        """
        วาดเลเยอร์หลักทั้งหมด (ยกเว้น foreground / collision)
        """
        if camera_offset is None:
            camera_offset = pygame.Vector2(0, 0)

        for layer_name in self.draw_order:
            self._draw_layer(surface, layer_name, camera_offset)

    def draw_foreground(
        self,
        surface: pygame.Surface,
        camera_offset: pygame.Vector2 | None = None,
    ) -> None:
        """
        วาดเลเยอร์ foreground (ถ้ามี) ให้อยู่หน้าตัวละคร
        ให้เรียกจาก GameScene.draw() หลังวาด sprite เสร็จ
        """
        if camera_offset is None:
            camera_offset = pygame.Vector2(0, 0)

        if "foreground" in self.layers:
            self._draw_layer(surface, "foreground", camera_offset)

    def get_world_size(self) -> tuple[int, int]:
        """
        คืนค่า (pixel_width, pixel_height) ของทั้งแผนที่
        """
        return self.pixel_width, self.pixel_height
