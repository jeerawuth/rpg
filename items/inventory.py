# items/inventory.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .item_base import ItemBase
from .item_database import ITEM_DB


@dataclass
class ItemStack:
    item_id: str
    quantity: int = 1

    @property
    def item(self) -> ItemBase:
        return ITEM_DB.get(self.item_id)


class Inventory:
    def __init__(self, size: int = 20) -> None:
        self.size = size
        self.slots: List[Optional[ItemStack]] = [None] * size

    # ---------- Helpers ----------
    def get(self, index: int) -> Optional[ItemStack]:
        if 0 <= index < self.size:
            return self.slots[index]
        return None

    def set(self, index: int, stack: Optional[ItemStack]) -> None:
        if 0 <= index < self.size:
            self.slots[index] = stack

    def swap(self, i: int, j: int) -> None:
        if 0 <= i < self.size and 0 <= j < self.size:
            self.slots[i], self.slots[j] = self.slots[j], self.slots[i]

    # ---------- Add / Remove ----------
    def add_item(self, item_id: str, amount: int = 1) -> int:
        """
        เพิ่ม item เข้ากระเป๋า
        return: จำนวนที่ "เหลือเพิ่มไม่ได้" (0 = เพิ่มได้ครบ)
        """
        item = ITEM_DB.get(item_id)
        remaining = amount

        # 1) เติมใน stack เดิมก่อน
        for stack in self.slots:
            if remaining <= 0:
                break
            if stack is None:
                continue
            if stack.item_id != item_id:
                continue
            # stack เดิม + ของใหม่
            space = item.max_stack - stack.quantity
            if space <= 0:
                continue
            add = min(space, remaining)
            stack.quantity += add
            remaining -= add

        # 2) สร้าง stack ใหม่ลงช่องว่าง
        for idx, stack in enumerate(self.slots):
            if remaining <= 0:
                break
            if stack is not None:
                continue
            add = min(item.max_stack, remaining)
            self.slots[idx] = ItemStack(item_id=item_id, quantity=add)
            remaining -= add

        return remaining

    def remove_item(self, item_id: str, amount: int = 1) -> int:
        """
        ลบ item ออกจากกระเป๋า
        return: จำนวนที่ "ลบไม่สำเร็จเพราะไม่พอ" (0 = ลบได้ครบ)
        """
        remaining = amount
        for idx, stack in enumerate(self.slots):
            if remaining <= 0:
                break
            if stack is None or stack.item_id != item_id:
                continue
            if stack.quantity > remaining:
                stack.quantity -= remaining
                remaining = 0
            else:
                remaining -= stack.quantity
                self.slots[idx] = None
        return remaining

    def first_non_empty_index(self) -> int:
        for i, stack in enumerate(self.slots):
            if stack is not None:
                return i
        return -1
