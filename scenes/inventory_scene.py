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

    def handle_events(self, events) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_i):
                    self.game.scene_manager.pop_scene()

                elif event.key == pygame.K_UP:
                    self.selected_index = max(0, self.selected_index - 1)
                elif event.key == pygame.K_DOWN:
                    inv_size = self.player.inventory.size
                    self.selected_index = min(inv_size - 1, self.selected_index + 1)

                elif event.key == pygame.K_RETURN:
                    # กด ENTER เพื่อ equip weapon (ถ้าเป็น weapon)
                    equipped = self.player.equipment.equip_from_inventory(
                        self.player.inventory,
                        self.selected_index,
                        slot="main_hand",
                    )
                    if equipped:
                        print("Equipped main-hand weapon from inventory slot", self.selected_index)

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        # ทำ overlay ทึบหน่อย
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        surface.blit(overlay, (0, 0))

        w, h = surface.get_size()

        # Title
        title = self.title_font.render("Inventory", True, (255, 255, 255))
        surface.blit(title, title.get_rect(center=(w // 2, 60)))

        # ข้อความช่วย
        hint = self.font.render("UP/DOWN: Move  |  ENTER: Equip main-hand  |  I/ESC: Close", True, (200, 200, 200))
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

        # แสดงอาวุธที่ equip อยู่
        equipped = self.player.equipment.get_item("main_hand")
        if equipped:
            equip_txt = f"Main-hand: {equipped.name}"
        else:
            equip_txt = "Main-hand: (none)"

        equip_surf = self.font.render(equip_txt, True, (255, 255, 0))
        surface.blit(equip_surf, (start_x, start_y + self.player.inventory.size * line_h + 20))
