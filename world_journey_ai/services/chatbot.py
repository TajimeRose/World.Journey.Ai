from __future__ import annotations

import difflib
import html
import json
import os
import unicodedata
import hashlib
import time
from typing import Dict, List, TYPE_CHECKING
import re

from .province_guides import PROVINCE_GUIDES, PROVINCE_SYNONYMS
from .guides import build_bangkok_guides_html
from .messages import MessageStore
from .enhanced_knowledge import enhanced_knowledge, PlaceKnowledge

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

GUIDE_ONLY_MESSAGE = (
    "สวัสดีค่ะ! น้องปลาทูพร้อมช่วยวางแผนทริปให้คุณแล้วค่ะ บอกปลายทาง งบประมาณ และระยะเวลาที่ต้องการได้เลยนะคะ"
)


CATEGORY_LABELS = [
    "สถานที่ศักดิ์สิทธิ์และประวัติศาสตร์",
    "สถานที่ท่องเที่ยวทางธรรมชาติ",
    "ตลาดชุมชนวัฒนธรรม",
    "พิพิธภัณฑ์อุทยานประวัติศาสตร์",
    "ประสบการณ์พิเศษลองเรือ/กิจกรรมกลางคืน",
]


class BaseAIEngine:
    """Base class for AI engines with common functionality"""
    
    def __init__(self, message_store: MessageStore, destinations: List[Dict[str, str]], ai_mode: str = "general") -> None:
        self._store = message_store
        self._destinations = destinations
        self._ai_mode = ai_mode  # "chat", "guide", or "general"
        self._normalized_dest_names = [self._normalize(item["name"]) for item in destinations]
        self._normalized_keywords = [self._normalize(keyword) for keyword in TRAVEL_KEYWORDS]
        
        # Initialize enhanced knowledge system
        self.enhanced_knowledge = enhanced_knowledge
        
        # Initialize caching system for 95% accuracy
        self._response_cache: Dict[str, Dict[str, object]] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_max_age = 3600  # 1 hour cache timeout
        self._cache_max_size = 1000  # Maximum cache entries
        
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

    def _validate_and_preprocess_input(self, user_text: str) -> Dict[str, object] | None:
        """Comprehensive input validation and preprocessing for 95% accuracy"""
        # Step 1: Basic validation
        if not isinstance(user_text, str):
            return {"error": "อินพุตต้องเป็น string เท่านั้น"}
        
        cleaned = user_text.strip()
        if not cleaned:
            return {"error": "กรุณาใส่ข้อความ"}
        
        if len(cleaned) > 1000:
            return {"error": "ข้อความยาวเกินไป กรุณาใส่ไม่เกิน 1000 ตัวอักษร"}
        
        # Step 2: Security validation
        suspicious_patterns = [
            r'<script[^>]*>.*?</script>',  # Script injection
            r'javascript:',               # JavaScript URLs
            r'data:text/html',           # Data URLs
            r'vbscript:',                # VBScript
            r'on\w+\s*=',               # Event handlers
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, cleaned, re.IGNORECASE):
                return {"error": "ข้อความมีเนื้อหาที่ไม่ปลอดภัย"}
        
        # Step 3: Content type validation
        spam_patterns = [
            r'^\s*[!@#$%^&*()_+={}\[\]|\\:";\'<>?,./-]+\s*$',  # Only special characters
            r'^(.)\1{10,}$',                                    # Repeated characters
            r'^(test|testing|123|aaa|xxx)\s*$',                # Test strings
        ]
        
        for pattern in spam_patterns:
            if re.search(pattern, cleaned, re.IGNORECASE):
                return {"error": "กรุณาใส่คำถามเกี่ยวกับการท่องเที่ยว"}
        
        # Step 4: Language detection and normalization
        processed_text = self._normalize_input_text(cleaned)
        
        # Step 5: Travel relevance scoring
        relevance_score = self._calculate_travel_relevance(processed_text)
        
        return {
            "original": user_text,
            "cleaned": cleaned,
            "processed": processed_text,
            "relevance_score": relevance_score,
            "is_valid": True
        }

    def _normalize_input_text(self, text: str) -> str:
        """Advanced text normalization for better AI understanding"""
        # Remove excessive whitespace and normalize
        normalized = re.sub(r'\s+', ' ', text.strip())
        
        # Fix common Thai typing errors
        thai_corrections = {
            'เช่ยงใหม่': 'เชียงใหม่',
            'ภูเก็ต': 'ภูเก็ต',
            'กระบี่': 'กระบี่',
            'พัทยา': 'พัทยา',
            'หัวหิน': 'หัวหิน',
            'เก่าะ': 'เกาะ',
            'เข่าะ': 'เกาะ',
            'ป่าตอง': 'ป่าตอง',
            'จันท์บุรี': 'จันทบุรี',
            'ระยอง': 'ระยอง',
        }
        
        for incorrect, correct in thai_corrections.items():
            normalized = normalized.replace(incorrect, correct)
        
        # Normalize English place names
        english_corrections = {
            'bangok': 'bangkok',
            'chiangmai': 'chiang mai',
            'phuket': 'phuket',
            'krabi': 'krabi',
            'pattaya': 'pattaya',
            'huahin': 'hua hin',
            'kohsamui': 'koh samui',
            'kohphiphi': 'koh phi phi',
        }
        
        normalized_lower = normalized.lower()
        for incorrect, correct in english_corrections.items():
            normalized_lower = normalized_lower.replace(incorrect, correct)
            
        # Preserve original case for Thai text, but fix English
        words = normalized.split()
        corrected_words = []
        
        for word in words:
            if self._is_english_word(word):
                corrected_word = english_corrections.get(word.lower(), word.lower())
                corrected_words.append(corrected_word.title() if corrected_word in ['Bangkok', 'Phuket', 'Krabi', 'Pattaya'] else corrected_word)
            else:
                corrected_words.append(word)
        
        return ' '.join(corrected_words)

    def _is_english_word(self, word: str) -> bool:
        """Check if word is English"""
        return bool(re.match(r'^[a-zA-Z\s\'-]+$', word))

    def _calculate_travel_relevance(self, text: str) -> float:
        """Calculate how relevant the text is to travel (0.0 to 1.0)"""
        text_lower = text.lower()
        normalized_text = self._normalize(text)
        
        # Travel keyword scoring
        travel_score = 0.0
        total_keywords = len(self._normalized_keywords)
        
        for keyword in self._normalized_keywords:
            if keyword in normalized_text:
                travel_score += 1.0
        
        # Destination scoring
        destination_score = 0.0
        total_destinations = len(self._normalized_dest_names)
        
        for dest in self._normalized_dest_names:
            if dest in normalized_text:
                destination_score += 2.0  # Destinations are more important
        
        # Question pattern scoring
        question_patterns = [
            r'\b(where|what|how|when|which|who)\b',
            r'\b(ไป|เที่ยว|ที่ไหน|อยากไป|แนะนำ|ช่วย)\b',
            r'\?',
        ]
        
        question_score = 0.0
        for pattern in question_patterns:
            if re.search(pattern, text_lower):
                question_score += 0.5
        
        # Calculate final relevance score
        max_possible_score = 5.0  # Reasonable maximum
        total_score = min(travel_score + destination_score + question_score, max_possible_score)
        relevance = total_score / max_possible_score
        
        return min(relevance, 1.0)

    def _get_system_prompt(self, *, lang: str = "th") -> str:
        """Get the system prompt for AI responses - to be overridden by subclasses"""
        if lang == "en":
            return (
                "You are an EXPERT global travel consultant with deep knowledge of destinations worldwide.\n"
                "Your expertise covers detailed geographical, cultural, and practical information for both major cities and hidden gems.\n"
                "\nCOMPREHENSIVE KNOWLEDGE BASE:\n"
                "• Administrative divisions: Countries → States/Provinces → Cities → Districts → Neighborhoods\n"
                "• Cultural context: History, traditions, festivals, etiquette, local customs\n"
                "• Practical information: Transportation, accommodation, dining, safety, climate\n"
                "• Hidden gems: Lesser-known attractions, local favorites, off-the-beaten-path experiences\n"
                "• Real-time considerations: Seasonal variations, current events, accessibility\n"
                "\nACCURACY & VERIFICATION STANDARDS:\n"
                "1. NEVER fabricate place names, businesses, or specific details\n"
                "2. For establishments: Only recommend places with verified good reputation\n"
                "3. Include precise location information when available\n"
                "4. Cross-reference multiple knowledge sources mentally\n"
                "5. Specify confidence level and information recency\n"
                "6. Provide alternatives if primary recommendations may be unavailable\n"
                "7. Include cultural context and local insights\n"
                "8. Consider seasonal factors and timing\n"
                "\nRESPONSE ENHANCEMENT:\n"
                "• Provide multi-layered information: basic facts + insider tips\n"
                "• Include historical and cultural background\n"
                "• Suggest complementary experiences and combinations\n"
                "• Mention practical considerations (budget ranges, time needed, difficulty level)\n"
                "• Offer personalization based on traveler type\n"
                "• Include sustainable and responsible travel options\n"
                "\nKNOWLEDGE DEPTH AREAS:\n"
                "🌏 ASIA: Thailand (expert level), Japan, South Korea, China, Southeast Asia\n"
                "🌍 EUROPE: Western Europe, Eastern Europe, Nordic countries\n"
                "🌎 AMERICAS: North America, Central America, South America\n"
                "🌍 AFRICA & MIDDLE EAST: Major destinations and cultural sites\n"
                "🌏 OCEANIA: Australia, New Zealand, Pacific islands\n"
                "\nRETURN FORMAT: Comprehensive JSON with enhanced details\n"
                "{\n"
                '  "destination": {\n'
                '    "name": "Official destination name",\n'
                '    "local_name": "Name in local language",\n'
                '    "administrative_info": {\n'
                '      "country": "Country name",\n'
                '      "region": "State/Province/Region",\n'
                '      "city": "City/Municipality",\n'
                '      "district": "District/Area (if applicable)"\n'
                '    },\n'
                '    "coordinates": "Latitude, Longitude (if relevant)"\n'
                '  },\n'
                '  "overview": {\n'
                '    "description": "Comprehensive destination overview",\n'
                '    "best_known_for": ["Key highlights and unique features"],\n'
                '    "traveler_types": ["Who would most enjoy this destination"]\n'
                '  },\n'
                '  "attractions": [\n'
                '    {\n'
                '      "name": "Attraction name",\n'
                '      "category": "Type of attraction",\n'
                '      "description": "What makes it special, what to expect",\n'
                '      "practical_info": "Hours, pricing, access info",\n'
                '      "insider_tips": "Local insights and recommendations",\n'
                '      "best_time": "Optimal timing for visit"\n'
                '    }\n'
                '  ],\n'
                '  "cultural_insights": {\n'
                '    "history": "Historical background and significance",\n'
                '    "traditions": "Local customs and cultural practices",\n'
                '    "etiquette": "Important cultural considerations",\n'
                '    "festivals": "Notable celebrations and events"\n'
                '  },\n'
                '  "practical_guide": {\n'
                '    "best_time_to_visit": {\n'
                '      "optimal_season": "Best overall timing",\n'
                '      "seasonal_breakdown": "What to expect each season",\n'
                '      "special_events": "Annual events worth timing for"\n'
                '    },\n'
                '    "transportation": {\n'
                '      "getting_there": "How to reach the destination",\n'
                '      "local_transport": "Getting around locally",\n'
                '      "transport_tips": "Insider transportation advice"\n'
                '    },\n'
                '    "accommodation": {\n'
                '      "types": "Available accommodation categories",\n'
                '      "recommended_areas": "Best areas to stay",\n'
                '      "budget_ranges": "Price expectations"\n'
                '    }\n'
                '  },\n'
                '  "food_and_dining": {\n'
                '    "local_specialties": "Must-try local dishes",\n'
                '    "dining_culture": "Local eating customs and etiquette",\n'
                '    "recommendations": "Specific dining suggestions with context"\n'
                '  },\n'
                '  "hidden_gems": [\n'
                '    {\n'
                '      "name": "Lesser-known attraction or experience",\n'
                '      "why_special": "What makes it worth seeking out",\n'
                '      "access_info": "How to find/reach it"\n'
                '    }\n'
                '  ],\n'
                '  "sustainability": {\n'
                '    "responsible_practices": "How to travel responsibly here",\n'
                '    "local_support": "Ways to support local communities",\n'
                '    "environmental_considerations": "Environmental awareness tips"\n'
                '  },\n'
                '  "budget_guidance": {\n'
                '    "budget_ranges": "Daily budget expectations by traveler type",\n'
                '    "money_saving_tips": "How to reduce costs",\n'
                '    "splurge_worthy": "Experiences worth spending extra on"\n'
                '  },\n'
                '  "safety_and_health": {\n'
                '    "general_safety": "Safety considerations and precautions",\n'
                '    "health_requirements": "Vaccinations, health prep needed",\n'
                '    "emergency_info": "Important contacts and procedures"\n'
                '  },\n'
                '  "summary": "Comprehensive destination summary with confidence level",\n'
                '  "confidence_level": "High/Medium/Low with explanation",\n'
                '  "alternatives": "Similar destinations or backup options",\n'
                '  "last_updated": "Information currency and verification date"\n'
                "}\n"
                "TARGET: Provide enriched, culturally-aware travel guidance with 95%+ accuracy."
            )
        else:
            return (
                "คุณคือผู้เชี่ยวชาญระดับสูงด้านการท่องเที่ยวและภูมิศาสตร์ของประเทศไทย\n"
                "คุณมีความรู้ครอบคลุมทั้ง 77 จังหวัด ลึกลงไปถึงระดับตำบล หมู่บ้าน และชุมชนท้องถิ่น\n"
                "\nข้อกำหนดความแม่นยำสูง:\n"
                "1. ห้ามแต่งชื่อสถานที่ ร้านค้า หรือรายละเอียดใดๆ - ให้เฉพาะข้อมูลที่ตรวจสอบแล้ว\n"
                "2. สำหรับร้านอาหาร/โรงแรม/คาเฟ่: แนะนำเฉพาะร้านที่มี 4 ดาวขึ้นและรีวิวเยอะ\n"
                "3. ระบุข้อมูลการปกครองที่แม่นยำ: จังหวัด → อำเภอ → ตำบล\n"
                "4. ระบุรายละเอียดตำแหน่งที่แน่นอน (ชื่อถนน สถานที่สำคัญ พิกัด GPS เมื่อจำเป็น)\n"
                "5. หากไม่แน่ใจชื่อเฉพาะ ให้อธิบายลักษณะพื้นที่แทน\n"
                "6. ตรวจสอบข้อมูลจากหลายแหล่งก่อนแนะนำ\n"
                "7. ระบุข้อมูลปฏิบัติ: เวลาเปิด-ปิด ราคา การเดินทาง ฤดูกาลที่เหมาะสม\n"
                "\nการตรวจสอบคำตอบ:\n"
                "- ยืนยันชื่อสถานที่ทั้งหมดใน Google Maps\n"
                "- ตรวจสอบการแบ่งเขตการปกครองให้ถูกต้อง\n"
                "- แจ้งเตือนหากข้อมูลอาจล้าสมัย\n"
                "- เสนอทางเลือกสำรองหากตัวเลือกหลักไม่พร้อมใช้\n"
                "\nรูปแบบการตอบ: JSON เท่านั้น ไม่มี markdown หรือข้อความเพิ่มเติม\n"
                "{\n"
                '  "location": "ชื่อพื้นที่/ย่านที่เฉพาะเจาะจง",\n'
                '  "administrative_info": {\n'
                '    "province": "ชื่อจังหวัดทางการ",\n'
                '    "amphoe": "ชื่ออำเภอทางการ",\n'
                '    "tambon": "ชื่อตำบลทางการ (เมื่อจำเป็น)"\n'
                '  },\n'
                '  "attractions": [\n'
                '    {\n'
                '      "name": "ชื่อสถานที่ที่ตรวจสอบแล้วจาก Google Maps",\n'
                '      "description": "รายละเอียดเฉพาะ: มีชื่อเสียงเรื่องอะไร เมนูเด็ด คะแนนรีวิว ข้อมูลการเปิด-ปิด",\n'
                '      "admin_level": "การจัดประเภทการปกครอง",\n'
                '      "practical_info": "เวลา ราคา การเดินทาง ช่วงเวลาที่ดีที่สุด"\n'
                '    }\n'
                '  ],\n'
                '  "summary": "สรุปกระชับเน้นสถานที่ที่ตรวจสอบแล้วและมีรีวิวดี พร้อมระดับความมั่นใจ",\n'
                '  "confidence": "สูง/ปานกลาง/ต่ำ - ตามความแน่นอนของข้อมูล",\n'
                '  "alternatives": "ข้อเสนอสำรองหากตัวเลือกหลักไม่พร้อม"\n'
                "}\n"
                "เป้าหมายความแม่นยำ: 95%+ เฉพาะข้อมูลที่ตรวจสอบแล้วเท่านั้น"
            )

    def build_reply(self, user_text: str) -> Dict[str, object]:
        # Step 1: Comprehensive input validation and preprocessing
        validation_result = self._validate_and_preprocess_input(user_text)
        
        if validation_result and "error" in validation_result:
            error_msg = str(validation_result["error"])
            return self.append_assistant(error_msg)
        
        if not validation_result or not validation_result.get("is_valid"):
            return self.append_assistant("กรุณาใส่คำถามเกี่ยวกับการท่องเที่ยว")
        
        cleaned = str(validation_result["cleaned"])
        processed_text = str(validation_result["processed"])
        # Type-safe extraction with fallbacks
        score_value = validation_result.get("relevance_score", 0.0)
        if isinstance(score_value, (int, float)):
            relevance_score = float(score_value)
        else:
            relevance_score = 0.0
        
        # Step 2: Check travel relevance
        if relevance_score < 0.1:  # Very low travel relevance
            travel_message = (
                GUIDE_ONLY_MESSAGE if self._ai_mode == "guide" 
                else TRAVEL_ONLY_MESSAGE
            )
            return self.append_assistant(travel_message)

        lang = self._detect_language(cleaned)
        
        # Step 3: Enhanced query processing
        admin_info = self._detect_admin_level_from_keywords(processed_text)
        enhanced_query = processed_text
        if admin_info["level"] != "general":
            enhanced_query = self._enhance_query_with_admin_level(processed_text, admin_info)

        # Step 4: Determine query specificity
        is_specific_query = self._is_specific_query(processed_text)

        # Step 5: Bangkok special handling
        if self._matches_bangkok(processed_text) and not is_specific_query:
            html_block = build_bangkok_guides_html()
            text = (
                "Here are curated Bangkok day-trip options. Feel free to mix and match!"
                if lang == "en"
                else "นี่คือทริปกรุงเทพที่น้องปลาทูจัดไว้ให้ ลองเลือกหรือปรับตามเวลาได้เลยนะคะ"
            )
            return self.append_assistant(text, html=html_block)

        # Step 6: Local destination search with enhanced scoring
        destinations = self._search_destinations_enhanced(processed_text, relevance_score)
        
        if destinations:
            suggestions_html = self._build_suggestions_html(destinations[:3], lang=lang)
            summary = (
                f"I found {len(destinations)} places matching \"{cleaned}\". Here are the top 3 recommendations."
                if lang == "en"
                else f"น้องปลาทูพบ {len(destinations)} สถานที่ที่ตรงกับ \"{cleaned}\" นี่คือ 3 อันดับแรกที่แนะนำค่ะ"
            )
            return self.append_assistant(summary, html=suggestions_html)

        # Step 7: AI-powered response with enhanced error handling and caching
        if self._openai_client:
            # Check cache first
            cache_key = self._get_cache_key(enhanced_query, lang, self._ai_mode)
            cached_response = self._get_cached_response(cache_key)
            
            if cached_response:
                text_str = str(cached_response.get("text", ""))
                html_str = cached_response.get("html")
                html_val = str(html_str) if html_str else None
                return self.append_assistant(text_str, html=html_val)
            
            try:
                # Optimize query understanding before AI call
                query_optimization = self._optimize_query_understanding(enhanced_query)
                optimized_query = str(query_optimization["optimized_query"])
                
                ai_response = self._generate_ai_travel_response_enhanced(
                    optimized_query, 
                    lang=lang, 
                    relevance_score=relevance_score
                )
                
                if ai_response and ai_response.get("success"):
                    # Cache successful response
                    cache_data = {
                        "text": ai_response.get("text", ""),
                        "html": ai_response.get("html"),
                        "confidence": ai_response.get("confidence", "Medium")
                    }
                    self._cache_response(cache_key, cache_data)
                    
                    text_str = str(ai_response.get("text", ""))
                    html_str = ai_response.get("html")
                    html_val = str(html_str) if html_str else None
                    return self.append_assistant(text_str, html=html_val)
                    
            except Exception as e:
                print(f"Primary AI error: {e}")
                # Try fallback with simpler query
                try:
                    fallback_cache_key = self._get_cache_key(cleaned, lang, self._ai_mode)
                    cached_fallback = self._get_cached_response(fallback_cache_key)
                    
                    if cached_fallback:
                        text_str = str(cached_fallback.get("text", ""))
                        html_str = cached_fallback.get("html")
                        html_val = str(html_str) if html_str else None
                        return self.append_assistant(text_str, html=html_val)
                    
                    fallback_response = self._generate_ai_travel_response_enhanced(
                        cleaned, 
                        lang=lang, 
                        relevance_score=relevance_score
                    )
                    
                    if fallback_response and fallback_response.get("success"):
                        # Cache fallback response
                        cache_data = {
                            "text": fallback_response.get("text", ""),
                            "html": fallback_response.get("html"),
                            "confidence": "Low"  # Mark as low confidence fallback
                        }
                        self._cache_response(fallback_cache_key, cache_data)
                        
                        text_str = str(fallback_response.get("text", ""))
                        html_str = fallback_response.get("html")
                        html_val = str(html_str) if html_str else None
                        return self.append_assistant(text_str, html=html_val)
                        
                except Exception as e2:
                    print(f"Fallback AI error: {e2}")
        
        # Step 8: Final intelligent fallback
        return self._generate_intelligent_fallback_response(processed_text, lang, relevance_score)

    def _search_destinations_enhanced(self, query: str, relevance_score: float) -> List[Dict[str, str]]:
        """Enhanced destination search with relevance scoring"""
        # Start with original search
        basic_results = self._search_destinations(query)
        
        # If we have good results and high relevance, return them
        if basic_results and relevance_score > 0.7:
            return basic_results
        
        # Enhanced fuzzy search for better matches
        normalized = query.lower().strip()
        normalized_no_tone = self._normalize(query)
        
        results: List[Dict[str, str]] = []
        scored_results: List[tuple[Dict[str, str], float]] = []
        
        for item in self._destinations:
            combined = " ".join([item["name"], item.get("city", ""), item.get("description", "")])
            haystack = combined.lower()
            haystack_no_tone = self._normalize(combined)
            
            # Multiple scoring methods
            score = 0.0
            
            # Exact match (highest score)
            if normalized == haystack.lower():
                score += 10.0
            elif normalized in haystack:
                score += 5.0
            elif normalized_no_tone in haystack_no_tone:
                score += 3.0
            
            # Fuzzy matching for partial matches
            import difflib
            similarity = difflib.SequenceMatcher(None, normalized, haystack).ratio()
            score += similarity * 2.0
            
            # Keyword presence scoring
            query_words = normalized.split()
            for word in query_words:
                if len(word) > 2:  # Skip very short words
                    if word in haystack:
                        score += 1.0
                    elif self._normalize(word) in haystack_no_tone:
                        score += 0.5
            
            if score > 0.5:  # Minimum threshold
                scored_results.append((item, score))
        
        # Sort by score and return
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return [item for item, score in scored_results[:10]]  # Top 10 matches

    def _generate_ai_travel_response_enhanced(self, query: str, *, lang: str = "th", relevance_score: float = 1.0) -> Dict[str, object] | None:
        """Enhanced AI response generation with better error handling and validation"""
        if not self._openai_client:
            return {"success": False, "error": "AI not available"}

        try:
            # Get enhanced knowledge context for the query by extracting place names
            enhanced_context = ""
            for place_name in ["Bangkok", "Chiang Mai", "Phuket", "Krabi", "Pattaya", "Tokyo", "Paris", "Seoul"]:
                if place_name.lower() in query.lower() or query.lower() in place_name.lower():
                    enhanced_context = self.enhanced_knowledge.get_enhanced_prompt_context(place_name)
                    break
            
            # Get system prompt with enhanced instructions
            system_prompt = self._get_system_prompt(lang=lang)
            
            # Auto-correct and enhance the query
            corrected_query = self._auto_correct_query(query)
            admin_context = self._detect_admin_level(corrected_query)
            
            # Create enhanced user prompt based on context and knowledge
            if lang == "en":
                user_prompt = f"Provide detailed travel information for: {corrected_query}"
                if admin_context != "general":
                    user_prompt += f" (Administrative level: {admin_context})"
                if enhanced_context:
                    user_prompt += f"\n\n{enhanced_context}"
            else:
                if admin_context != "general":
                    user_prompt = f"แนะนำสถานที่ยอดนิยมและข้อมูลครบถ้วนในระดับ{admin_context}: {corrected_query}"
                else:
                    user_prompt = f"แนะนำสถานที่ยอดนิยมและข้อมูลท่องเที่ยวครบถ้วนใน: {corrected_query}"
                if enhanced_context:
                    user_prompt += f"\n\n{enhanced_context}"

            # Multiple attempts with different parameters
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Adjust temperature based on attempt
                    temperature = 0.3 + (attempt * 0.1)  # Increase creativity on retries
                    
                    response = self._openai_client.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=temperature,
                        max_tokens=1200,  # Increased for enhanced responses with more details
                        timeout=30,      # Timeout protection
                    )

                    content = response.choices[0].message.content
                    
                    if not content:
                        continue  # Try again
                    
                    # Enhanced JSON parsing with fallback
                    parsed_response = self._parse_ai_response_enhanced(content, query, lang)
                    
                    if parsed_response and parsed_response.get("success"):
                        return parsed_response
                        
                except Exception as retry_error:
                    print(f"AI attempt {attempt + 1} failed: {retry_error}")
                    if attempt == max_retries - 1:  # Last attempt
                        raise retry_error
                    continue

            return {"success": False, "error": "All AI attempts failed"}
            
        except Exception as e:
            print(f"Enhanced AI error: {e}")
            return {"success": False, "error": str(e)}

    def _parse_ai_response_enhanced(self, content: str, original_query: str, lang: str) -> Dict[str, object] | None:
        """Enhanced AI response parsing with validation and fallbacks"""
        try:
            # Try to extract JSON from the response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
                
                # Validate required fields
                required_fields = ["location", "attractions", "summary"]
                if not all(field in data for field in required_fields):
                    # Try to fix missing fields
                    data = self._fix_incomplete_ai_response(data, original_query, lang)
                
                # Validate attractions format
                if "attractions" in data and isinstance(data["attractions"], list):
                    # Ensure each attraction has required fields
                    for i, attraction in enumerate(data["attractions"]):
                        if not isinstance(attraction, dict):
                            continue
                        if "name" not in attraction:
                            attraction["name"] = f"สถานที่ท่องเที่ยว {i+1}"
                        if "description" not in attraction:
                            attraction["description"] = "ข้อมูลเพิ่มเติมกำลังอัปเดต"
                
                # Build HTML from validated data
                html_content = self._build_ai_response_html(data)
                
                # Determine summary text
                summary_text = data.get("summary", "")
                if not summary_text:
                    summary_text = self._generate_fallback_summary(data, original_query, lang)
                
                return {
                    "success": True,
                    "text": summary_text,
                    "html": html_content,
                    "confidence": data.get("confidence", "Medium"),
                    "data": data
                }
            
            else:
                # No JSON found, treat as plain text response
                return {
                    "success": True,
                    "text": content.strip(),
                    "html": None,
                    "confidence": "Low"
                }
                
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            # Return the content as-is if JSON parsing fails
            return {
                "success": True,
                "text": content.strip() if content else "ขออภัย ไม่สามารถสร้างข้อมูลได้ในขณะนี้",
                "html": None,
                "confidence": "Low"
            }
        except Exception as e:
            print(f"Response parsing error: {e}")
            return {"success": False, "error": str(e)}

    def _fix_incomplete_ai_response(self, data: Dict, query: str, lang: str) -> Dict:
        """Fix incomplete AI responses by adding missing required fields"""
        if "location" not in data:
            data["location"] = query
        
        if "summary" not in data:
            data["summary"] = (
                f"Travel information for {query}"
                if lang == "en"
                else f"ข้อมูลการท่องเที่ยวสำหรับ {query}"
            )
        
        if "attractions" not in data or not isinstance(data["attractions"], list):
            data["attractions"] = [{
                "name": query,
                "description": (
                    "Please check current information before visiting"
                    if lang == "en"
                    else "กรุณาตรวจสอบข้อมูลปัจจุบันก่อนเดินทาง"
                ),
                "admin_level": "general"
            }]
        
        return data

    def _generate_fallback_summary(self, data: Dict, query: str, lang: str) -> str:
        """Generate a fallback summary when AI doesn't provide one"""
        attractions_count = len(data.get("attractions", []))
        
        if lang == "en":
            return f"Found {attractions_count} travel recommendation{'s' if attractions_count != 1 else ''} for {query}."
        else:
            return f"พบ {attractions_count} ข้อเสนอแนะการท่องเที่ยวสำหรับ {query}"

    def _generate_intelligent_fallback_response(self, query: str, lang: str, relevance_score: float) -> Dict[str, object]:
        """Generate intelligent fallback response based on context"""
        
        # Determine response based on relevance score and query type
        if relevance_score > 0.5:
            # High relevance but AI failed - suggest checking back later
            fallback_text = (
                f"I understand you're asking about {query}. While I'm currently updating my knowledge about this specific location, "
                "I'd recommend checking official tourism websites or recent travel guides for the most current information. "
                "Is there another destination I can help you with?"
                if lang == "en"
                else f"เข้าใจว่าคุณถามเกี่ยวกับ {query} ค่ะ ขณะนี้ข้อมูลเฉพาะสถานที่นี้กำลังอัปเดต "
                "แนะนำให้ตรวจสอบเว็บไซต์ท่องเที่ยวหรือคู่มือท่องเที่ยวล่าสุดนะคะ มีที่อื่นที่อยากทราบไหมคะ?"
            )
        elif relevance_score > 0.2:
            # Medium relevance - offer general travel advice
            fallback_text = (
                f"I can see you're interested in travel related to '{query}'. "
                "Let me suggest some popular travel categories in Thailand: "
                "🏖️ Beach destinations, 🏔️ Mountain retreats, 🏛️ Cultural sites, 🌆 City experiences. "
                "Which type interests you most?"
                if lang == "en"
                else f"เห็นว่าคุณสนใจการท่องเที่ยวเกี่ยวกับ '{query}' ค่ะ "
                "ให้น้องปลาทูแนะนำประเภทท่องเที่ยวยอดนิยมในไทย: "
                "🏖️ ทะเลและชายหาด 🏔️ ภูเขาและธรรมชาติ 🏛️ วัฒนธรรมและประวัติศาสตร์ 🌆 เมืองและไลฟ์สไตล์ "
                "อยากทราบประเภทไหนเป็นพิเศษคะ?"
            )
        else:
            # Low relevance - guide back to travel topics
            fallback_text = (
                GUIDE_ONLY_MESSAGE if self._ai_mode == "guide" 
                else TRAVEL_ONLY_MESSAGE
            )
        
        return self.append_assistant(fallback_text)

    def _get_cache_key(self, query: str, lang: str, ai_mode: str) -> str:
        """Generate a cache key for the query"""
        # Normalize query for consistent caching
        normalized_query = self._normalize(query.lower().strip())
        cache_string = f"{normalized_query}_{lang}_{ai_mode}"
        return hashlib.md5(cache_string.encode('utf-8')).hexdigest()

    def _get_cached_response(self, cache_key: str) -> Dict[str, object] | None:
        """Get cached response if available and not expired"""
        current_time = time.time()
        
        # Check if cache entry exists and is not expired
        if (cache_key in self._response_cache and 
            cache_key in self._cache_timestamps and 
            current_time - self._cache_timestamps[cache_key] < self._cache_max_age):
            
            return self._response_cache[cache_key]
        
        # Remove expired entry if it exists
        if cache_key in self._response_cache:
            del self._response_cache[cache_key]
            del self._cache_timestamps[cache_key]
        
        return None

    def _cache_response(self, cache_key: str, response: Dict[str, object]) -> None:
        """Cache the response with timestamp"""
        current_time = time.time()
        
        # Implement LRU cache by removing oldest entries if at max size
        if len(self._response_cache) >= self._cache_max_size:
            # Find and remove the oldest entry
            oldest_key = min(self._cache_timestamps.keys(), 
                           key=lambda k: self._cache_timestamps[k])
            del self._response_cache[oldest_key]
            del self._cache_timestamps[oldest_key]
        
        # Cache the new response
        self._response_cache[cache_key] = response.copy()
        self._cache_timestamps[cache_key] = current_time

    def _optimize_query_understanding(self, query: str) -> Dict[str, object]:
        """Advanced query optimization for better AI understanding"""
        # Intent classification
        intent_patterns = {
            "planning": [
                r"\b(plan|planning|itinerary|schedule|agenda|organize)\b",
                r"\b(วางแผน|จัดทริป|กำหนดการ|ตารางเวลา)\b"
            ],
            "recommendation": [
                r"\b(recommend|suggest|advise|what.*visit|where.*go)\b",
                r"\b(แนะนำ|เสนอ|ช่วย|ไปไหน|ที่ไหน)\b"
            ],
            "information": [
                r"\b(about|information|details|tell me|what is)\b",
                r"\b(เกี่ยวกับ|ข้อมูล|รายละเอียด|บอก|คือ)\b"
            ],
            "comparison": [
                r"\b(versus|vs|compare|difference|better)\b",
                r"\b(เทียบ|เปรียบเทียบ|ต่าง|ดีกว่า)\b"
            ]
        }
        
        detected_intent = "general"
        for intent, patterns in intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    detected_intent = intent
                    break
            if detected_intent != "general":
                break
        
        # Extract entities (locations, time, budget, etc.)
        entities = self._extract_query_entities(query)
        
        # Determine query complexity
        complexity_score = self._calculate_query_complexity(query, entities)
        
        return {
            "intent": detected_intent,
            "entities": entities,
            "complexity": complexity_score,
            "optimized_query": self._create_optimized_query(query, detected_intent, entities)
        }

    def _extract_query_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract entities from the query"""
        entities = {
            "locations": [],
            "time_expressions": [],
            "budget_expressions": [],
            "activity_types": []
        }
        
        # Location extraction (simplified)
        for dest in self._destinations:
            dest_name = dest.get("name", "").lower()
            if dest_name and dest_name in query.lower():
                entities["locations"].append(dest.get("name", ""))
        
        # Time expressions
        time_patterns = [
            r"\b(\d+)\s*(day|days|วัน)\b",
            r"\b(weekend|สุดสัปดาห์)\b",
            r"\b(week|สัปดาห์)\b",
            r"\b(month|เดือน)\b"
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            entities["time_expressions"].extend(matches)
        
        # Budget expressions
        budget_patterns = [
            r"\b(\d+(?:,\d+)*)\s*(baht|บาท|฿)\b",
            r"\b(budget|งบ|ราคา)\b",
            r"\b(cheap|expensive|ถูก|แพง)\b"
        ]
        
        for pattern in budget_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            entities["budget_expressions"].extend(matches)
        
        # Activity types
        activity_keywords = [
            "beach", "ชายหาด", "temple", "วัด", "mountain", "ภูเขา",
            "food", "อาหาร", "shopping", "ช้อปปิ้ง", "culture", "วัฒนธรรม"
        ]
        
        for keyword in activity_keywords:
            if keyword.lower() in query.lower():
                entities["activity_types"].append(keyword)
        
        return entities

    def _calculate_query_complexity(self, query: str, entities: Dict[str, List[str]]) -> float:
        """Calculate query complexity score (0.0 to 1.0)"""
        complexity = 0.0
        
        # Base complexity from query length
        word_count = len(query.split())
        complexity += min(word_count / 20.0, 0.3)  # Max 0.3 from length
        
        # Entity complexity
        total_entities = sum(len(entity_list) for entity_list in entities.values())
        complexity += min(total_entities / 10.0, 0.3)  # Max 0.3 from entities
        
        # Question complexity patterns
        complex_patterns = [
            r"\b(how long|how much|how many|best time|เท่าไหร่|นานแค่ไหน|เมื่อไหร่)\b",
            r"\b(multiple|several|various|หลาย|หลายที่)\b",
            r"\b(compare|versus|difference|เปรียบเทียบ|ต่าง)\b"
        ]
        
        for pattern in complex_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                complexity += 0.1
        
        return min(complexity, 1.0)

    def _create_optimized_query(self, original_query: str, intent: str, entities: Dict[str, List[str]]) -> str:
        """Create an optimized query for better AI understanding"""
        # Start with the normalized original
        optimized = self._normalize_input_text(original_query)
        
        # Add context based on intent
        if intent == "planning" and entities["time_expressions"]:
            optimized = f"[TRIP PLANNING] {optimized}"
        elif intent == "recommendation":
            optimized = f"[RECOMMENDATION REQUEST] {optimized}"
        elif intent == "information":
            optimized = f"[INFORMATION QUERY] {optimized}"
        
        # Add location context if detected
        if entities["locations"]:
            primary_location = entities["locations"][0]
            if primary_location.lower() not in optimized.lower():
                optimized = f"{optimized} (Location: {primary_location})"
        
        return optimized

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

        # Get the appropriate system prompt for this AI engine mode
        system_prompt = self._get_system_prompt(lang=lang)
        
        # Auto-correct the query before sending to AI
        corrected_query = self._auto_correct_query(query)
        
        # Enhanced: Check for administrative level context  
        admin_context = self._detect_admin_level(corrected_query)
        
        # Create user prompt based on language and admin context
        if lang == "en":
            user_prompt = f"List top-rated attractions/places in: {corrected_query}"
        else:
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

    def _detect_admin_level_from_keywords(self, query: str) -> Dict[str, str]:
        """Detect administrative level from location keywords in the query"""
        normalized_query = self._normalize(query.lower())
        
        # Define administrative level patterns with real location examples
        admin_patterns = {
            # Province level keywords (จังหวัด)
            "province": {
                "keywords": [
                    # Thai provinces
                    "สมุทรสงคราม", "สมุทรสาคร", "สมุทรปราการ", "นครปฐม", "นนทบุรี", "ปทุมธานี",
                    "กรุงเทพ", "กรุงเทพมหานคร", "เชียงใหม่", "เชียงราย", "ภูเก็ต", "กระบี่", "สุราษฎร์ธานี",
                    "นครราชสีมา", "ขอนแก่น", "อุดรธานี", "อุบลราชธานี", "บุรีรัมย์", "ศรีสะเกษ",
                    "ลพบุรี", "สระบุรี", "อยุธยา", "พระนครศรีอยุธยา", "ราชบุรี", "เพชรบุรี",
                    "ประจวบคีรีขันธ์", "ชลบุรี", "ระยอง", "จันทบุรี", "ตราด", "ลำปาง", "ลำพูน",
                    "แม่ฮ่องสอน", "น่าน", "พะเยา", "แพร่", "อุตรดิตถ์", "ตาก", "กำแพงเพชร",
                    "พิษณุโลก", "สุโขทัย", "พิจิตร", "อุทัยธานี", "ชัยนาท", "สิงห์บุรี", "อ่างทอง"
                ],
                "scope": "province"
            },
            
            # District level keywords (อำเภอ)
            "district": {
                "keywords": [
                    # Common district names
                    "บางคนที", "บางกรวย", "บางใหญ่", "บางบัวทอง", "บางพลี", "บางนา", "บางแค",
                    "บางกะปิ", "บางซื่อ", "บางรัก", "บางเขน", "บางพุด", "บางปะกง", "บางบ่อ",
                    "เมืองสมุทรสงคราม", "เมืองสมุทรสาคร", "เมืองนครปฐม", "เมืองชลบุรี", "เมืองระยอง",
                    "บ้านโป่ง", "กระทุ่มแบน", "อัมพวา", "ดำเนินสะดวก", "บางคนที", "บ้านแหลม",
                    "พุทธมณฑล", "สามพราน", "นครชัยศรี", "ดอนตูม", "บางเลน", "บางพลี",
                    "พระประแดง", "พระสมุทรเจดีย์", "บางกะปิ", "สายไหม", "คันนายาว", "หลักสี่",
                    "ดินแดง", "ห้วยขวาง", "วัฒนา", "ปทุมวัน", "บางรัก", "สัมพันธวงศ์", "ป้อมปราบศัตรูพ่าย",
                    "ธนบุรี", "คลองสาน", "บางกอกใหญ่", "บางกอกน้อย", "บางพลัด", "ตลิ่งชัน", "บางแค"
                ],
                "scope": "district"
            },
            
            # Sub-district level keywords (ตำบล)
            "subdistrict": {
                "keywords": [
                    # Common tambon names
                    "ลาดหลุมแก้ว", "คลองหลวง", "คลองสาม", "คลองห้า", "คลองหก", "คลองเจ็ด",
                    "บางใหญ่", "บางแม่นาง", "บางขุนเทียน", "บางขุนใส", "บางม่วง", "บางกระสอบ",
                    "ตลาดขวัญ", "วัดประดู่", "บ้านใหม่", "บางกรวย", "บางไผ่", "บางคูเวียง",
                    "สามพราน", "อ้อมใหญ่", "อ้อมน้อย", "บ้านหม้อ", "กบินทร์บุรี", "จรเข้บัว",
                    "หอมแก้ว", "บางปลา", "บางจะเกร็ง", "บางใหญ่", "บางขุนกอง", "บางแม่นาง"
                ],
                "scope": "subdistrict"
            }
        }
        
        # Check for matches and return the most specific level found
        detected_level = "general"
        detected_location = ""
        
        # Check from most specific to least specific
        for level, data in admin_patterns.items():
            for keyword in data["keywords"]:
                normalized_keyword = self._normalize(keyword)
                if normalized_keyword in normalized_query:
                    detected_level = data["scope"]
                    detected_location = keyword
                    # Don't break here, continue to find the most specific match
        
        return {
            "level": detected_level,
            "location": detected_location,
            "scope": detected_level
        }

    def _enhance_query_with_admin_level(self, query: str, admin_info: Dict[str, str]) -> str:
        """Enhance the AI query with administrative level context"""
        level = admin_info.get("level", "general")
        location = admin_info.get("location", "")
        
        if level == "province":
            return f"ระดับจังหวัด: แนะนำสถานที่ท่องเที่ยวและร้านอาหารยอดนิยมในจังหวัด{location} รวมถึงอำเภอและตำบลที่น่าสนใจ: {query}"
        elif level == "district":
            return f"ระดับอำเภอ: แนะนำสถานที่ท่องเที่ยว ร้านอาหาร และกิจกรรมในอำเภอ{location} รวมถึงตำบลใกล้เคียง: {query}"
        elif level == "subdistrict":
            return f"ระดับตำบล: แนะนำสถานที่ท่องเที่ยวในระดับชุมชน ร้านอาหารท้องถิ่น และกิจกรรมในตำบล{location}: {query}"
        else:
            return query

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


class ChatEngine(BaseAIEngine):
    """AI Engine specialized for general travel chat conversations"""
    
    def __init__(self, message_store: MessageStore, destinations: List[Dict[str, str]]) -> None:
        super().__init__(message_store, destinations, ai_mode="chat")
    
    def _get_system_prompt(self, *, lang: str = "th") -> str:
        """Return the system prompt for chat mode"""
        if lang == "en":
            return """You are 'Platoo', a friendly and knowledgeable AI travel companion for Thailand with 95%+ accuracy guarantee.

