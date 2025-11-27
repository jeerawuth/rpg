# items/item_database.py
from __future__ import annotations

from typing import Dict

from .item_base import ItemBase


class ItemDatabase:
    def __init__(self) -> None:
        # เก็บ item_id -> ItemBase
        self._items: Dict[str, ItemBase] = {}

        self._register_defaults()

    # ---------------- ลงทะเบียนไอเท็มเริ่มต้น ----------------
    def _register_defaults(self) -> None:
        # ตัวอย่าง potion เล็ก (เผื่อคุณใช้)
        potion_small = ItemBase(
            id="potion_small",
            name="Small Potion",
            description="ฟื้นฟู HP เล็กน้อย",
            item_type="consumable",
            max_stack=20,
            icon_key="items/potion_small.png",   # คุณค่อยไปทำรูปตาม path นี้
        )
        self._items[potion_small.id] = potion_small

        # ตัวอย่างดาบพื้นฐาน (เผื่อไว้)
        sword_basic = ItemBase(
            id="sword_basic",
            name="Basic Sword",
            description="ดาบพื้น ๆ สำหรับมือใหม่",
            item_type="weapon",
            max_stack=1,
            icon_key="items/sword_basic.png",
        )
        self._items[sword_basic.id] = sword_basic

        # 🔥 ไอเท็มเพิ่มพลังธนูที่คุณต้องการใช้
        bow_power_1 = ItemBase(
            id="bow_power_1",
            name="Bow Power Lv.1",
            description="เพิ่มพลังโจมตีของลูกธนูเล็กน้อย",
            item_type="weapon",
            max_stack=1,
            icon_key="items/bow_power_1.png",   # ไปวางรูปตาม path นี้
        )
        self._items[bow_power_1.id] = bow_power_1

    # ---------------- API ใช้งานจากที่อื่น ----------------
    def get(self, item_id: str) -> ItemBase:
        return self._items[item_id]

    def try_get(self, item_id: str):
        return self._items.get(item_id)

    def all_items(self):
        return list(self._items.values())


# singleton แบบง่าย ๆ ให้ import ใช้ได้เลย
ITEM_DB = ItemDatabase()
