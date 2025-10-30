from __future__ import annotations

import difflib
import html
import json
import os
import unicodedata
from typing import Dict, List, TYPE_CHECKING

from .province_guides import PROVINCE_GUIDES, PROVINCE_SYNONYMS
from .guides import build_bangkok_guides_html
from .messages import MessageStore

if TYPE_CHECKING:
    from openai import OpenAI

try:
    from openai import OpenAI as OpenAIClient
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAIClient = None  # type: ignore

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
        
        # Initialize OpenAI client if available
        self._openai_client = None
        if OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                try:
                    self._openai_client = OpenAIClient(api_key=api_key)  # type: ignore
                except Exception:
                    pass
        self._province_aliases = self._build_province_aliases()

    def append_user(self, text: str) -> Dict[str, object]:
        return self._store.add("user", text)

    def append_assistant(self, text: str, *, html: str | None = None) -> Dict[str, object]:
        return self._store.add("assistant", text, html=html)

    def build_reply(self, user_text: str) -> Dict[str, object]:
        cleaned = user_text.strip()
        if not cleaned:
            return self.append_assistant("ลองพิมพ์ชื่อเมืองหรือสไตล์การเดินทางที่อยากไปนะคะ")

        # Check Bangkok first (special case with pre-built guides)
        if self._matches_bangkok(cleaned):
            html_block = build_bangkok_guides_html()
            text = "นี่คือทริปกรุงเทพที่น้องปลาทูจัดไว้ให้ ลองเลือกหรือปรับตามเวลาได้เลยนะคะ"
            return self.append_assistant(text, html=html_block)

        # Try local destinations first
        destinations = self._search_destinations(cleaned)
        
        # If we have local matches, use them
        if destinations:
            suggestions_html = self._build_suggestions_html(destinations[:3])
            summary = (
                f"น้องปลาทูรวบรวมที่เที่ยวที่น่าจะตรงกับ \"{cleaned}\" มาให้ 3 ตัวเลือกแรก ลองดูรายละเอียดด้านล่างได้เลยนะคะ"
            )
            return self.append_assistant(summary, html=suggestions_html)

        # If no local match and OpenAI is available, use AI to generate response
        if self._openai_client:
            try:
                ai_response = self._generate_ai_travel_response(cleaned)
                if ai_response:
                    text_str = str(ai_response.get("text", ""))
                    html_str = ai_response.get("html")
                    html_val = str(html_str) if html_str else None
                    return self.append_assistant(text_str, html=html_val)
            except Exception as e:
                print(f"OpenAI error: {e}")
        
        # Fallback: check if it looks travel-related
        if not self._looks_travel_related(cleaned, destinations):
            return self.append_assistant(TRAVEL_ONLY_MESSAGE)

        return self.append_assistant(
            "ยังไม่เจอข้อมูลที่เกี่ยวข้อง ลองบอกชื่อเมือง ประเทศ หรือสไตล์ทริปเพิ่มเติมอีกนิดนะคะ"
        )

    def _matches_bangkok(self, query: str) -> bool:
        """Check if query matches Bangkok keywords"""
        from .destinations import BANGKOK_KEYWORDS
        normalized = self._normalize(query)
        return any(self._normalize(keyword) in normalized for keyword in BANGKOK_KEYWORDS)

    def _search_destinations(self, query: str) -> List[Dict[str, str]]:
        """Search through destinations list"""
        normalized = query.lower().strip()
        normalized_no_tone = self._normalize(query)
        if not normalized:
            return self._destinations

        results: List[Dict[str, str]] = []
        for item in self._destinations:
            combined = " ".join([item["name"], item.get("city", ""), item.get("description", "")])
            haystack = combined.lower()
            haystack_no_tone = self._normalize(combined)
            if normalized in haystack or normalized_no_tone in haystack_no_tone:
                results.append(item)

        return results

    def _build_suggestions_html(self, suggestions: List[Dict[str, str]]) -> str:
        """Build HTML for destination suggestions"""
        cards: List[str] = []
        for item in suggestions:
            lines_html = f"<li>{html.escape(item.get('description', ''))}</li>"
            cards.append(
                (
                    "<article class=\"guide-entry guide-entry--suggestion\">"
                    "<h3>{name} - {city}</h3>"
                    "<ul class=\"guide-lines\">{lines}</ul>"
                    "<p class=\"guide-link\"><a href=\"{map_url}\" target=\"_blank\" rel=\"noopener\">เปิดใน Google Maps</a></p>"
                    "</article>"
                ).format(
                    name=html.escape(item.get("name", "")),
                    city=html.escape(item.get("city", "")),
                    lines=lines_html,
                    map_url=html.escape(item.get("mapUrl", "")),
                )
            )
        return f"<div class=\"guide-response\">{''.join(cards)}</div>"


    def _generate_ai_travel_response(self, query: str) -> Dict[str, object] | None:
        """Use OpenAI to generate a travel response for any location"""
        if not self._openai_client:
            return None

        system_prompt = """คุณคือน้องปลาทู AI ผู้ช่วยวางแผนการท่องเที่ยว 
คุณต้องตอบคำถามเกี่ยวกับการท่องเที่ยวเท่านั้น โดยเฉพาะสถานที่ท่องเที่ยวในประเทศไทย
ให้คำแนะนำแบบกันเองและเป็นมิตร ใช้ภาษาไทย
ถ้าผู้ใช้ถามเกี่ยวกับสถานที่ท่องเที่ยว ให้แนะนำ 3-5 สถานที่ยอดนิยมหรือกิจกรรมที่น่าสนใจ พร้อมคำอธิบายสั้นๆ
จัดรูปแบบเป็น JSON ที่มี: 
{
  "location": "ชื่อสถานที่",
  "attractions": [
    {"name": "ชื่อสถานที่ท่องเที่ยว", "description": "คำอธิบายสั้นๆ", "type": "ประเภท เช่น ทะเล ภูเขา วัด ช้อปปิ้ง"}
  ],
  "summary": "สรุปแบบกันเองสั้นๆ"
}"""

        try:
            response = self._openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"ช่วยแนะนำที่เที่ยวเกี่ยวกับ: {query}"}
                ],
                temperature=0.7,
                max_tokens=800
            )

            content = response.choices[0].message.content
            
            # Check if content is None
            if not content:
                return None
            
            # Try to extract JSON from the response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
                
                # Build HTML from AI response
                html_content = self._build_ai_response_html(data)
                
                return {
                    "text": data.get("summary", f"นี่คือข้อมูลเกี่ยวกับ {query} ที่น้องปลาทูหามาให้นะคะ"),
                    "html": html_content
                }
            else:
                # If JSON parsing fails, return the raw response as plain text
                plain_html = f'<div class="guide-response"><p>{html.escape(content)}</p></div>'
                return {
                    "text": content[:200] + "..." if len(content) > 200 else content,
                    "html": plain_html
                }

        except Exception as e:
            print(f"AI generation error: {e}")
            return None

    def _build_ai_response_html(self, data: Dict) -> str:
        """Build HTML from AI-generated travel data"""
        attractions = data.get("attractions", [])
        if not attractions:
            return ""

        cards: List[str] = []
        location = html.escape(data.get("location", ""))
        
        for item in attractions:
            name = html.escape(item.get("name", ""))
            description = html.escape(item.get("description", ""))
            item_type = html.escape(item.get("type", ""))
            
            map_query = f"{name} {location}".replace(" ", "+")
            map_url = f"https://www.google.com/maps/search/?api=1&query={map_query}"
            
            cards.append(
                (
                    "<article class=\"guide-entry guide-entry--suggestion\">"
                    "<h3>{name}</h3>"
                    "<p class=\"guide-type\">ประเภท: {item_type}</p>"
                    "<ul class=\"guide-lines\"><li>{description}</li></ul>"
                    "<p class=\"guide-link\"><a href=\"{map_url}\" target=\"_blank\" rel=\"noopener\">เปิดใน Google Maps</a></p>"
                    "</article>"
                ).format(
                    name=name,
                    item_type=item_type,
                    description=description,
                    map_url=map_url,
                )
            )
        
        return f"<div class=\"guide-response\">{''.join(cards)}</div>"

    def _old_build_reply(self, user_text: str) -> Dict[str, object]:
        """Old province-based reply logic (kept for reference)"""
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

    def _looks_travel_related(self, user_input: str, destinations: List[Dict[str, str]] | None = None) -> bool:
        normalized = self._normalize(user_input)
        if any(keyword in normalized for keyword in self._normalized_keywords):
            return True
        if any(name in normalized for name in self._normalized_dest_names):
            return True
        if destinations:  # If we have destination matches, it's travel-related
            return True
        if self._resolve_province(user_input):
            return True
        return False

    @staticmethod
    def _normalize(text: str) -> str:
        decomposed = unicodedata.normalize("NFKD", text.lower().strip())
        return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


