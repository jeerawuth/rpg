# scenes/base_scene.py
# abstract base class ของทุก scene

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from core.game_app import GameApp
    import pygame


class BaseScene(ABC):
    # ---------- HUD / UI standard style ----------
    HUD_BG_COLOR = (0, 0, 0)
    HUD_BG_ALPHA = int(0.10 * 255)  # 10% transparency
    HUD_TEXT_COLOR = (255, 255, 255)
    HUD_TEXT_MUTED = (220, 220, 220)
    HUD_TEXT_ACCENT = (255, 230, 140)
    HUD_SHADOW_COLOR = (0, 0, 0)

    def __init__(self, game: "GameApp") -> None:
        self.game = game

    # เรียกตอน scene ถูกแสดงครั้งแรก/ถูก push
    def enter(self, **kwargs) -> None:
        pass

    # เรียกตอน scene ถูก pop หรือเปลี่ยน
    def exit(self) -> None:
        pass

    # ---------- HUD / UI drawing helpers ----------
    def draw_dim_overlay(
        self,
        surface: pygame.Surface,
        alpha: int = 160,
        color: tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        """Draw fullscreen dim overlay (for menus / pause / inventory)."""
        w, h = surface.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((*color, max(0, min(255, alpha))))
        surface.blit(overlay, (0, 0))

    def draw_panel(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        alpha: int | None = None,
        color: tuple[int, int, int] | None = None,
        border_radius: int = 10,
    ) -> None:
        """Draw rounded rectangle panel with alpha."""
        if alpha is None:
            alpha = self.HUD_BG_ALPHA
        if color is None:
            color = self.HUD_BG_COLOR
        panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (*color, max(0, min(255, alpha))), panel.get_rect(), border_radius=border_radius)
        surface.blit(panel, rect.topleft)

    def draw_text(
        self,
        surface: pygame.Surface,
        text: str,
        pos: tuple[int, int],
        font: pygame.font.Font,
        color: tuple[int, int, int] | None = None,
        shadow: bool = True,
        shadow_offset: tuple[int, int] = (1, 1),
        shadow_color: tuple[int, int, int] | None = None,
    ) -> pygame.Rect:
        if color is None:
            color = self.HUD_TEXT_COLOR
        if shadow_color is None:
            shadow_color = self.HUD_SHADOW_COLOR
        x, y = pos
        if shadow:
            s = font.render(text, True, shadow_color)
            surface.blit(s, (x + shadow_offset[0], y + shadow_offset[1]))
        t = font.render(text, True, color)
        rect = t.get_rect(topleft=(x, y))
        surface.blit(t, rect)
        return rect

    def draw_text_block(
        self,
        surface: pygame.Surface,
        lines: list[str],
        topleft: tuple[int, int],
        font: pygame.font.Font,
        *,
        padding: int = 10,
        line_gap: int = 4,
        panel_alpha: int | None = None,
        panel_color: tuple[int, int, int] | None = None,
        text_color: tuple[int, int, int] | None = None,
        shadow: bool = True,
        border_radius: int = 10,
    ) -> pygame.Rect:
        if not lines:
            return pygame.Rect(topleft, (0, 0))
        widths = [font.size(t)[0] for t in lines]
        line_h = font.get_height()
        w = max(widths)
        h = len(lines) * line_h + (len(lines) - 1) * line_gap
        x, y = topleft
        rect = pygame.Rect(x, y, w + padding * 2, h + padding * 2)
        self.draw_panel(surface, rect, alpha=panel_alpha, color=panel_color, border_radius=border_radius)
        cy = y + padding
        for t in lines:
            self.draw_text(surface, t, (x + padding, cy), font, color=text_color, shadow=shadow)
            cy += line_h + line_gap
        return rect


    @abstractmethod
    def handle_events(self, events: list) -> None:
        ...

    @abstractmethod
    def update(self, dt: float) -> None:
        ...

    @abstractmethod
    def draw(self, surface: "pygame.Surface") -> None:
        ...
