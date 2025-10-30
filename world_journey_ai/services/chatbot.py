from __future__ import annotations

import html
import json
import os
import unicodedata
from typing import Dict, List

from .destinations import BANGKOK_KEYWORDS
from .guides import build_bangkok_guides_html
from .messages import MessageStore

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

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
        
        # Initialize OpenAI client if available
        self._openai_client = None
        if OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                try:
                    self._openai_client = OpenAI(api_key=api_key)
                except Exception:
                    pass

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
                f"น้องปลาทูรวบรวมที่เที่ยวที่น่าจะตรงกับ "{cleaned}" มาให้ 3 ตัวเลือกแรก ลองดูรายละเอียดด้านล่างได้เลยนะคะ"
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
