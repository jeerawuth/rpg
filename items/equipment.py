# items/equipment.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .item_base import ItemBase
from .item_database import ITEM_DB
from .inventory import Inventory, ItemStack


@dataclass
class Equipment:
    main_hand: Optional[str] = None    # item_id ของ weapon
    off_hand: Optional[str] = None
    armor: Optional[str] = None

    def get_item(self, slot: str) -> Optional[ItemBase]:
        item_id = getattr(self, slot, None)
        if not item_id:
            return None
        return ITEM_DB.try_get(item_id)

    # ---------- Equip from inventory ----------
    def equip_from_inventory(self, inventory: Inventory, index: int, slot: str = "main_hand") -> bool:
        """
        เอาไอเทมจาก inventory slot index มาใส่ในช่องอุปกรณ์ (slot)
        - ถ้าเป็น weapon และเป็น type ถูกต้อง ก็ equip ได้
        - ถ้ามีของเดิมในช่อง equipment จะถูกย้ายกลับลง inventory (ถ้าใส่ได้)
        """
        stack = inventory.get(index)
        if stack is None:
            return False

        item = stack.item
        if item.item_type != "weapon" and slot == "main_hand":
            # ตอนนี้รองรับ equip weapon ก่อน
            return False

        # ของเดิมที่ใส่อยู่ (ถ้ามี)
        old_item_id = getattr(self, slot, None)

        # ใส่ของใหม่
        setattr(self, slot, item.id)

        # ลดจำนวนใน slot ของ inventory
        stack.quantity -= 1
        if stack.quantity <= 0:
            inventory.set(index, None)

        # เอาของเดิมกลับลง inventory ถ้ามี
        if old_item_id:
            leftover = inventory.add_item(old_item_id, 1)
            if leftover > 0:
                # ถ้าใส่กลับไม่ได้จริง ๆ ก็ถือว่าของเก่าหายไป (หรือจะ drop ลงพื้นก็ได้)
                pass

        return True
