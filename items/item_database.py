# items/item_database.py
from __future__ import annotations

from typing import Dict

from .item_base import ItemBase


class ItemDatabase:
    def __init__(self) -> None:
        # ตอนนี้ hardcode ไอเทมตัวอย่างไว้ก่อน
        self._items: Dict[str, ItemBase] = {}

        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(
            ItemBase(
                id="potion_small",
                name="Small Potion",
                description="Restore a small amount of HP.",
                item_type="consumable",
                max_stack=10,
            )
        )
        self.register(
            ItemBase(
                id="sword_basic",
                name="Rusty Sword",
                description="A basic, rusty sword. Better than nothing.",
                item_type="weapon",
                max_stack=1,
            )
        )
        self.register(
            ItemBase(
                id="sword_iron",
                name="Iron Sword",
                description="A solid iron sword. Deals more damage.",
                item_type="weapon",
                max_stack=1,
            )
        )

    # ---------- CRUD ----------
    def register(self, item: ItemBase) -> None:
        self._items[item.id] = item

    def get(self, item_id: str) -> ItemBase:
        return self._items[item_id]

    def try_get(self, item_id: str):
        return self._items.get(item_id)

    def all_items(self):
        return list(self._items.values())


# singleton แบบง่าย ๆ ให้ import ใช้ได้เลย
ITEM_DB = ItemDatabase()
