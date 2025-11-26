# scenes/base_scene.py
# abstract base class ของทุก scene

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.game_app import GameApp
    import pygame


class BaseScene(ABC):
    def __init__(self, game: "GameApp") -> None:
        self.game = game

    # เรียกตอน scene ถูกแสดงครั้งแรก/ถูก push
    def enter(self, **kwargs) -> None:
        pass

    # เรียกตอน scene ถูก pop หรือเปลี่ยน
    def exit(self) -> None:
        pass

    @abstractmethod
    def handle_events(self, events: list) -> None:
        ...

    @abstractmethod
    def update(self, dt: float) -> None:
        ...

    @abstractmethod
    def draw(self, surface: "pygame.Surface") -> None:
        ...
