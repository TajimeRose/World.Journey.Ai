from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional


class MessageStore:
    def __init__(self, limit: int) -> None:
        self._messages: Deque[Dict[str, object]] = deque(maxlen=limit)

    def add(self, role: str, text: str, *, html: Optional[str] = None) -> Dict[str, object]:
        entry: Dict[str, object] = {
            "role": role,
            "text": text,
            "createdAt": self._now_iso(),
        }
        if html:
            entry["html"] = html
        self._messages.append(entry)
        return entry

    def list(self) -> List[Dict[str, object]]:
        return list(self._messages)

    def since(self, since_iso: str) -> List[Dict[str, object]]:
        try:
            since_dt = datetime.fromisoformat(since_iso)
            if since_dt.tzinfo is None:
                since_dt = since_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return self.list()

        filtered: List[Dict[str, object]] = []
        for message in self._messages:
            created_raw = message.get("createdAt")
            try:
                created = datetime.fromisoformat(str(created_raw))
            except (TypeError, ValueError):
                filtered.append(message)
                continue
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created > since_dt:
                filtered.append(message)
        return filtered

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
