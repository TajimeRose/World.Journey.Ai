"""Minimal in-memory MessageStore used by chatbot during development/tests."""
from typing import List, Dict, Optional
import time


class MessageStore:
    def __init__(self) -> None:
        self._messages: List[Dict[str, object]] = []

    def add(self, role: str, text: str, html: Optional[str] = None) -> Dict[str, object]:
        item = {
            "role": role,
            "text": text,
            "html": html,
            "timestamp": time.time()
        }
        self._messages.append(item)
        return item

    def list(self) -> List[Dict[str, object]]:
        return list(self._messages)

    def since(self, since_iso: str) -> List[Dict[str, object]]:
        # Very simple stub: return all messages
        return list(self._messages)
