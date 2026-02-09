# scenes/options_scene.py
# หน้าตั้งค่า (placeholder)

from __future__ import annotations

import pygame

from .base_scene import BaseScene
from config.settings import UI_FONT_PATH


class OptionsScene(BaseScene):
    def __init__(self, game) -> None:
        super().__init__(game)
        self.font = self.game.resources.load_font(UI_FONT_PATH, 32)
        
        # ---------- Character Scanning ----------
        import os
        # Use resource manager's base_path to ensure correct path in frozen builds
        base_path = os.path.join(self.game.resources.base_path, "graphics", "images", "player")
        self.available_players = []
        if os.path.isdir(base_path):
            for d in os.listdir(base_path):
                full_p = os.path.join(base_path, d)
                if os.path.isdir(full_p) and not d.startswith("."):
                    self.available_players.append(d)
        self.available_players.sort()
        if not self.available_players:
            self.available_players = ["knight"]

        # Sync with Global State
        current = self.game.selected_player_type
        if current in self.available_players:
            self.selected_index = self.available_players.index(current)
        else:
            self.selected_index = 0
            if self.available_players:
                self.game.selected_player_type = self.available_players[0]

    def handle_events(self, events) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    self.game.scene_manager.pop_scene()
                elif event.key == pygame.K_UP:
                    self.selected_index = (self.selected_index - 1) % len(self.available_players)
                    self._update_global_selection()
                elif event.key == pygame.K_DOWN:
                    self.selected_index = (self.selected_index + 1) % len(self.available_players)
                    self._update_global_selection()

    def _update_global_selection(self):
        self.game.selected_player_type = self.available_players[self.selected_index]

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((15, 15, 40))
        w, h = surface.get_size()
        title = self.font.render("Options", True, self.HUD_TEXT_COLOR)
        surface.blit(title, title.get_rect(center=(w // 2, h // 4)))

        # สร้างรายการข้อความที่จะแสดง
        # บรรทัดแรก
        lines = ["-- SELECT CHARACTER --", " "]
        
        # วนลูปรายชื่อตัวละคร
        for i, name in enumerate(self.available_players):
            prefix = "  "
            color_hex = self.HUD_TEXT_COLOR
            
            # ถ้าเป็นตัวที่เลือกอยู่ ให้มีลูกศรนำหน้า + สีเด่น
            if i == self.selected_index:
                prefix = "> "
                color_hex = self.HUD_TEXT_ACCENT
            
            lines.append(f"{prefix}{name.upper()}")

        lines.append(" ")
        lines.append("(UP/DOWN to select)")
        lines.append("ESC - Back")

        # วาด Text Block กลางจอ
        line_h = self.font.get_height()
        widths = [self.font.size(t)[0] for t in lines]
        block_w = max(widths)
        block_h = len(lines) * line_h + (len(lines) - 1) * 10
        
        panel = pygame.Rect(0, 0, block_w + 60, block_h + 40)
        panel.center = (w // 2, h // 2)
        self.draw_panel(surface, panel, alpha=self.HUD_BG_ALPHA)

        y = panel.top + 20
        # เราต้องวาดทีละบรรทัด เพราะสีอาจต่างกัน (ตัวที่เลือก)
        for i, line in enumerate(lines):
            # ตรวจสอบว่าเป็นบรรทัดตัวเลือกหรือไม่ (ข้าม header 2 บรรทัดแรก)
            # index ของตัวละครเริ่มที่บรรทัด index 2
            # ตัวละครมีจำนวน len(self.available_players)
            
            # Default color
            color = self.HUD_TEXT_COLOR
            
            # คำนวณว่าบรรทัดนี้คือ index ของ player คนไหน
            # lines[0] = header, lines[1] = space
            # lines[2] = player[0]
            player_idx = i - 2
            
            if 0 <= player_idx < len(self.available_players):
                if player_idx == self.selected_index:
                    color = self.HUD_TEXT_ACCENT
            
            if "ESC" in line or "UP/DOWN" in line:
                 color = self.HUD_TEXT_MUTED

            t_surf = self.font.render(line, True, color)
            rect = t_surf.get_rect(centerx=panel.centerx, y=y)
            
            # shadow
            s_surf = self.font.render(line, True, self.HUD_SHADOW_COLOR)
            surface.blit(s_surf, (rect.x + 1, rect.y + 1))
            
            surface.blit(t_surf, rect)
            y += line_h + 10