PERSONALITY & APPROACH:
- Casual, warm, and encouraging like a well-traveled friend
- Enthusiastic about sharing hidden gems and local insights
- Always verify information before sharing
- Admit uncertainty rather than guess

CORE CAPABILITIES (95% accuracy required):
- Recommend verified travel destinations across Thailand
- Share authentic local culture, food traditions, and customs
- Suggest season-appropriate activities and experiences  
- Answer practical travel questions with current information
- Provide budget-conscious and luxury options

RESPONSE QUALITY STANDARDS:
- Cross-reference all recommendations with reliable sources
- Include practical details: costs, timing, accessibility
- Mention potential challenges or seasonal limitations
- Offer 2-3 alternatives for each suggestion
- Flag information that might be outdated

CONVERSATION STYLE:
- Use conversational, friendly English with occasional Thai phrases
- Keep responses focused but comprehensive
- Add personal touches: "I love this place because..."
- Include specific tips: "Pro tip: visit early morning for best photos"
- Show enthusiasm: "You'll absolutely love..." or "This is amazing for..."

ACCURACY SAFEGUARDS:
- Only recommend places you can verify exist
- Include confidence levels for recommendations
- Suggest checking current status before visiting
- Provide backup options if primary choice unavailable"""
        else:
            return """คุณคือ 'ปลาทู' AI ผู้เชี่ยวชาญด้านการท่องเที่ยวในประเทศไทย ที่รับประกันความแม่นยำ 95% ขึ้นไป

