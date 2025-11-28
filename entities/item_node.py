# entities/item_node.py
from __future__ import annotations

import math
import os
from typing import List

import pygame

from .animated_node import AnimatedNode
from items.item_database import ITEM_DB
from items.item_base import ItemBase


class ItemNode(AnimatedNode):
    """
    โหนดไอเท็มที่วางอยู่บนพื้น (มีแอนิเมชัน + ลอยดึ๋ง ๆ)

    - รองรับหลายชนิดไอเท็ม เช่น bow_power, shield ฯลฯ
    - โหลดเฟรมตามแพทเทิร์น:

        items/<base_key>_01.png
        items/<base_key>_02.png
        ...

      เช่น:
        bow_power -> items/bow_power_01.png, bow_power_02.png, ...
        shield    -> items/shield_01.png,   shield_02.png,   ...
    """

    def __init__(
        self,
        game,
        pos: tuple[int, int],
        item_id: str,
        amount: int = 1,
        *groups,
    ) -> None:
        # ยังไม่เรียก super() เพราะต้องเตรียม frames ก่อน
        self.game = game
        self.item_id = item_id
        self.amount = amount

        # ข้อมูลชนิดไอเท็มจากฐานข้อมูล
        self.item: ItemBase = ITEM_DB.get(item_id)

        # โหลดเฟรมแอนิเมชันจากไฟล์
        frames = self._load_animation_frames()
        if not frames:
            # ถ้าไม่มีเฟรมจริงเลย -> ใช้ icon หรือ placeholder
            frames = [self._load_icon_or_placeholder()]

        # ความเร็วแอนิเมชัน (วินาทีต่อเฟรม)
        frame_duration = 0.12
        loop = True

        # เรียก AnimatedNode ให้จัดการระบบแอนิเมชัน
        super().__init__(frames, frame_duration, loop, *groups)

        # ตั้งตำแหน่งเริ่มต้นของไอเท็มบนพื้น
        self.rect.center = pos

        # สำหรับเอฟเฟกต์ลอยขึ้นลง
        self._bob_time = 0.0
        self._base_y = float(self.rect.y)

    # ------------------------------------------------------------------
    # หา base_key สำหรับโหลดชุดเฟรมตามชนิดไอเท็ม
    # ------------------------------------------------------------------

    def _get_animation_base_key(self) -> str:
        """
        ลำดับการหา base_key:

        1) ถ้า ItemBase มี field animation_key -> ใช้อันนี้ก่อน
        2) ถ้าไม่มี แต่มี icon_key = "items/bow_power_01.png"
           -> ตัดนามสกุล + ตัด suffix "_NN" ทิ้ง -> "bow_power"
        3) ถ้าไม่มีอะไรเลย -> ใช้ item_id ตรง ๆ

        base_key จะถูกใช้ใน pattern:

            items/<base_key>_01.png
            items/<base_key>_02.png
            ...
        """
        # 1) animation_key (ถ้ามีใน ItemBase)
        base_key = getattr(self.item, "animation_key", None)
        if base_key:
            return base_key

        # 2) จาก icon_key
        icon_key = getattr(self.item, "icon_key", "") or ""
        if icon_key:
            filename = os.path.basename(icon_key)        # "bow_power_01.png"
            name_no_ext, _ = os.path.splitext(filename)  # "bow_power_01"

            # ถ้าชื่อจบด้วย "_NN" (NN = ตัวเลข 2 หลัก) -> ตัดออก เช่น "bow_power_01" -> "bow_power"
            parts = name_no_ext.rsplit("_", 1)
            if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 2:
                return parts[0]  # "bow_power"
            else:
                return name_no_ext

        # 3) fallback: ใช้ item_id
        return self.item_id


    # ------------------------------------------------------------------
    # โหลดเฟรมตามแพทเทิร์น items/<base_key>_NN.png
    # ------------------------------------------------------------------
    def _load_animation_frames(self) -> List[pygame.Surface]:
        frames: List[pygame.Surface] = []
        resources = self.game.resources

        base_key = self._get_animation_base_key()
        index = 1

        while True:
            rel_path = f"items/{base_key}_{index:02d}.png"
            try:
                surf = resources.load_image(rel_path)
            except Exception:
                break
            else:
                frames.append(surf)
                index += 1

        return frames

    # ------------------------------------------------------------------
    # fallback: ใช้ icon_key หรือ placeholder 1 รูป
    # ------------------------------------------------------------------
    def _load_icon_or_placeholder(self) -> pygame.Surface:
        """
        ถ้าไม่มีไฟล์แอนิเมชัน:
            - ลองใช้ icon_key จาก ItemBase
            - ถ้าโหลดไม่ได้ -> ใช้ placeholder เป็นเหรียญทอง
        """
        resources = self.game.resources
        icon_key = getattr(self.item, "icon_key", "") or ""

        if icon_key:
            try:
                return resources.load_image(icon_key)
            except Exception:
                pass

        # placeholder: วงกลมทอง
        surf = pygame.Surface((24, 24), pygame.SRCALPHA)
        pygame.draw.circle(surf, (255, 215, 0), (12, 12), 10)
        return surf

    # ------------------------------------------------------------------
    # UPDATE: ลอยดึ๋ง ๆ + ให้ AnimatedNode เปลี่ยนเฟรม
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        # ลอยขึ้นลงนิดหน่อย
        self._bob_time += dt
        offset = math.sin(self._bob_time * 3.0) * 3  # ปรับ speed/ระยะได้
        self.rect.y = int(self._base_y + offset)

        # อัปเดตเฟรมแอนิเมชัน (AnimatedNode จะจัดการ frames ให้)
        super().update(dt)
