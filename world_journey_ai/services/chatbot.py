from __future__ import annotations

import difflib
import html
import json
import os
import unicodedata
from typing import Dict, List, TYPE_CHECKING
import re

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
    # Thai - Basic travel terms
    "เที่ยว", "ทริป", "ที่เที่ยว", "ท่องเที่ยว", "อยากเที่ยว", "อยากไป", "ไปเที่ยว", "เดินทาง",
    "ทะเล", "ภูเขา", "วัด", "ตลาด", "คาเฟ่", "โฮมสเตย์", "น้ำตก", "ดำน้ำ", "เดินป่า", "เกาะ",
    "ไนท์มาร์เก็ต", "ตลาดน้ำ", "ชายหาด", "อุทยาน", "สวน", "พิพิธภัณฑ์", "อนุสาวรีย์",
    
    # Thai - Administrative divisions and location queries
    "จังหวัด", "อำเภอ", "ตำบล", "หมู่บ้าน", "เขต", "แขวง", "ย่าน", "ชุมชน", "หมู่", "บ้าน",
    "อยู่ที่ไหน", "ใกล้กับ", "ห่างจาก", "มีอะไรบ้าง", "น่าสนใจ", "แนะนำ", "ช่วยบอก", "อยากรู้",
    "มีที่เที่ยว", "สถานที่ท่องเที่ยว", "จุดท่องเที่ยว", "แหล่งท่องเที่ยว", "ไปเที่ยวที่ไหนดี",
    "ควรไป", "น่าไป", "มีชื่อเสียง", "เด็ด", "ดัง", "โด่งดัง", "มีอะไรดีๆ", "น่าเข้าชม",
    
    # English - Basic travel terms  
    "travel", "trip", "itinerary", "journey", "vacation", "holiday", "beach", "mountain", "temple",
    "market", "night market", "floating market", "cafe", "coffee shop", "homestay", "waterfall",
    "snorkel", "snorkeling", "diving", "hike", "hiking", "island", "old town", "museum", "park",
    
    # English - Administrative divisions and location queries
    "province", "district", "subdistrict", "tambon", "amphoe", "village", "town", "city", "area",
    "where is", "near to", "close to", "far from", "what to see", "what to do", "recommend",
    "suggest", "tell me about", "interesting", "attractions", "tourist spots", "worth visiting",
    "should visit", "must see", "famous for", "known for", "popular", "best places",
)