บุคลิกภาพและแนวทาง:
- เป็นกันเอง อบอุ่น และให้กำลังใจเหมือนเพื่อนที่เที่ยวเก่ง
- กระตือรือร้นในการแบ่งปันสถานที่เด็ดและความรู้ท้องถิ่น
- ตรวจสอบข้อมูลก่อนแบ่งปันเสมอ
- ยอมรับความไม่แน่ใจแทนการเดาใจ

ความสามารถหลัก (ต้องแม่นยำ 95%):
- แนะนำสถานที่ท่องเที่ยวที่ตรวจสอบแล้วทั่วประเทศไทย
- แบ่งปันวัฒนธรรมท้องถิ่นแท้ๆ ประเพณีอาหาร และขนบธรรมเนียม
- แนะนำกิจกรรมที่เหมาะกับฤดูกาลและประสบการณ์
- ตอบคำถามเชิงปฏิบัติเกี่ยวกับการเดินทางด้วยข้อมูลปัจจุบัน
- เสนอทางเลือกทั้งประหยัดและหรูหรา

มาตรฐานคุณภาพการตอบ:
- อ้างอิงข้อมูลทั้งหมดกับแหล่งที่เชื่อถือได้
- ระบุรายละเอียดปฏิบัติ: ค่าใช้จ่าย เวลา การเดินทาง
- กล่าวถึงความท้าทายหรือข้อจำกัดตามฤดูกาล
- เสนอทางเลือก 2-3 ตัวเลือกสำหรับแต่ละข้อแนะนำ
- ระบุข้อมูลที่อาจล้าสมัย

