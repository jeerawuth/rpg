# entities/item_node.py
from __future__ import annotations

import math
import pygame

from .node_base import NodeBase
from items.item_database import ITEM_DB


class ItemNode(NodeBase):
    """
    โหนดไอเท็มที่วางอยู่บนพื้น
    - มี item_id + จำนวน (amount)
    - เดินชนแล้วจะเก็บเข้า inventory
    """

    def __init__(
        self,
        game,
        pos: tuple[int, int],
        item_id: str,
        amount: int = 1,
        *groups,
    ) -> None:
        super().__init__(*groups)

        self.game = game
        self.item_id = item_id
        self.amount = amount

        # โหลดข้อมูล item จากฐานข้อมูล
        self.item = ITEM_DB.get(item_id)

        # โหลดรูปจาก ResourceManager ตาม icon_key หรือ fallback จากชื่อไอเท็ม
        self._load_graphics(pos)

        # ทำให้ลอยดึ๋ง ๆ
        self._bob_time = 0.0
        self._base_y = float(self.rect.y)

    def _load_graphics(self, pos: tuple[int, int]) -> None:
        """
        สมมติว่าใน ItemBase.icon_key เก็บ path แบบ relative ของ sprite ไว้ เช่น:
            icon_key = "items/bow_power_01.png"

        ถ้า icon_key ว่าง จะลองใช้ "items/{item_id}.png" แทน
        """
        if self.item.icon_key:
            rel_path = self.item.icon_key   # เช่น "items/bow_power_01.png"
        else:
            rel_path = f"items/{self.item_id}.png"

        try:
            image = self.game.resources.load_image(rel_path)
        except Exception:
            # ถ้ายังไม่มีไฟล์ภาพ ก็ใช้ placeholder แทน
            image = pygame.Surface((24, 24), pygame.SRCALPHA)
            pygame.draw.circle(image, (255, 215, 0), (12, 12), 10)

        self.image = image
        self.rect = self.image.get_rect(center=pos)

    def update(self, dt: float) -> None:
        """
        ทำ animation ให้ไอเท็มลอยขึ้นลงเล็กน้อย
        """
        self._bob_time += dt
        offset = math.sin(self._bob_time * 3.0) * 3  # ปรับสปีด/ระยะได้
        self.rect.y = int(self._base_y + offset)