TRAVEL_ONLY_MESSAGE = (
    "น้องปลาทูช่วยเรื่องสถานที่ท่องเที่ยวได้ค่ะ ลองบอกชื่อเมือง ประเทศ หรือสถานที่ที่อยากรู้จักดูนะคะ"
)


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

        lang = self._detect_language(cleaned)

        # Check if it's a specific query (has specific keywords) vs just a city name
        is_specific_query = self._is_specific_query(cleaned)

        # Check Bangkok - but only use pre-built guide if NOT a specific query
        if self._matches_bangkok(cleaned) and not is_specific_query:
            html_block = build_bangkok_guides_html()
            text = (
                "Here are curated Bangkok day-trip options. Feel free to mix and match!"
                if lang == "en"
                else "นี่คือทริปกรุงเทพที่น้องปลาทูจัดไว้ให้ ลองเลือกหรือปรับตามเวลาได้เลยนะคะ"
            )
            return self.append_assistant(text, html=html_block)

        # Try local destinations first
        destinations = self._search_destinations(cleaned)
        
        # If we have local matches, use them
        if destinations:
            suggestions_html = self._build_suggestions_html(destinations[:3], lang=lang)
            summary = (
                f"I found a few places matching \"{cleaned}\". Here are the first 3."
                if lang == "en"
                else f"น้องปลาทูรวบรวมที่เที่ยวที่น่าจะตรงกับ \"{cleaned}\" มาให้ 3 ตัวเลือกแรก ลองดูรายละเอียดด้านล่างได้เลยนะคะ"
            )
            return self.append_assistant(summary, html=suggestions_html)

        # If no local match and OpenAI is available, use AI to generate response
        if self._openai_client:
            try:
                ai_response = self._generate_ai_travel_response(cleaned, lang=lang)
                if ai_response:
                    text_str = str(ai_response.get("text", ""))
                    html_str = ai_response.get("html")
                    html_val = str(html_str) if html_str else None
                    return self.append_assistant(text_str, html=html_val)
            except Exception as e:
                print(f"OpenAI error: {e}")
        
        # Even if not explicitly travel-related, try to provide location info via AI
        if self._openai_client:
            try:
                general_response = self._generate_ai_travel_response(cleaned, lang=lang)
                if general_response:
                    text_str = str(general_response.get("text", ""))
                    html_str = general_response.get("html")
                    html_val = str(html_str) if html_str else None
                    return self.append_assistant(text_str, html=html_val)
            except Exception as e:
                print(f"OpenAI general info error: {e}")
        
        # Final fallback
        return self.append_assistant(
            "Hello! I'm Platoo, your personal travel guide. Describe any place, scenery, or atmosphere you have in mind, and I'll help you identify the perfect destination that matches what you're looking for. Whether it's a bustling city, peaceful countryside, exotic beach, or cultural landmark - just tell me what you envision!"
            if lang == "en"
            else "สวัสดีค่ะ! น้องปลาทูค่ะ ขอเป็นผู้ช่วยในการแนะนำสถานที่ท่องเที่ยวและจังหวัดต่างๆ ที่น่าสนใจให้คุณได้ไหมคะ บอกลักษณะสถานที่หรือบรรยากาศที่อยากไปเที่ยวมาได้เลยค่ะ น้องปลาทูจะช่วยหาจุดหมายที่เหมาะกับความต้องการของคุณค่ะ"
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

    def _build_suggestions_html(self, suggestions: List[Dict[str, str]], *, lang: str = "th") -> str:
        """Build HTML for destination suggestions"""
        cards: List[str] = []
        for item in suggestions:
            lines_html = f"<li>{html.escape(item.get('description', ''))}</li>"
            cards.append(
                (
                    "<article class=\"guide-entry guide-entry--suggestion\">"
                    "<h3>{name} - {city}</h3>"
                    "<ul class=\"guide-lines\">{lines}</ul>"
                    "<p class=\"guide-link\"><a href=\"{map_url}\" target=\"_blank\" rel=\"noopener\">{map_label}</a></p>"
                    "</article>"
                ).format(
                    name=html.escape(item.get("name", "")),
                    city=html.escape(item.get("city", "")),
                    lines=lines_html,
                    map_url=html.escape(item.get("mapUrl", "")),
                    map_label=("Open in Google Maps" if lang == "en" else "เปิดใน Google Maps"),
                )
            )
        return f"<div class=\"guide-response\">{''.join(cards)}</div>"


    def _generate_ai_travel_response(self, query: str, *, lang: str = "th") -> Dict[str, object] | None:
        """Use OpenAI to generate a travel response for any location"""
        if not self._openai_client:
            return None

        if lang == "en":
            system_prompt = (
                "You are a Thailand travel and geography expert with deep knowledge down to Tambon (sub-district) level.\n"
                "You have extensive knowledge of local communities, villages, and authentic local experiences.\n"
                "When asked about restaurants, cafes, hotels, or specific places, recommend ONLY real, highly-rated places (4+ stars on Google Maps).\n"
                "Reply in English and provide accurate administrative information.\n"
                "CRITICAL RULES:\n"
                "1. Use EXACT real place names from Google Maps - never invent names\n"
                "2. For restaurants/cafes/hotels: recommend popular places with high ratings\n"
                "3. Include specific details (famous dishes, specialties, what they're known for)\n"
                "4. Provide correct administrative information (Province, District, Sub-district)\n"
                "5. Be factual - only mention places you know exist\n"
                "6. If unsure about specific names, describe general area recommendations\n"
                "7. If user asks about Tambon level, provide detailed community-level information\n"
                "Return ONLY valid JSON (no extra text) with this exact structure:\n"
                "{\n"
                '  "location": "Area/district name",\n'
                '  "administrative_info": {\n'
                '    "province": "Province name",\n'
                '    "amphoe": "District name",\n'
                '    "tambon": "Sub-district name (if applicable)"\n'
                '  },\n'
                '  "attractions": [\n'
                '    {"name": "EXACT place name", "description": "What it\'s famous for, specialty items, rating info", "admin_level": "Administrative level"},\n'
                '    {"name": "EXACT place name", "description": "What it\'s famous for, specialty items, rating info", "admin_level": "Administrative level"}\n'
                '  ],\n'
                '  "summary": "Brief overview emphasizing these are popular, highly-rated places with local context"\n'
                "}\n"
                "Be factual and concise. No extra fields."
            )
            # Auto-correct the query before sending to AI
            corrected_query = self._auto_correct_query(query)
            user_prompt = f"List top-rated attractions/places in: {corrected_query}"
        else:
            system_prompt = (
                "คุณคือผู้เชี่ยวชาญด้านการท่องเที่ยวและภูมิศาสตร์ของประเทศไทย\n"
                "คุณมีความรู้ลึกลงไปถึงระดับตำบล หมู่บ้าน และชุมชนท้องถิ่น\n"
                "เมื่อถูกถามเกี่ยวกับร้านอาหาร คาเฟ่ โรงแรม หรือสถานที่เฉพาะ ให้แนะนำเฉพาะสถานที่ที่มีจริง มีรีวิวดี (4 ดาวขึ้นไปใน Google Maps)\n"
                "ตอบเป็นภาษาไทย และให้ข้อมูลการปกครองที่ถูกต้อง\n"
                "กฎสำคัญ:\n"
                "1. ใช้ชื่อสถานที่จริงจาก Google Maps - ห้ามแต่งชื่อขึ้นมาเอง\n"
                "2. สำหรับร้านอาหาร/คาเฟ่/โรงแรม: แนะนำร้านที่มีชื่อเสียง คนรีวิวเยอะ\n"
                "3. ระบุรายละเอียดเฉพาะ (เมนูเด็ด ของแนะนำ จุดเด่น)\n"
                "4. ระบุข้อมูลการปกครองที่ถูกต้อง (จังหวัด อำเภอ ตำบล)\n"
                "5. ต้องเป็นข้อมูลจริง - แนะนำแต่สถานที่ที่มั่นใจว่ามีอยู่จริง\n"
                "6. ถ้าไม่แน่ใจชื่อเฉพาะ ให้บอกลักษณะพื้นที่และประเภทร้านทั่วไป\n"
                "7. หากผู้ใช้ถามในระดับตำบล ให้ข้อมูลละเอียดระดับชุมชนท้องถิ่น\n"
                "ส่งกลับเฉพาะ JSON ที่ถูกต้อง (ไม่มีข้อความอื่น) ตามโครงสร้างนี้:\n"
                "{\n"
                '  "location": "ชื่อพื้นที่/ย่าน",\n'
                '  "administrative_info": {\n'
                '    "province": "ชื่อจังหวัด",\n'
                '    "amphoe": "ชื่ออำเภอ",\n'
                '    "tambon": "ชื่อตำบล (ถ้ามี)"\n'
                '  },\n'
                '  "attractions": [\n'
                '    {"name": "ชื่อสถานที่จริง", "description": "มีชื่อเสียงเรื่องอะไร เมนูเด็ด ข้อมูลรีวิว", "admin_level": "ระดับการปกครอง"},\n'
                '    {"name": "ชื่อสถานที่จริง", "description": "มีชื่อเสียงเรื่องอะไร เมนูเด็ด ข้อมูลรีวิว", "admin_level": "ระดับการปกครอง"}\n'
                '  ],\n'
                '  "summary": "สรุปแบบสั้นๆ เน้นว่าเป็นร้านที่คนนิยม มีรีวิวดี พร้อมข้อมูลท้องถิ่น"\n'
                "}\n"
                "ให้ข้อมูลจริง กระชับ ไม่มีฟิลด์อื่น"
            )
        # Auto-correct the query before sending to AI
        corrected_query = self._auto_correct_query(query)
        
        # Enhanced: Check for administrative level context  
        admin_context = self._detect_admin_level(corrected_query)
        if admin_context != "general":
            user_prompt = f"แนะนำสถานที่ยอดนิยมที่มีรีวิวดีในระดับ{admin_context}: {corrected_query}"
        else:
            user_prompt = f"แนะนำสถานที่ยอดนิยมที่มีรีวิวดีใน: {corrected_query}"

        try:
            response = self._openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=600
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
                    "text": data.get(
                        "summary",
                        (
                            f"Here is what I found about {query}."
                            if lang == "en"
                            else f"นี่คือข้อมูลเกี่ยวกับ {query} ที่น้องปลาทูหามาให้นะคะ"
                        ),
                    ),
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
        """Build HTML from AI-generated travel data - enhanced with administrative info"""
        attractions = data.get("attractions", [])
        admin_info = data.get("administrative_info", {})
        
        if not attractions:
            return ""

        # Build administrative info section
        admin_html = ""
        if admin_info:
            admin_parts = []
            if admin_info.get("province"):
                admin_parts.append(f"จังหวัด{admin_info['province']}")
            if admin_info.get("amphoe"):
                admin_parts.append(f"อำเภอ{admin_info['amphoe']}")
            if admin_info.get("tambon"):
                admin_parts.append(f"ตำบล{admin_info['tambon']}")
            
            if admin_parts:
                admin_html = f'<div class="administrative-info"><strong>ข้อมูลการปกครอง:</strong> {" > ".join(admin_parts)}</div>'

        cards: List[str] = []
        location = html.escape(data.get("location", ""))
        
        for item in attractions:
            name = html.escape(item.get("name", ""))
            description = html.escape(item.get("description", ""))
            admin_level = html.escape(item.get("admin_level", ""))
            
            # Build Google Maps search URL with enhanced location context
            if admin_info.get("province"):
                map_query = f"{name} {admin_info['province']}".replace(" ", "+")
            else:
                map_query = f"{name} {location}".replace(" ", "+")
            map_url = f"https://www.google.com/maps/search/?api=1&query={map_query}"
            
            # Add admin level badge if available
            level_badge = f'<span class="admin-level-badge">{admin_level}</span>' if admin_level else ""
            
            cards.append(
                (
                    "<article class=\"guide-entry guide-entry--suggestion\">"
                    "<h3>{name} {level_badge}</h3>"
                    "<ul class=\"guide-lines\"><li>{description}</li></ul>"
                    "<p class=\"guide-link\"><a href=\"{map_url}\" target=\"_blank\" rel=\"noopener\">เปิดใน Google Maps</a></p>"
                    "</article>"
                ).format(
                    name=name,
                    level_badge=level_badge,
                    description=description,
                    map_url=map_url,
                )
            )
        
        return f"<div class=\"guide-response guide-response--enhanced\">{admin_html}{''.join(cards)}</div>"

    def list_messages(self) -> List[Dict[str, object]]:
        return self._store.list()

    def list_since(self, since_iso: str) -> List[Dict[str, object]]:
        return self._store.since(since_iso)

    def _resolve_province(self, text: str) -> str | None:
        normalized = self._normalize(text)
        # 1) Exact/substring match first (most reliable)
        for alias, province in self._province_aliases.items():
            if alias == normalized or (alias in normalized and len(alias) >= 4):
                return province

        # 2) Fuzzy match with ambiguity guard
        if normalized and self._province_aliases:
            scored: List[tuple[str, float]] = []
            for alias in self._province_aliases.keys():
                distance = self._levenshtein_distance(normalized, alias)
                max_len = max(len(normalized), len(alias)) or 1
                similarity = 1.0 - (distance / max_len)
                scored.append((alias, similarity))

            # sort by similarity desc
            scored.sort(key=lambda x: x[1], reverse=True)
            if not scored:
                return None
            top_alias, top_sim = scored[0]
            second_sim = scored[1][1] if len(scored) > 1 else 0.0

            # If too ambiguous (very close top-2), don't guess
            if top_sim >= 0.8 and (top_sim - second_sim) >= 0.1:
                return self._province_aliases[top_alias]
            # For medium similarity, require stronger lead
            if top_sim >= 0.7 and (top_sim - second_sim) >= 0.2:
                return self._province_aliases[top_alias]
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

    @staticmethod
    def _detect_language(text: str) -> str:
        """Very light language detection: 'en' if mostly ASCII letters, 'th' if Thai chars present."""
        if re.search(r"[\u0E00-\u0E7F]", text):
            return "th"
        # count ascii letters proportion
        letters = re.findall(r"[A-Za-z]", text)
        if letters and (len(letters) / max(len(text), 1)) >= 0.3:
            return "en"
        # fallback to Thai
        return "th"

    @staticmethod
    def _is_specific_query(text: str) -> bool:
        """Check if query contains specific search terms (not just a city name)"""
        normalized = text.lower()
        
        # Specific activity/place type keywords
        specific_keywords = [
            # Thai
            "ร้าน", "คาเฟ่", "กาแฟ", "ร้านอาหาร", "โรงแรม", "ที่พัก", "มัสยิด",
            "ตลาด", "ห้าง", "ช้อปปิ้ง", "สวน", "พิพิธภัณฑ์", "ชายหาด", "หาด",
            "น้ำตก", "ภูเขา", "วิว", "ดำน้ำ", "เดินป่า", "ปีนเขา",
            "โฮมสเตย์", "รีสอร์ท", "บาร์", "ผับ", "คลับ", "นวด", "สปา",
            # English
            "cafe", "coffee", "shop", "restaurant", "hotel", "accommodation",
            "mosque", "temple", "market", "mall", "shopping", "park", "museum",
            "beach", "waterfall", "mountain", "view", "diving", "hiking", "climbing",
            "homestay", "resort", "bar", "pub", "club", "massage", "spa",
            "best", "top", "recommend", "suggestion", "where",
            # Question words
            "อะไร", "ไหน", "แนะนำ", "ดี", "สวย", "เด็ด",
        ]
        
        # Check if any specific keyword is in the query
        for keyword in specific_keywords:
            if keyword in normalized:
                return True
        
        return False

    def _auto_correct_query(self, query: str) -> str:
        """Auto-correct common typos in place names and common Thai/English words using advanced fuzzy matching"""
        # Known correct spellings - places AND common words
        known_places = {
            # Thai Markets
            "ตลาดร่มหุบ": ["ตลาดร่มหัก", "ตลาดร่อมหุบ", "ตลาดโรมหุบ", "รมหุบ"],
            "ตลาดน้ำดำเนินสะดวก": ["ตลาดดำเนินสะดวก", "ตลาดน้ำดำเนิน", "ดำเนินสะดวก", "ตลาดน้ำดำเนินสะดวก"],
            "ตลาดจตุจักร": ["จตุจัก", "ตลาดจตุจัก", "ตลาดจะตุจัก", "จตุจักร", "ตลาดจะตุจักร"],
            "ตลาดน้ำอัมพวา": ["อัมพวา", "ตลาดอัมพวา", "อำพวา", "ตลาดอำพวา"],
            # Thai Temples
            "วัดพระแก้ว": ["วัดพระแก้ว", "วัดพระแกว", "พระแก้ว"],
            "วัดอรุณราชวราราม": ["วัดอรุณ", "วัดอรุน", "วัดอะรุณ", "อรุณราชวราราม"],
            "วัดโพธิ์": ["วัดโพธิ", "วัดโพธ", "โพธิ์"],
            "วัดพระธาตุดอยสุเทพ": ["วัดดอยสุเทพ", "ดอยสุเทพ", "วัดพระธาตุดอยสุเทพ"],
            # Thai Provinces (long names)
            "สมุทรสงคราม": ["สมุทสงคราม", "สมุทรสงคราม", "สมุทรสงคาม"],
            "สมุทรสาคร": ["สมุทสาคร", "สมุทรสาคร", "สมุทสาคร"],
            "นครปฐม": ["นครปถม", "นคปฐม", "นครปฐม"],
            "นครราชสีมา": ["นครราชสีมะ", "โคราช", "นครราชสีมา"],
            "อุบลราชธานี": ["อุบล", "อุบลราชธานี", "อุบลราชทานี"],
            "พระนครศรีอยุธยา": ["อยุธยา", "พระนครศรีอยุธยา", "พระนครศรีอยุทยา"],
            # Thai Cities
            "เชียงใหม่": ["เชียงใหม", "เชียงใหมา", "เชียงใหม่"],
            "กรุงเทพมหานคร": ["กรุงเทพ", "กรุงเทพฯ", "กทม", "กรุงเทพมหานคร"],
            # Common Thai words (non-location)
            "ร้านกาแฟ": ["ร้านกาแฟ", "ร้านกาแฟ", "ร้านกาเฟ", "ร้านคาเฟ่"],
            "ร้านอาหาร": ["ร้านอาหาร", "ร้านอาหาร", "ร้านอาหาร"],
            "โรงแรม": ["โรงแรม", "โรงเเรม"],
            "ที่พัก": ["ที่พัก", "ทีพัก"],
            "พิพิธภัณฑ์": ["พิพิธภัณฑ์", "พิพิทธภัณฑ์", "พิพิธภัณฑ์"],
            "อนุสาวรีย์": ["อนุสาวรีย์", "อนุสาวรีย์", "อนุสาวะรีย์"],
            # English place names
            "Bangkok": ["bangok", "bankok", "bangkog", "bangkkok"],
            "Chiang Mai": ["chiangmai", "chaing mai", "chiang my", "chiangmy"],
            "Phuket": ["puket", "phucket", "pukhet", "phukhet"],
            "Pattaya": ["pataya", "phataya", "patthaya", "phatthaya"],
            "Ayutthaya": ["ayuthaya", "ayudhya", "ayutaya", "ayuttaya"],
            "Krabi": ["karbi", "krapi", "kraby"],
            "Nakhon Ratchasima": ["korat", "nakhon ratchasima", "nakorn ratchasima"],
            # Common English words
            "restaurant": ["resturant", "restaurnt", "restaraunt"],
            "hotel": ["hotell", "hotle"],
            "museum": ["musem", "musuem"],
            "temple": ["templ", "tempel"],
            "monument": ["monumnt", "monumet"],
        }
        
        # Build a flat list of all correct names
        all_correct_names = list(known_places.keys())
        
        # Words to preserve (don't try to correct these)
        preserve_words = {
            # Thai prepositions and connectors
            "ใกล้", "ใน", "ที่", "ของ", "และ", "หรือ", "กับ", "แล้ว", "จาก", "ไป",
            "มา", "อยู่", "เป็น", "ได้", "ให้", "จะ", "ไหม", "นะ", "คะ", "ครับ",
            "สำหรับ", "เพื่อ", "ถึง", "ตั้งแต่", "จนถึง", "ระหว่าง",
            # English prepositions and connectors
            "near", "in", "at", "to", "from", "with", "and", "or", "for", "by",
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "have",
            "has", "had", "do", "does", "did", "will", "would", "can", "could",
            "around", "between", "about", "of", "on", "off",
            # Common short words (1-2 chars)
            "ที", "ใน", "ไป", "มา", "อยู", "ไว", "ได", "แล", "ไม", "ใน",
        }
        
        # First, try to match the entire query (for long compound words)
        query_lower = query.lower().strip()
        best_full_match = None
        best_full_score = 0.0
        
        for correct_name in all_correct_names:
            # Check direct typo list for full query match
            if correct_name in known_places:
                for typo in known_places[correct_name]:
                    if query_lower == typo.lower():
                        return correct_name
            
            # For long words (>8 chars), use more lenient matching
            min_chars = max(len(query_lower), len(correct_name.lower()))
            if min_chars >= 8:
                # Use multiple similarity measures for better accuracy
                seq_ratio = difflib.SequenceMatcher(None, query_lower, correct_name.lower()).ratio()
                
                # Also check if query is substring of correct name or vice versa
                contains_score = 0.0
                if query_lower in correct_name.lower():
                    contains_score = len(query_lower) / len(correct_name.lower())
                elif correct_name.lower() in query_lower:
                    contains_score = len(correct_name.lower()) / len(query_lower)
                
                # Combined score (weighted average)
                combined_score = (seq_ratio * 0.7) + (contains_score * 0.3)
                
                # Lower threshold for long words (75% instead of 80%)
                if combined_score > 0.75 and combined_score > best_full_score:
                    best_full_score = combined_score
                    best_full_match = correct_name
            else:
                # Short words use strict matching (80%+)
                similarity = difflib.SequenceMatcher(None, query_lower, correct_name.lower()).ratio()
                if similarity > 0.8 and similarity > best_full_score:
                    best_full_score = similarity
                    best_full_match = correct_name
        
        # If we found a good full match, return it
        if best_full_match and best_full_score >= 0.75:
            return best_full_match
        
        # Otherwise, check word by word (for multi-word queries)
        words = query.split()
        corrected_words = []
        
        for word in words:
            # Skip very short words and preserved words
            if len(word) <= 2 or word.lower() in preserve_words:
                corrected_words.append(word)
                continue
            
            best_match = word
            best_score = 0.0
            word_lower = word.lower()
            
            # Try to find a close match in known places
            for correct_name in all_correct_names:
                # Check direct typo list first
                if correct_name in known_places:
                    for typo in known_places[correct_name]:
                        if word_lower == typo.lower():
                            best_match = correct_name
                            best_score = 1.0
                            break
                
                if best_score >= 1.0:
                    break
                
                # Use fuzzy matching for similar words
                similarity = difflib.SequenceMatcher(None, word_lower, correct_name.lower()).ratio()
                
                # Adaptive threshold based on word length
                threshold = 0.75 if len(word) >= 8 else 0.8
                
                if similarity > threshold and similarity > best_score:
                    best_score = similarity
                    best_match = correct_name
            
            corrected_words.append(best_match)
        
        corrected = " ".join(corrected_words)
        
        # Log correction if something changed (optional - can be disabled in production)
        # Disabled by default to avoid encoding issues in some terminals
        # if corrected != query:
        #     print(f"Auto-corrected: '{query}' -> '{corrected}'")
        
        return corrected

    def _detect_admin_level(self, query: str) -> str:
        """Detect the administrative level mentioned in the query"""
        normalized_query = query.lower()
        
        # Check for specific administrative level keywords
        admin_keywords = {
            "ตำบล": "ตำบล",
            "tambon": "ตำบล", 
            "sub-district": "ตำบล",
            "subdistrict": "ตำบล",
            "อำเภอ": "อำเภอ",
            "amphoe": "อำเภอ",
            "district": "อำเภอ",
            "จังหวัด": "จังหวัด",
            "province": "จังหวัด",
            "หมู่บ้าน": "หมู่บ้าน",
            "village": "หมู่บ้าน",
            "หมู่": "หมู่บ้าน",
            "เขต": "เขต",
            "แขวง": "แขวง",
            "ย่าน": "ย่าน",
            "area": "ย่าน",
            "neighborhood": "ย่าน"
        }
        
        for keyword, level in admin_keywords.items():
            if keyword in normalized_query:
                return level
                
        # If no specific level mentioned, return general
        return "general"

