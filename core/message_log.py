# core/message_log.py
import time
from collections import deque

class MessageLog:
    def __init__(self, max_messages: int = 50, default_lifetime: float = 5.0) -> None:
        self.messages = deque(maxlen=max_messages)
        self.default_lifetime = default_lifetime

    def add(self, text: str, lifetime: float | None = None) -> None:
        if lifetime is None:
            lifetime = self.default_lifetime
        
        # (timestamp_added, lifetime, text)
        entry = (time.time(), lifetime, text)
        self.messages.append(entry)

    def get_messages(self) -> list[str]:
        """
        Return list of active messages (strings only).
        Also prunes expired messages internally (lazy prune).
        """
        now = time.time()
        active = []
        
        # Filter and rebuild deque to remove expired
        # Note: Since we want to keep order, we iterate and keep valid ones
        valid_entries = []
        for ts, life, text in self.messages:
            if now - ts < life:
                valid_entries.append((ts, life, text))
                active.append(text)
        
        # Update internal deque if we pruned anything
        if len(valid_entries) < len(self.messages):
            self.messages.clear()
            self.messages.extend(valid_entries)
            
        return active
