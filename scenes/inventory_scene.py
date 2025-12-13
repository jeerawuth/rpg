# scenes/inventory_scene.py
from __future__ import annotations

import pygame

from collections import OrderedDict

from .base_scene import BaseScene
# from items.item_database import ITEM_DB
from config.settings import UI_FONT_PATH, UI_FONT_HUD_PATH


class InventoryScene(BaseScene):
    def __init__(self, game, player) -> None:
        super().__init__(game)
        self.player = player

        self.font = self.game.resources.load_font(UI_FONT_PATH, 20)
        self.title_font = self.game.resources.load_font(UI_FONT_HUD_PATH, 21)

        self.selected_index = 0

        # cache: รายการไอเท็มแบบ "รวมซ้ำ" (item_id เดียวกันรวมเป็นก้อนเดียว)
        # โครงสร้างแต่ละรายการ: {"item": ItemBase, "qty": int, "slots": [slot_index, ...]}
        self._grouped_view_cache = []

    def _build_grouped_view(self):
        """รวมไอเท็มที่มี item_id ซ้ำกัน ให้แสดงเป็นบรรทัดเดียว พร้อมจำนวนรวม"""
        inv = getattr(self.player, "inventory", None)
        if inv is None:
            return []

        grouped = OrderedDict()
        for slot_i in range(inv.size):
            stack = inv.get(slot_i)
            if stack is None:
                continue

            item = stack.item
            g = grouped.get(item.id)
            if g is None:
                grouped[item.id] = {"item": item, "qty": int(stack.quantity), "slots": [slot_i]}
            else:
                g["qty"] += int(stack.quantity)
                g["slots"].append(slot_i)

        return list(grouped.values())

    def _get_grouped_view(self):
        # rebuild ทุกครั้งเพื่อกันจำนวนเปลี่ยนระหว่างเฟรม
        self._grouped_view_cache = self._build_grouped_view()
        # clamp selected_index ให้ไม่หลุด
        if self._grouped_view_cache:
            self.selected_index = max(0, min(self.selected_index, len(self._grouped_view_cache) - 1))
        else:
            self.selected_index = 0
        return self._grouped_view_cache

    # ----------------- EVENTS -----------------
    def handle_events(self, events) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                # ปิดหน้าต่าง inventory
                if event.key in (pygame.K_ESCAPE, pygame.K_i):
                    self.game.scene_manager.pop_scene()

                # เลื่อนช่องเลือก
                elif event.key == pygame.K_UP:
                    self.selected_index = max(0, self.selected_index - 1)
                    self._get_grouped_view()  # clamp
                elif event.key == pygame.K_DOWN:
                    view_len = len(self._get_grouped_view())
                    if view_len > 0:
                        self.selected_index = min(view_len - 1, self.selected_index + 1)

                # กด ENTER เพื่อ equip
                elif event.key == pygame.K_RETURN:
                    self._handle_equip_selected()

    # ----------------- LOGIC -----------------------
    #---------- ฟังก์ชันจัดการ equip ไอเท็มที่เลือก ----------
    # ----- เคสพิเศษ: ไอเท็มกดใช้ (ใช้แล้วหายไป) ----------
    def _handle_equip_selected(self) -> None:
        """เลือกช่อง inventory ปัจจุบัน แล้วพยายาม equip หรือใช้ไอเท็ม"""

        inv = self.player.inventory
        eq = self.player.equipment

        if inv is None or eq is None:
            return

        view = self._get_grouped_view()
        if not view:
            return

        slot_index = view[self.selected_index]["slots"][0]

        stack = inv.get(slot_index)
        if stack is None:
            return

        item = stack.item

        # ==================================================================
        # เคส magic_lightning: เปิดบัฟถืออาวุธชั่วคราว (ไม่ร่ายทันที)
        # ==================================================================
        if item.id == "magic_lightning":
            duration = 10.0  # ปรับได้ตามต้องการ

            # ใช้แล้วหายไป 1 ชิ้น
            stack.quantity -= 1
            if stack.quantity <= 0:
                inv.set(slot_index, None)

            if hasattr(self.player, "activate_magic_lightning"):
                self.player.activate_magic_lightning(item_id=item.id, duration=duration)
                print(f"ถือ magic_lightning ({duration} วินาที) กด SPACE เพื่อร่ายสายฟ้า")
            else:
                print("PlayerNode ยังไม่มี activate_magic_lightning()")

            self.game.scene_manager.pop_scene()
            return

        # ==================================================================
        # เคส magic_lightning_2: เปิดบัฟถืออาวุธชั่วคราว (ไม่ร่ายทันที)
        # ==================================================================
        if item.id == "magic_lightning_2":
            duration = 5.0  # ปรับได้ตามต้องการ

            # ใช้แล้วหายไป 1 ชิ้น
            stack.quantity -= 1
            if stack.quantity <= 0:
                inv.set(slot_index, None)

            if hasattr(self.player, "activate_magic_lightning"):
                self.player.activate_magic_lightning(item_id=item.id, duration=duration)
                print(f"ถือ magic_lightning 2 ({duration} วินาที) กด SPACE เพื่อร่ายสายฟ้า")
            else:
                print("PlayerNode ยังไม่มี activate_magic_lightning()")

            self.game.scene_manager.pop_scene()
            return

        # ---------- เคสพิเศษ: ดาบรอบทิศทาง = ไอเท็มกดใช้ (ใช้แล้วหายไป) ----------
        # รองรับทั้ง sword_all_direction (10 วิ) และ sword_all_direction_2 (20 วิ)
        if item.id in ("sword_all_direction", "sword_all_direction_2"):
            # 1. กำหนดระยะเวลาตามไอเท็ม
            duration = 10.0
            item_name = "All Direction Sword"
            
            if item.id == "sword_all_direction_2":
                duration = 20.0
                item_name = item.name  # ใช้ชื่อจาก ItemBase ที่คุณสร้างไว้

            # 2. ลบออกจากช่องปัจจุบัน 1 ชิ้น
            stack.quantity -= 1
            if stack.quantity <= 0:
                inv.set(slot_index, None)

            # 3. สั่งให้ player เปิดบัฟตามระยะเวลาที่กำหนด ส่งชื่อไอเท็มและรหัสไอดีของไอเท็มไป
            if hasattr(self.player, "activate_sword_all_direction"):
                self.player.activate_sword_all_direction(item_id=item.id, duration=duration)

            print(f"ใช้ไอเท็ม {item_name} ({duration} วินาที)")
            # self.game.scene_manager.pop_scene()
            return


        # ==================================================================
        # เคสพิเศษ: ธนู Power (ใช้แล้วหมดไป มีเวลาจำกัด)
        # รองรับทั้ง bow_power_1 (20 วิ) และ bow_power_2 (10 วิ)
        # ==================================================================
        if item.id in ("bow_power_1", "bow_power_2"):
            # 1. กำหนดระยะเวลา
            duration = 20.0
            if item.id == "bow_power_2":
                duration = 10.0
            
            # 2. ลบออกจาก inventory 1 ชิ้น
            stack.quantity -= 1
            if stack.quantity <= 0:
                inv.set(slot_index, None)

            # 3. สั่งให้ player เปิดบัฟธนู
            # (เราจะต้องไปสร้างฟังก์ชัน activate_bow_power ใน PlayerNode)
            if hasattr(self.player, "activate_bow_power"):
                self.player.activate_bow_power(item_id=item.id, duration=duration)
            
            print(f"ใช้ไอเท็ม {item.name} ({duration} วินาที)")
            return


        # ---------- เคสทั่วไป: equip ตามประเภทของไอเท็ม ----------
        # ตัดสินใจว่าจะใส่ช่องไหนตามประเภทของไอเท็ม
        if item.item_type == "weapon":
            slot = "main_hand"
        elif item.item_type == "armor":
            # ถ้าอยากแยก armor / off_hand เพิ่มเงื่อนไขได้
            slot = "armor"
        else:
            print(f"Item '{item.name}' (type={item.item_type}) equip ไม่ได้")
            return

        equipped = eq.equip_from_inventory(inv, slot_index, slot=slot)
        if equipped:
            print(f"Equipped {item.name} -> slot {slot}")
        else:
            print(f"Equip {item.name} ล้มเหลว (slot={slot})")


    # ----------------- UPDATE / DRAW -----------------
    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()

        # พื้นหลังทึบหน่อย
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        # Title
        title_surf = self.title_font.render("Inventory", True, (255, 255, 255))
        surface.blit(title_surf, title_surf.get_rect(center=(w // 2, 40)))

        # Hint: อธิบายการกดปุ่ม
        hint_text = "UP/DOWN: Move  |  ENTER: Equip (weapon→main, armor→armor)  |  I/ESC: Close"
        hint = self.font.render(hint_text, True, (200, 200, 200))
        surface.blit(hint, hint.get_rect(center=(w // 2, 100)))

        # แสดงไอเทมแบบรวมซ้ำ (item_id เดียวกัน แสดงบรรทัดเดียว + จำนวนรวม)
        start_x = 200
        start_y = 140
        line_h = 28

        grouped = self._get_grouped_view()
        if not grouped:
            empty_txt = self.font.render("(empty)", True, (180, 180, 180))
            surface.blit(empty_txt, (start_x, start_y))
        else:
            for i, entry in enumerate(grouped):
                item = entry["item"]
                qty = entry["qty"]

                # highlight ช่องที่เลือกอยู่
                bg_rect = pygame.Rect(start_x - 10, start_y + i * line_h - 4, 520, line_h)
                if i == self.selected_index:
                    pygame.draw.rect(surface, (80, 80, 140), bg_rect)

                text = f"{i:02d}: {item.name} X{qty} [{item.item_type}]"
                t_surf = self.font.render(text, True, (255, 255, 255))
                surface.blit(t_surf, (start_x, start_y + i * line_h))

        # ------------ แสดงของที่ equip อยู่ ------------
        eq = self.player.equipment

        # main-hand (weapon)
        main_weapon = eq.get_item("main_hand")
        if main_weapon:
            main_txt = f"Main-hand: {main_weapon.name}"
        else:
            main_txt = "Main-hand: (none)"

        # armor (shield / เกราะ)
        armor_item = eq.get_item("armor")
        if armor_item:
            armor_txt = f"Armor: {armor_item.name}"
        else:
            armor_txt = "Armor: (none)"

        base_y = start_y + max(1, len(grouped)) * line_h + 20

        main_surf = self.font.render(main_txt, True, (255, 255, 0))
        armor_surf = self.font.render(armor_txt, True, (255, 255, 0))

        surface.blit(main_surf, (start_x, base_y))
        surface.blit(armor_surf, (start_x, base_y + 28))
