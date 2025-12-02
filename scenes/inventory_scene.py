# scenes/inventory_scene.py
from __future__ import annotations

import pygame

from .base_scene import BaseScene
from items.item_database import ITEM_DB


class InventoryScene(BaseScene):
    def __init__(self, game, player) -> None:
        super().__init__(game)
        self.player = player

        self.font = pygame.font.Font(None, 28)
        self.title_font = pygame.font.Font(None, 36)

        self.selected_index = 0

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
                elif event.key == pygame.K_DOWN:
                    inv_size = self.player.inventory.size
                    self.selected_index = min(inv_size - 1, self.selected_index + 1)

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

        stack = inv.get(self.selected_index)
        if stack is None:
            return

        item = stack.item

        # ---------- เคสพิเศษ: sword_all_direction = ไอเท็มกดใช้ ----------
        if item.id == "sword_all_direction":
            # ลบออกจากช่องปัจจุบัน 1 ชิ้น
            stack.quantity -= 1
            if stack.quantity <= 0:
                inv.set(self.selected_index, None)

            # สั่งให้ player เปิดบัฟ 10 วินาที
            if hasattr(self.player, "activate_sword_all_direction"):
                self.player.activate_sword_all_direction(duration=10.0)

            print("ใช้ไอเท็ม All Direction Sword (10 วินาที)")
            # จะปิดหน้าต่าง inventory เลยก็ได้ ถ้าชอบ
            # self.game.scene_manager.pop_scene()
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

        equipped = eq.equip_from_inventory(inv, self.selected_index, slot=slot)
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

        # แสดงไอเทมเป็น list
        start_x = 200
        start_y = 140
        line_h = 28

        for i in range(self.player.inventory.size):
            stack = self.player.inventory.get(i)

            # highlight ช่องที่เลือกอยู่
            bg_rect = pygame.Rect(start_x - 10, start_y + i * line_h - 4, 420, line_h)
            if i == self.selected_index:
                pygame.draw.rect(surface, (80, 80, 140), bg_rect)

            if stack is None:
                text = f"{i:02d}: (empty)"
                color = (120, 120, 120)
            else:
                item = stack.item
                text = f"{i:02d}: {item.name} x{stack.quantity} [{item.item_type}]"
                color = (255, 255, 255)

            t_surf = self.font.render(text, True, color)
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

        base_y = start_y + self.player.inventory.size * line_h + 20

        main_surf = self.font.render(main_txt, True, (255, 255, 0))
        armor_surf = self.font.render(armor_txt, True, (255, 255, 0))

        surface.blit(main_surf, (start_x, base_y))
        surface.blit(armor_surf, (start_x, base_y + 28))
