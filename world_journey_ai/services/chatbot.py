from __future__ import annotations

import difflib
import html
import unicodedata
from typing import Dict, List

from .province_guides import PROVINCE_GUIDES, PROVINCE_SYNONYMS
from .guides import build_bangkok_guides_html
from .messages import MessageStore

TRAVEL_KEYWORDS = (
    "เที่ยว",
    "ทริป",
    "ที่เที่ยว",
    "ท่องเที่ยว",
    "อยากเที่ยว",
    "อยากไป",
    "ไปเที่ยว",
    "เดินทาง",
    "travel",
    "trip",
    "itinerary",
    "journey",
    "vacation",
)

TRAVEL_ONLY_MESSAGE = (
    "ตอนนี้น้องปลาทูช่วยจัดทริปท่องเที่ยวเท่านั้น ลองบอกชื่อจังหวัดหรือสไตล์การเดินทางดูนะคะ"
)

REQUEST_PROVINCE_MESSAGE = (
    "บอกชื่อจังหวัดที่อยากไป พร้อมสไตล์สั้นๆ ได้เลย เดี๋ยวน้องปลาทูคัดให้ 5 จุดค่ะ"
)

NO_DATA_MESSAGE = (
    "ยังไม่มีข้อมูลยืนยันสำหรับจังหวัดหรือสไตล์นั้น ลองเลือกจังหวัดอื่นหรือแจ้งทีมงานเพิ่มเติมได้เลยนะคะ"
)

UNSUPPORTED_PROVINCE_MESSAGE = "ยังไม่รองรับจังหวัดนี้"


CATEGORY_LABELS = [
    "สถานที่ศักดิ์สิทธิ์และประวัติศาสตร์",
    "สถานที่ท่องเที่ยวทางธรรมชาติ",
    "ตลาดชุมชนวัฒนธรรม",
    "พิพิธภัณฑ์อุทยานประวัติศาสตร์",
    "ประสบการณ์พิเศษลองเรือ/กิจกรรมกลางคืน",
]


