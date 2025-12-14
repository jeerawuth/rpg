# core/scene_manager.py
# จัดการ stack ของ Scene ปัจจุบัน

from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # type hints only
    from ..scenes.base_scene import BaseScene
    from .game_app import GameApp


class SceneManager:
    def __init__(self, game: "GameApp") -> None:
        self.game = game
        self._stack: List["BaseScene"] = []

    @property
    def current_scene(self) -> Optional["BaseScene"]:
        if not self._stack:
            return None
        return self._stack[-1]
    
    def _sync_music(self) -> None:
        # หา scene บนสุดที่ "override music" และมี MUSIC
        for s in reversed(self._stack):
            if getattr(s, "OVERRIDE_MUSIC", True):
                self.game.audio.apply_music(getattr(s, "get_music", lambda: None)())
                return
        self.game.audio.apply_music(None)

    def set_scene(self, scene: "BaseScene") -> None:
        # เคลียร์ทั้งหมดแล้วเปลี่ยนไป scene ใหม่
        while self._stack:
            old = self._stack.pop()
            old.exit()
        self._stack.append(scene)
        scene.enter()
        self._sync_music()

    def push_scene(self, scene: "BaseScene") -> None:
        self._stack.append(scene)
        scene.enter()
        self._sync_music()

    def pop_scene(self) -> None:
        if not self._stack:
            return
        old = self._stack.pop()
        old.exit()
        self._sync_music()

    # ---------- Delegation ----------
    def handle_events(self, events) -> None:
        if self.current_scene:
            self.current_scene.handle_events(events)

    def update(self, dt: float) -> None:
        if self.current_scene:
            self.current_scene.update(dt)

    def draw(self, surface) -> None:
        # วาดทุก scene ใน stack เผื่อ pause overlay ฯลฯ
        for scene in self._stack:
            scene.draw(surface)

