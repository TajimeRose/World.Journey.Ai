from __future__ import annotations

import unicodedata
from typing import Dict, List

from .destinations import BANGKOK_KEYWORDS
from .guides import build_bangkok_guides_html
from .messages import MessageStore


class ChatEngine:
    def __init__(self, message_store: MessageStore, destinations: List[Dict[str, str]]) -> None:
        self._store = message_store
        self._destinations = destinations

    def append_user(self, text: str) -> Dict[str, object]:
        return self._store.add("user", text)

    def append_assistant(self, text: str, *, html: str | None = None) -> Dict[str, object]:
        return self._store.add("assistant", text, html=html)

    def build_reply(self, user_text: str) -> Dict[str, object]:
        if self._matches_bangkok(user_text):
            guide_html = build_bangkok_guides_html()
            return self.append_assistant(
                "จัดให้! รวม 510 ไฮไลต์เที่ยวกรุงเทพพร้อมลิงก์แผนที่",
                html=guide_html,
            )

        destinations = self._search_destinations(user_text)
        highlight = destinations[0]
        summary = (
            f"ลองเริ่มต้นที่ {highlight['name']} ({highlight['city']}) — {highlight['description']}\n"
            f"ดูตำแหน่งใน Google Maps: {highlight['mapUrl']}"
        )
        return self.append_assistant(summary)

    def list_messages(self) -> List[Dict[str, object]]:
        return self._store.list()

    def list_since(self, since_iso: str) -> List[Dict[str, object]]:
        return self._store.since(since_iso)

    def _matches_bangkok(self, query: str) -> bool:
        normalized = self._normalize(query)
        return any(keyword in normalized for keyword in BANGKOK_KEYWORDS)

    def search_destinations(self, query: str) -> List[Dict[str, str]]:
        return self._search_destinations(query)

    def _search_destinations(self, query: str) -> List[Dict[str, str]]:
        normalized = query.lower().strip()
        if not normalized:
            return self._destinations
        results: List[Dict[str, str]] = []
        for item in self._destinations:
            haystack = " ".join([item["name"], item["city"], item["description"]]).lower()
            if normalized in haystack:
                results.append(item)
        return results or self._destinations

    @staticmethod
    def _normalize(text: str) -> str:
        decomposed = unicodedata.normalize("NFKD", text.lower().strip())
        return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