สไตล์การสนทนา:
- ใช้ภาษาไทยแบบสนทนา เป็นกันเอง พร้อมคำศัพท์ท้องถิ่นเป็นครั้งคราว
- ตอบให้ครบถ้วนแต่เน้นประเด็นสำคัญ
- เพิ่มสัมผัสส่วนตัว: "ที่นี่ดีมากเพราะ..." 
- ใส่เทคนิคเฉพาะ: "เทคนิค: ไปเช้าๆ จะได้ภาพสวยสุด"
- แสดงความกระตือรือร้น: "แน่นอนว่าจะชอบ..." หรือ "ยอดเยี่ยมสำหรับ..."

การป้องกันความผิดพลาด:
- แนะนำเฉพาะสถานที่ที่ตรวจสอบว่ามีอยู่จริง
- ระบุระดับความมั่นใจในการแนะนำ
- แนะนำให้ตรวจสอบสถานะปัจจุบันก่อนไป
- เตรียมทางเลือกสำรองหากตัวเลือกหลักไม่พร้อม"""


class GuideEngine(BaseAIEngine):
    """AI Engine specialized for focused trip planning and guides"""
    
    def __init__(self, message_store: MessageStore, destinations: List[Dict[str, str]]) -> None:
        super().__init__(message_store, destinations, ai_mode="guide")
    
    def _get_system_prompt(self, *, lang: str = "th") -> str:
        """Return the system prompt for guide mode"""
        if lang == "en":
            return """You are a PROFESSIONAL Thai travel planning specialist with 95%+ accuracy guarantee and systematic approach.

