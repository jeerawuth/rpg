# items/equipment.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .item_base import ItemBase
from .item_database import ITEM_DB
from .inventory import Inventory, ItemStack


@dataclass
class Equipment:
    # เก็บ item_id ของไอเท็มที่ใส่อยู่ในช่องต่าง ๆ
    main_hand: Optional[str] = None    # อาวุธ (weapon)
    off_hand: Optional[str] = None     # มือรอง (จะใช้ทีหลังก็ได้)
    armor: Optional[str] = None        # เกราะ / โล่ (shield, armor)

    # ----------------- อ่านข้อมูลไอเท็มจากช่องอุปกรณ์ -----------------
    def get_item(self, slot: str) -> Optional[ItemBase]:
        """
        slot: "main_hand" | "off_hand" | "armor"
        คืน ItemBase ถ้ามีของใส่อยู่ในช่องนั้น
        """
        item_id = getattr(self, slot, None)
        if not item_id:
            return None
        return ITEM_DB.try_get(item_id)

    # ----------------- Equip จาก inventory -----------------
    def equip_from_inventory(
        self,
        inventory: Inventory,
        index: int,
        slot: str = "main_hand",
    ) -> bool:
        """
        เอาไอเท็มจาก inventory slot[index] มาใส่ในช่องอุปกรณ์ (slot)

        - slot = "main_hand"  -> ใส่ได้เฉพาะ weapon
        - slot = "armor"      -> ใส่ได้เฉพาะ armor (เช่น shield)
        - slot = "off_hand"   -> ตอนนี้ให้ตามประเภทเดียวกับ armor ไปก่อน

        คืน True ถ้าใส่สำเร็จ
        """

        # 1) ดูว่าช่อง inventory นั้นมีของไหม
        stack: ItemStack | None = inventory.get(index)
        if stack is None:
            return False

        item = stack.item  # ItemBase

        # 2) เช็ค type ตามช่องที่ใส่
        if slot == "main_hand":
            # main_hand ต้องเป็นอาวุธเท่านั้น
            if item.item_type != "weapon":
                return False
        elif slot in ("armor", "off_hand"):
            # armor / off_hand ต้องเป็น armor (เช่น shield)
            if item.item_type != "armor":
                return False
        else:
            # ยังไม่รองรับ slot แบบอื่น
            return False

        # 3) เก็บของเก่าที่ใส่อยู่ในช่องนั้น (ถ้ามี)
        old_item_id = getattr(self, slot, None)

        # 4) ใส่ของใหม่เข้าไปในช่อง
        setattr(self, slot, item.id)

        # 5) ลดจำนวนใน inventory
        stack.quantity -= 1
        if stack.quantity <= 0:
            inventory.set(index, None)

        # 6) เอาของเก่า (ถ้ามี) ย้ายกลับเข้า inventory
        if old_item_id:
            leftover = inventory.add_item(old_item_id, 1)
            if leftover > 0:
                # ถ้าใส่กลับไม่ได้จริง ๆ (กระเป๋าเต็ม) จะทิ้งก็ได้
                # ตอนนี้ปล่อยทิ้งไปเฉย ๆ
                pass

        return True
