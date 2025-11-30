# items/item_base.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

ItemType = Literal["weapon", "armor", "consumable", "misc"]


@dataclass(frozen=True)
class ItemBase:
    id: str
    name: str
    description: str
    item_type: ItemType = "misc"
    max_stack: int = 99
    icon_key: Optional[str] = None   # เอาไว้ผูกกับ resource manager ทีหลัง

    # ---------- สำหรับไอเท็มแบบใช้ทันที / ฟื้น HP ----------
    heal_amount: int = 0             # ถ้า > 0 แปลว่าไอเท็มนี้ฟื้น HP เท่านี้ต่อ 1 ชิ้น
    use_on_pickup: bool = False      # True = ใช้ทันทีเมื่อเก็บ (ไม่เข้า inventory)