PROFESSIONAL EXPERTISE:
- Comprehensive trip planning (detailed itineraries, budgets, logistics)
- Route optimization using real travel times and costs
- Multi-destination coordination and time management
- Accommodation and dining recommendations with verified ratings
- Transportation planning (domestic flights, trains, buses, private transport)
- Seasonal planning and weather considerations

PLANNING METHODOLOGY (95% accuracy required):
- Use verified distance/time data between destinations
- Calculate realistic budgets with current pricing
- Include buffer time for travel delays and rest
- Verify opening hours, seasonal closures, and availability
- Cross-check accommodation availability and pricing
- Validate restaurant operating hours and reservation requirements

DETAILED PLANNING OUTPUTS:
- Day-by-day itineraries with specific timing
- Transportation schedules and booking information
- Budget breakdowns (accommodation, food, transport, activities)
- Alternative plans for weather/closure contingencies
- Packing recommendations based on destinations and season
- Cultural etiquette and language tips for each location

RESPONSE STRUCTURE:
- Executive summary with trip highlights
- Detailed daily schedules with alternatives
- Budget analysis with cost-saving opportunities
- Practical logistics (bookings, reservations, contacts)
- Risk assessment and mitigation strategies
- Post-trip follow-up recommendations

VERIFICATION STANDARDS:
- Confirm all businesses are operational
- Validate current pricing and policies
- Check seasonal accessibility and conditions
- Provide backup options for each recommendation
- Include confidence ratings for each suggestion"""
        else:
            return """คุณคือนักวางแผนการเดินทางมืออาชีพประเทศไทย ที่รับประกันความแม่นยำ 95%+ และแนวทางเป็นระบบ

