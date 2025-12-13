# scenes/inventory_scene.py
from __future__ import annotations

import pygame

from .base_scene import BaseScene
from items.item_database import ITEM_DB
from config.settings import UI_FONT_HUD_PATH, UI_FONT_PATH


class InventoryScene(BaseScene):
    """
    Inventory UI (icon grid + grouped by item_id)

    - รวมไอเท็มที่ id ซ้ำกันเป็นก้อนเดียวในการแสดงผล
    - แสดง icon (ใช้เฟรมแรกจาก item.icon_key) แทนข้อความ
    - แสดงจำนวนเป็น "xN" ซ้อนบนรูปภาพ
    - การกด ENTER จะใช้/equip จาก "ช่องแรก" ของไอเท็มนั้นใน inventory จริง
    """

    def __init__(self, game, player) -> None:
        super().__init__(game)
        self.player = player

        # ใช้ฟอนต์เดิมก่อน (ถ้าคุณย้ายไปใช้ ResourceManager.load_font แล้ว
        # สามารถเปลี่ยนตรงนี้เป็น self.game.resources.load_font("fonts/Kanit-Regular.ttf", size) ได้)
        self.font = self.game.resources.load_font(UI_FONT_HUD_PATH, 22)
        self.title_font = self.game.resources.load_font(UI_FONT_PATH, 28)
        self.qty_font = self.game.resources.load_font(UI_FONT_PATH, 22)

        # selected index ใน "รายการที่รวมแล้ว"
        self.selected_index = 0

        # cache ของรายการไอเท็มรวมแล้ว (rebuild ทุกครั้งที่ draw)
        self._grouped = []
        self._grid_cols = 6  # จะคำนวณใหม่ตามขนาดหน้าจอ

    # ----------------- INTERNAL -----------------
    def _build_grouped_items(self):
        """
        คืนค่า list ของ dict:
        {
          "item": ItemBase,
          "count": int,
          "slot_indices": [int, ...]   # ช่องจริงใน inventory ที่มีไอเท็มนี้
        }
        """
        inv = getattr(self.player, "inventory", None)
        if inv is None:
            return []

        groups = {}
        for i in range(inv.size):
            stack = inv.get(i)
            if stack is None:
                continue
            item = stack.item
            if item is None:
                continue

            gid = item.id
            if gid not in groups:
                groups[gid] = {"item": item, "count": 0, "slot_indices": []}

            # รวมจำนวนจากทุก stack (ส่วนมากจะเป็น 1)
            groups[gid]["count"] += int(getattr(stack, "quantity", 1) or 1)
            groups[gid]["slot_indices"].append(i)

        # จัดเรียงให้คงที่: ตาม item.name (หรือ id)
        grouped_list = list(groups.values())
        grouped_list.sort(key=lambda g: (getattr(g["item"], "item_type", ""), getattr(g["item"], "name", g["item"].id)))
        return grouped_list

    def _selected_slot_index(self) -> int | None:
        """คืนค่า slot index จริง (ช่องใน inventory) ของรายการที่เลือกอยู่"""
        if not self._grouped:
            return None
        idx = max(0, min(self.selected_index, len(self._grouped) - 1))
        slots = self._grouped[idx]["slot_indices"]
        return slots[0] if slots else None

    def _handle_equip_selected(self) -> None:
        """ใช้/equip ไอเท็มที่เลือก (อ้างอิง slot จริงช่องแรกของกลุ่มนั้น)"""
        inv = getattr(self.player, "inventory", None)
        eq = getattr(self.player, "equipment", None)
        if inv is None or eq is None:
            return

        slot_index = self._selected_slot_index()
        if slot_index is None:
            return

        stack = inv.get(slot_index)
        if stack is None:
            return

        item = stack.item
        if item is None:
            return

        # ---------- เคสพิเศษ: ดาบรอบทิศทาง = ไอเท็มกดใช้ ----------
        if item.id in ("sword_all_direction", "sword_all_direction_2"):
            duration = 10.0
            item_name = "All Direction Sword"

            if item.id == "sword_all_direction_2":
                duration = 20.0
                item_name = item.name

            stack.quantity -= 1
            if stack.quantity <= 0:
                inv.set(slot_index, None)

            if hasattr(self.player, "activate_sword_all_direction"):
                self.player.activate_sword_all_direction(item_id=item.id, duration=duration)

            print(f"ใช้ไอเท็ม {item_name} ({duration} วินาที)")
            return

        # ---------- เคสพิเศษ: ธนู Power = ไอเท็มกดใช้ ----------
        if item.id in ("bow_power_1", "bow_power_2"):
            duration = 10.0
            if item.id == "bow_power_2":
                duration = 20.0

            stack.quantity -= 1
            if stack.quantity <= 0:
                inv.set(slot_index, None)

            if hasattr(self.player, "activate_bow_power"):
                self.player.activate_bow_power(item_id=item.id, duration=duration)

            print(f"ใช้ไอเท็ม {item.name} ({duration} วินาที)")
            return

        # ---------- เคสพิเศษ: สายฟ้า ----------
        if item.id in ("magic_lightning", "magic_lightning_2"):
            # magic_lightning_2 เป็นแบบ auto tick (ถ้าคุณทำไว้แล้ว)
            duration = 10.0
            if item.id == "magic_lightning_2":
                duration = 5.0

            stack.quantity -= 1
            if stack.quantity <= 0:
                inv.set(slot_index, None)

            if hasattr(self.player, "activate_magic_lightning"):
                self.player.activate_magic_lightning(item_id=item.id, duration=duration)

            print(f"ใช้ไอเท็ม {item.name} ({duration} วินาที)")
            return

        # ---------- เคสทั่วไป: equip ตามประเภท ----------
        if item.item_type == "weapon":
            slot = "main_hand"
        elif item.item_type == "armor":
            slot = "armor"
        else:
            print(f"Item '{item.name}' (type={item.item_type}) equip ไม่ได้")
            return

        equipped = eq.equip_from_inventory(inv, slot_index, slot=slot)
        if equipped:
            print(f"Equipped {item.name} -> slot {slot}")
        else:
            print(f"Equip {item.name} ล้มเหลว (slot={slot})")

    # ----------------- EVENTS -----------------
    def handle_events(self, events) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue

            # ปิดหน้าต่าง inventory
            if event.key in (pygame.K_ESCAPE, pygame.K_i):
                self.game.scene_manager.pop_scene()
                return

            if not self._grouped:
                continue

            # เลื่อนแบบกริด
            cols = max(1, int(self._grid_cols))

            if event.key == pygame.K_LEFT:
                self.selected_index = max(0, self.selected_index - 1)
            elif event.key == pygame.K_RIGHT:
                self.selected_index = min(len(self._grouped) - 1, self.selected_index + 1)
            elif event.key == pygame.K_UP:
                self.selected_index = max(0, self.selected_index - cols)
            elif event.key == pygame.K_DOWN:
                self.selected_index = min(len(self._grouped) - 1, self.selected_index + cols)

            elif event.key == pygame.K_RETURN:
                self._handle_equip_selected()

    # ----------------- UPDATE / DRAW -----------------
    def update(self, dt: float) -> None:
        # ไม่มี logic แบบ real-time มากนัก
        pass

    def draw(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()

        # overlay พื้นหลัง
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        # สร้างรายการแบบรวม (ทุก frame เพื่อให้ sync กับ inventory)
        self._grouped = self._build_grouped_items()
        if self._grouped:
            self.selected_index = max(0, min(self.selected_index, len(self._grouped) - 1))
        else:
            self.selected_index = 0

        # title + hint
        title_surf = self.title_font.render("Inventory", True, (255, 255, 255))
        surface.blit(title_surf, (40, 30))

        hint_text = "Arrow keys: Move   ENTER: Use/Equip   ESC/I: Close"
        hint = self.font.render(hint_text, True, (220, 220, 220))
        surface.blit(hint, (40, 80))

        # แสดงชื่อไอเท็มที่เลือก (พร้อมจำนวน)
        if self._grouped:
            sel = self._grouped[self.selected_index]
            sel_item = sel["item"]
            sel_count = int(sel.get("count", 1) or 1)
            sel_name = getattr(sel_item, "name", getattr(sel_item, "id", ""))
            label = f"Selected: {sel_name}"
            if sel_count > 1:
                label += f"  x{sel_count}"
            label_surf = self.font.render(label, True, (255, 255, 255))
            surface.blit(label_surf, (40, 105))


        # พื้นที่กริด
        margin_x = 40
        margin_y = 120
        panel_w = w - margin_x * 2
        panel_h = h - margin_y - 40

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 26))  # ดำโปร่ง ~10%
        surface.blit(panel, (margin_x, margin_y))

        # ค่ากริด
        cell = 84
        pad = 12
        cols = max(1, (panel_w - pad * 2) // cell)
        self._grid_cols = cols
        icon_max = cell - 16

        # วาดไอเท็มเป็นกริด
        for idx, g in enumerate(self._grouped):
            row = idx // cols
            col = idx % cols

            x = margin_x + pad + col * cell
            y = margin_y + pad + row * cell

            cell_rect = pygame.Rect(x, y, cell, cell)

            # highlight
            if idx == self.selected_index:
                pygame.draw.rect(surface, (255, 215, 0), cell_rect, width=2, border_radius=5)
            else:
                pygame.draw.rect(surface, (255, 255, 255), cell_rect, width=1, border_radius=5)

            item = g["item"]
            count = g["count"]

            # โหลด icon เฟรมแรกจาก icon_key
            icon = None
            try:
                # รูปภาพ item สำหรับแสดงใน HUD หรือ Inventory
                if hasattr(item, "ui_icon_key") and item.ui_icon_key:
                    icon = self.game.resources.load_image(item.ui_icon_key)
            except Exception:
                icon = None

            # ถ้าไม่มีรูป ให้เป็น placeholder
            if icon is None:
                icon = pygame.Surface((icon_max, icon_max), pygame.SRCALPHA)
                icon.fill((120, 120, 120, 255))
                q = self.qty_font.render("?", True, (0, 0, 0))
                icon.blit(q, q.get_rect(center=(icon_max // 2, icon_max // 2)))

            # scale icon ให้พอดีช่อง
            iw, ih = icon.get_size()
            scale = min(icon_max / max(1, iw), icon_max / max(1, ih), 1.0)
            if scale != 1.0:
                icon = pygame.transform.smoothscale(icon, (int(iw * scale), int(ih * scale)))

            # วาง icon กลางช่อง
            icon_rect = icon.get_rect(center=cell_rect.center)
            surface.blit(icon, icon_rect)

            # จำนวนซ้อนบนรูป (เฉพาะกรณี > 1)
            if count > 1:
                qty_text = f"x{count}"
                # shadow
                sh = self.qty_font.render(qty_text, True, (0, 0, 0))
                surface.blit(sh, (cell_rect.right - sh.get_width() - 8 + 1, cell_rect.bottom - sh.get_height() - 6 + 1))
                qty = self.qty_font.render(qty_text, True, (255, 255, 255))
                surface.blit(qty, (cell_rect.right - qty.get_width() - 8, cell_rect.bottom - qty.get_height() - 6))

        # ถ้า inventory ว่าง
        if not self._grouped:
            msg = self.font.render("Inventory is empty.", True, (240, 240, 240))
            surface.blit(msg, msg.get_rect(center=(w // 2, h // 2)))