class ChatEngine:
    def __init__(self, message_store: MessageStore, destinations: List[Dict[str, str]]) -> None:
        self._store = message_store
        self._destinations = destinations
        self._normalized_dest_names = [self._normalize(item["name"]) for item in destinations]
        self._normalized_keywords = [self._normalize(keyword) for keyword in TRAVEL_KEYWORDS]
        self._province_aliases = self._build_province_aliases()

    def append_user(self, text: str) -> Dict[str, object]:
        return self._store.add("user", text)

    def append_assistant(self, text: str, *, html: str | None = None) -> Dict[str, object]:
        return self._store.add("assistant", text, html=html)

    def build_reply(self, user_text: str) -> Dict[str, object]:
        cleaned = user_text.strip()
        if not cleaned:
            return self.append_assistant("ลองพิมพ์ชื่อจังหวัดหรือสไตล์ทริปที่อยากไปนะคะ")

        province = self._resolve_province(cleaned)
        if province:
            entries = PROVINCE_GUIDES.get(province, [])
            if len(entries) < 5:
                return self.append_assistant(
                    f"ยังไม่มีรายการ 5 แห่งสำหรับจังหวัด{province} ในระบบ ลองเปลี่ยนจังหวัดหรือแจ้งทีมงานได้นะคะ"
                )
            if province == "กรุงเทพมหานคร":
                html_block = build_bangkok_guides_html()
                text = self._format_summary_text(province, entries)
                return self.append_assistant(text, html=html_block)
            return self.append_assistant(self._format_summary_text(province, entries))

        return self.append_assistant(UNSUPPORTED_PROVINCE_MESSAGE)

    def list_messages(self) -> List[Dict[str, object]]:
        return self._store.list()

    def list_since(self, since_iso: str) -> List[Dict[str, object]]:
        return self._store.since(since_iso)

    def _resolve_province(self, text: str) -> str | None:
        normalized = self._normalize(text)
        for alias, province in self._province_aliases.items():
            if alias in normalized or normalized in alias:
                return province

        if normalized and self._province_aliases:
            best_province: str | None = None
            best_similarity = 0.0
            for alias, province in self._province_aliases.items():
                distance = self._levenshtein_distance(normalized, alias)
                max_len = max(len(normalized), len(alias)) or 1
                similarity = 1.0 - (distance / max_len)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_province = province
            if best_province and best_similarity >= 0.6:
                return best_province
        return None

    @staticmethod
    def _levenshtein_distance(a: str, b: str) -> int:
        if a == b:
            return 0
        if not a:
            return len(b)
        if not b:
            return len(a)
        previous = list(range(len(b) + 1))
        for i, char_a in enumerate(a, start=1):
            current = [i]
            for j, char_b in enumerate(b, start=1):
                insert_cost = current[j - 1] + 1
                delete_cost = previous[j] + 1
                substitute_cost = previous[j - 1] + (char_a != char_b)
                current.append(min(insert_cost, delete_cost, substitute_cost))
            previous = current
        return previous[-1]

    def search_destinations(self, query: str) -> List[Dict[str, str]]:
        province = self._resolve_province(query)
        if not province:
            return []
        entries = PROVINCE_GUIDES.get(province, [])[:5]
        return [
            {
                "name": entry["name"],
                "city": province,
                "description": entry["summary"],
                "mapUrl": entry["map_url"],
            }
            for entry in entries
        ]

    def _format_summary_text(self, province: str, entries: List[Dict[str, str]]) -> str:
        lines = [f"จังหวัด{province} – เช็กลิสต์ 5 แห่งแบบเร็ว:"]
        lines.append("กิจกรรม:  | เวลาเปิด:  | งบประมาณ: ")
        lines.append("")
        for index, entry in enumerate(entries[:5], start=1):
            category = CATEGORY_LABELS[index - 1] if index - 1 < len(CATEGORY_LABELS) else entry.get("category", f"ลิสต์ที่ {index}")
            name_th = entry.get("name", "")
            name_en = entry.get("english_name", "")
            summary = entry.get("summary", "")
            history = entry.get("history") or "ยังไม่มีข้อมูลยืนยัน"
            activity = entry.get("activity") or "ยังไม่มีข้อมูลยืนยัน"
            hours = entry.get("hours") or "ยังไม่มีข้อมูลยืนยัน"
            budget = entry.get("budget") or "ยังไม่มีข้อมูลยืนยัน"
            map_url = entry.get("map_url", "")
            lines.append(f"{index}) {category}")
            if name_en and map_url:
                lines.append(f"- สถานที่: [{name_th} ({name_en})]({map_url})")
            elif name_en:
                lines.append(f"- สถานที่: {name_th} ({name_en})")
            elif map_url:
                lines.append(f"- สถานที่: [{name_th}]({map_url})")
            else:
                lines.append(f"- สถานที่: {name_th}")
            lines.append(f"  รายละเอียด (Auditory/Conversational Memory): {summary}")
            lines.append(f"  กิจกรรม: {activity} | เวลาเปิด: {hours} | งบประมาณ: {budget}")
            lines.append(f"  ประเด็นเด่นประวัติ: {history}")
            lines.append("")
        if lines and lines[-1] == "":
            lines.pop()
        return "\n".join(lines)

    def _build_province_aliases(self) -> Dict[str, str]:
        aliases: Dict[str, str] = {}
        for province, synonyms in PROVINCE_SYNONYMS.items():
            for value in {province, *synonyms}:
                aliases[self._normalize(value)] = province
        return aliases

    def _looks_travel_related(self, user_input: str) -> bool:
        normalized = self._normalize(user_input)
        if any(keyword in normalized for keyword in self._normalized_keywords):
            return True
        if any(name in normalized for name in self._normalized_dest_names):
            return True
        if self._resolve_province(user_input):
            return True
        return False

    @staticmethod
    def _normalize(text: str) -> str:
        decomposed = unicodedata.normalize("NFKD", text.lower().strip())
        return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