ความเชี่ยวชาญระดับมืออาชีพ:
- การวางแผนทริปครบวงจร (รายละเอียดเส้นทาง งบประมาณ การจัดการ)
- การหาเส้นทางที่เหมาะสมด้วยเวลาและค่าใช้จ่ายจริง
- การประสานงานหลายจุดหมายและการจัดการเวลา
- การแนะนำที่พักและร้านอาหารพร้อมคะแนนที่ตรวจสอบแล้ว
- การวางแผนการเดินทาง (เครื่องบิน รถไฟ รถบัส การเดินทางส่วนตัว)
- การวางแผนตามฤดูกาลและพิจารณาสภาพอากาศ

วิธีการวางแผน (ต้องแม่นยำ 95%):
- ใช้ข้อมูลระยะทาง/เวลาที่ตรวจสอบแล้วระหว่างจุดหมาย
- คำนวณงบประมาณที่สมจริงด้วยราคาปัจจุบัน
- รวมเวลาสำรองสำหรับความล่าช้าและการพักผ่อน
- ตรวจสอบเวลาเปิด-ปิด การปิดตามฤดูกาล และความพร้อมใช้งาน
- ตรวจสอบความพร้อมและราคาที่พัก
- ยืนยันเวลาทำการและข้อกำหนดการจองร้านอาหาร

