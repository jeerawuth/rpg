# core/event_bus.py
# ระบบ event ภายในเกมแบบ pub/sub ง่าย ๆ

from collections import defaultdict
from typing import Callable, Dict, List, Any


class EventBus:
    def __init__(self) -> None:
        self._listeners: Dict[str, List[Callable[..., None]]] = defaultdict(list)

    def subscribe(self, event_name: str, callback: Callable[..., None]) -> None:
        if callback not in self._listeners[event_name]:
            self._listeners[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callable[..., None]) -> None:
        if callback in self._listeners[event_name]:
            self._listeners[event_name].remove(callback)

    def emit(self, event_name: str, **payload: Any) -> None:
        for callback in list(self._listeners[event_name]):
            callback(**payload)
