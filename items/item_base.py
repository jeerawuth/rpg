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