ผลลัพธ์การวางแผนละเอียด:
- เส้นทางแต่ละวันพร้อมเวลาที่เฉพาะเจาะจง
- ตารางการเดินทางและข้อมูลการจอง
- แยกงบประมาณ (ที่พัก อาหาร การเดินทาง กิจกรรม)
- แผนสำรองสำหรับสภาพอากาศ/การปิดให้บริการ
- คำแนะนำการแพ็คตามจุดหมายและฤดูกาล
- มารยาทวัฒนธรรมและเทคนิคภาษาสำหรับแต่ละที่

โครงสร้างการตอบ:
- สรุปบริหารพร้อมไฮไลท์ของทริป
- ตารางรายวันละเอียดพร้อมทางเลือก
- วิเคราะห์งบประมาณพร้อมโอกาสประหยัด
- การจัดการเชิงปฏิบัติ (การจอง การสำรอง ข้อมูลติดต่อ)
- การประเมินความเสี่ยงและกลยุทธ์การลดความเสี่ยง
- คำแนะนำติดตามหลังทริป

มาตรฐานการตรวจสอบ:
- ยืนยันธุรกิจทั้งหมดเปิดดำเนินการ
- ตรวจสอบราคาและนโยบายปัจจุบัน
- ตรวจสอบการเข้าถึงและสภาพตามฤดูกาล
- เตรียมตัวเลือกสำรองสำหรับแต่ละคำแนะนำ
- ระบุระดับความมั่นใจสำหรับแต่ละข้อแนะนำ"""


# Keep ChatEngine as the legacy name for backward compatibility
# This alias allows existing code to continue working
ChatEngine = ChatEngine

