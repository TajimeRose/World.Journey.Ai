from __future__ import annotations

import html
import unicodedata
from typing import Dict, List

from .destinations import BANGKOK_KEYWORDS
from .guides import build_bangkok_guides_html
from .messages import MessageStore

TRAVEL_KEYWORDS = (
    "เที่ยว",
    "ทริป",
    "ที่เที่ยว",
    "ท่องเที่ยว",
    "travel",
    "trip",
    "itinerary",
    "journey",
    "vacation",
)

TRAVEL_ONLY_MESSAGE = (
    "ตอนนี้น้องปลาทูช่วยวางแผนท่องเที่ยวเท่านั้น ลองบอกชื่อเมือง สไตล์ทริป หรือกิจกรรมที่อยากทำดูนะคะ"
)

THEME_KEYWORDS = {
    "ทะเล": {"ภูเก็ต"},
    "sea": {"ภูเก็ต"},
    "island": {"ภูเก็ต"},
    "ภูเขา": {"เชียงใหม่", "เกียวโต"},
    "mountain": {"เชียงใหม่", "เกียวโต"},
    "คาเฟ": {"เชียงใหม่", "กรุงเทพมหานคร"},
    "cafe": {"เชียงใหม่", "กรุงเทพมหานคร"},
    "shopping": {"กรุงเทพมหานคร", "ดูไบ"},
    "ช้อป": {"กรุงเทพมหานคร", "ดูไบ"},
    "street food": {"กรุงเทพมหานคร"},
    "art": {"ปารีส"},
}


class ChatEngine:
    def __init__(self, message_store: MessageStore, destinations: List[Dict[str, str]]) -> None:
        self._store = message_store
        self._destinations = destinations
        self._normalized_dest_names = [self._normalize(item["name"]) for item in destinations]
        self._normalized_keywords = [self._normalize(keyword) for keyword in TRAVEL_KEYWORDS]

    def append_user(self, text: str) -> Dict[str, object]:
        return self._store.add("user", text)

    def append_assistant(self, text: str, *, html: str | None = None) -> Dict[str, object]:
        return self._store.add("assistant", text, html=html)

    def build_reply(self, user_text: str) -> Dict[str, object]:
        cleaned = user_text.strip()
        if not cleaned:
            return self.append_assistant("ลองพิมพ์ชื่อเมืองหรือสไตล์การเดินทางที่อยากไปนะคะ")

        destinations = self._search_destinations(cleaned)
        if not self._looks_travel_related(cleaned, destinations):
            return self.append_assistant(TRAVEL_ONLY_MESSAGE)

        if self._matches_bangkok(cleaned):
            html_block = build_bangkok_guides_html()
            text = "นี่คือทริปกรุงเทพที่น้องปลาทูจัดไว้ให้ ลองเลือกหรือปรับตามเวลาได้เลยนะคะ"
            return self.append_assistant(text, html=html_block)

        if not destinations:
            return self.append_assistant(
                "ยังไม่เจอข้อมูลที่เกี่ยวข้อง ลองบอกชื่อเมือง ประเทศ หรือสไตล์ทริปเพิ่มเติมอีกนิดนะคะ"
            )

        suggestions_html = self._build_suggestions_html(destinations[:3])
        summary = (
            f"น้องปลาทูรวบรวมที่เที่ยวที่น่าจะตรงกับ “{cleaned}” มาให้ 3 ตัวเลือกแรก ลองดูรายละเอียดด้านล่างได้เลยนะคะ"
        )
        return self.append_assistant(summary, html=suggestions_html)

    def list_messages(self) -> List[Dict[str, object]]:
        return self._store.list()

    def list_since(self, since_iso: str) -> List[Dict[str, object]]:
        return self._store.since(since_iso)

    def _matches_bangkok(self, query: str) -> bool:
        normalized = self._normalize(query)
        return any(self._normalize(keyword) in normalized for keyword in BANGKOK_KEYWORDS)

    def search_destinations(self, query: str) -> List[Dict[str, str]]:
        results = self._search_destinations(query)
        if query.strip():
            return results
        return self._destinations

    def _search_destinations(self, query: str) -> List[Dict[str, str]]:
        normalized = query.lower().strip()
        normalized_no_tone = self._normalize(query)
        if not normalized:
            return self._destinations

        results: List[Dict[str, str]] = []
        for item in self._destinations:
            combined = " ".join([item["name"], item["city"], item["description"]])
            haystack = combined.lower()
            haystack_no_tone = self._normalize(combined)
            if normalized in haystack or normalized_no_tone in haystack_no_tone:
                results.append(item)

        if results:
            return results

        return self._match_by_theme(normalized, normalized_no_tone)

    def _match_by_theme(self, normalized_query: str, normalized_query_no_tone: str) -> List[Dict[str, str]]:
        matches: List[Dict[str, str]] = []
        for keyword, names in THEME_KEYWORDS.items():
            keyword_lower = keyword.lower()
            keyword_no_tone = self._normalize(keyword)
            if keyword_lower in normalized_query or keyword_no_tone in normalized_query_no_tone:
                for item in self._destinations:
                    if item["name"] in names and item not in matches:
                        matches.append(item)
        return matches

    def _looks_travel_related(self, user_input: str, destinations: List[Dict[str, str]]) -> bool:
        normalized = self._normalize(user_input)
        if any(keyword in normalized for keyword in self._normalized_keywords):
            return True
        if any(name in normalized for name in self._normalized_dest_names):
            return True
        if destinations:
            return True
        if self._match_by_theme(user_input.lower().strip(), normalized):
            return True
        return False

    def _build_suggestions_html(self, suggestions: List[Dict[str, str]]) -> str:
        cards: List[str] = []
        for item in suggestions:
            lines_html = f"<li>{html.escape(item['description'])}</li>"
            cards.append(
                (
                    "<article class=\"guide-entry guide-entry--suggestion\">"
                    "<h3>{name} - {city}</h3>"
                    "<ul class=\"guide-lines\">{lines}</ul>"
                    "<p class=\"guide-link\"><a href=\"{map_url}\" target=\"_blank\" rel=\"noopener\">เปิดใน Google Maps</a></p>"
                    "</article>"
                ).format(
                    name=html.escape(item["name"]),
                    city=html.escape(item["city"]),
                    lines=lines_html,
                    map_url=html.escape(item["mapUrl"]),
                )
            )
        return f"<div class=\"guide-response\">{''.join(cards)}</div>"

    @staticmethod
    def _normalize(text: str) -> str:
        decomposed = unicodedata.normalize("NFKD", text.lower().strip())
        return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
