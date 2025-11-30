# items/item_database.py
from __future__ import annotations

from typing import Dict, Iterable

from .item_base import ItemBase


class ItemDatabase:
    """
    เก็บข้อมูลชนิดไอเท็มทั้งหมดในเกม (ไม่ใช่ instance ที่ผู้เล่นถือ)
    อ้างอิงด้วย item_id เช่น "potion_small", "bow_power_1", "shield"
    """

    def __init__(self) -> None:
        self._items: Dict[str, ItemBase] = {}
        self._register_defaults()

    # ------------------------------------------------------------------
    # ลงทะเบียนไอเท็มเริ่มต้น
    # ------------------------------------------------------------------
    def _register_defaults(self) -> None:
        """
        เพิ่ม/ลบไอเท็มเริ่มต้นของเกมได้ในฟังก์ชันนี้
        """

        # ---------- Consumable ----------
        self._register(
            ItemBase(
                id="potion_small",
                name="Small Potion",
                description="ยาฟื้นฟู HP ปริมาณเล็กน้อย",
                item_type="consumable",
                max_stack=20,
                icon_key="items/potion_small_01.png",

                # ใช้ค่าพวกนี้สำหรับเอฟเฟกต์ใน ItemNode
                heal_amount=50,        # ฟื้น HP 50 ต่อ 1 ชิ้น
                use_on_pickup=True,    # เก็บแล้วใช้ทันที (ไม่เข้า inventory)
            )
        )


        # ---------- Weapons ----------
        # ดาบพื้นฐาน
        self._register(
            ItemBase(
                id="sword_basic",
                name="Basic Sword",
                description="ดาบพื้นฐานสำหรับมือใหม่",
                item_type="weapon",
                max_stack=1,
                icon_key="items/sword_basic.png",
            )
        )

        # ไอเท็มเพิ่มพลังโจมตีธนู (เวอร์ชันที่คุณใช้คือ bow_power_1)
        # แนะนำให้มีไฟล์:
        #   assets/graphics/images/items/bow_power_01.png
        #   assets/graphics/images/items/bow_power_02.png
        self._register(
            ItemBase(
                id="bow_power_1",  # 👈 ให้ตรงกับที่ GameScene ใช้
                name="Bow Power Lv.1",
                description="เพิ่มพลังโจมตีของลูกธนู",
                item_type="weapon",
                max_stack=1,
                icon_key="items/bow_power_01.png",  # เฟรมแรกของอนิเมชัน
            )
        )

        # ---------- Shield / Armor ----------
        # ไอเท็มโล่
        # แนะนำไฟล์:
        #   assets/graphics/images/items/shield_01.png
        #   assets/graphics/images/items/shield_02.png
        self._register(
            ItemBase(
                id="shield",
                name="Wooden Shield",
                description="โล่ไม้สำหรับป้องกัน",
                item_type="armor",
                max_stack=1,
                icon_key="items/shield_01.png",
            )
        )



    # ------------------------------------------------------------------
    # ฟังก์ชันช่วยภายใน
    # ------------------------------------------------------------------
    def _register(self, item: ItemBase) -> None:
        if item.id in self._items:
            raise ValueError(f"Duplicate item id: {item.id}")
        self._items[item.id] = item

    # ------------------------------------------------------------------
    # API ให้ที่อื่นเรียกใช้
    # ------------------------------------------------------------------
    def get(self, item_id: str) -> ItemBase:
        """ดึง ItemBase ตาม id (ไม่เจอจะ KeyError)"""
        return self._items[item_id]

    def try_get(self, item_id: str) -> ItemBase | None:
        """ดึง ItemBase แบบไม่โยน error ถ้าไม่เจอ"""
        return self._items.get(item_id)

    def all_items(self) -> Iterable[ItemBase]:
        """คืน list/iter ของไอเท็มทั้งหมด (ใช้ debug / UI แสดงรายการ)"""
        return self._items.values()


# singleton ให้ import ใช้สะดวก
ITEM_DB = ItemDatabase()
