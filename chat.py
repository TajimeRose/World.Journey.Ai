"""GPT chatbot for Samut Songkhram tourism. OPENAI_MODEL (default: gpt-4o)."""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from world_journey_ai.configs import PromptRepo
from world_journey_ai.db import get_db, Place
try:
    from world_journey_ai.services.database import get_db_service
    DB_SERVICE_AVAILABLE = True
except Exception as exc:
    print(f"[WARN] Database service unavailable for adaptive flow: {exc}")
    DB_SERVICE_AVAILABLE = False

    # Provide stub to keep symbol bound for static analysis / linters.
    def get_db_service() -> Any:  # type: ignore[misc]
        raise RuntimeError("Database service unavailable")


try:
    from gpt_service import GPTService
    GPT_AVAILABLE = True
except Exception as exc:
    print(f"[WARN] GPT service import failed: {exc}")
    GPT_AVAILABLE = False
    GPTService = None

try:
    from simple_matcher import FlexibleMatcher
    FLEXIBLE_MATCHER_AVAILABLE = True
except Exception as exc:
    print(f"[WARN] Flexible matcher unavailable: {exc}")
    FLEXIBLE_MATCHER_AVAILABLE = False
    FlexibleMatcher = None

if TYPE_CHECKING:
    from simple_matcher import FlexibleMatcher as FlexibleMatcherType
else:
    FlexibleMatcherType = Any

PROMPT_REPO = PromptRepo()
# DATA_FILE and other JSON constants removed

LOCAL_KEYWORDS = PROMPT_REPO.get_prompt("chatbot/local_terms", default=[
    "สมุทรสงคราม",
    "samut songkhram"
])
DUPLICATE_WINDOW_SECONDS = 15


class TravelChatbot:
    """Chatbot powered solely by GPT (local data + prompts)."""

    def __init__(self) -> None:
        self.bot_name = "NongPlaToo"
        self.chatbot_prompts = PROMPT_REPO.get_prompt("chatbot/answer", default={})
        self.preferences = PROMPT_REPO.get_preferences()
        self.runtime_config = PROMPT_REPO.get_runtime_config()
        self.character_profile = PROMPT_REPO.get_character_profile()
        self.match_limit = self.runtime_config.get("matching", {}).get("max_matches", 5)
        self.display_limit = self.runtime_config.get("matching", {}).get("max_display", 4)
        self.gpt_service: Optional[Any] = None
        self.gpt_service: Optional[Any] = None
        # self.image_links = self._load_image_links() # Removed
        # self.province_profile = self._load_province_profile() # Removed
        # raw_trip_guides = self._load_trip_guides() # Removed
        self.travel_data = self._load_travel_data_from_db()
        self.trip_guides = {
            entry["id"]: entry
            for entry in self.travel_data
            if entry.get("category") == "trip_plan"
        }
        self.dataset_summary = self._build_dataset_summary()
        self.local_reference_terms = self._build_local_reference_terms()
        self.matching_engine: Optional[FlexibleMatcherType] = self._init_matcher()
        self._recent_requests: Dict[str, Dict[str, Any]] = {}

        if GPT_AVAILABLE and GPTService is not None:
            try:
                self.gpt_service = GPTService()
                print("[OK] GPT service initialized")
            except Exception as exc:
                print(f"[ERROR] Cannot initialize GPT service: {exc}")
                self.gpt_service = None
        else:
            print("[WARN] GPT service unavailable")

    def _init_matcher(self) -> Optional[FlexibleMatcherType]:
        if not FLEXIBLE_MATCHER_AVAILABLE or FlexibleMatcher is None:
            return None
        try:
            return FlexibleMatcher()
        except Exception as exc:
            print(f"[WARN] Cannot initialize flexible matcher: {exc}")
            return None

    @staticmethod
    def _detect_language(text: str) -> str:
        thai_chars = sum(1 for ch in text if "\u0e00" <= ch <= "\u0e7f")
        return "th" if thai_chars > max(1, len(text) // 3) else "en"

    def _matcher_analysis(self, query: str) -> Dict[str, Any]:
        if not query.strip():
            return {"topic": None, "confidence": 0.0, "keywords": [], "is_local": False}
        engine = getattr(self, "matching_engine", None)
        if not engine:
            return {"topic": None, "confidence": 0.0, "keywords": [], "is_local": False}
        topic = None
        confidence = 0.0
        try:
            topic, confidence = engine.find_best_match(query)
        except Exception as exc:
            print(f"[WARN] Flexible matcher topic detection failed: {exc}")
        try:
            is_local = engine.is_samutsongkhram_related(query)
        except Exception as exc:
            print(f"[WARN] Flexible matcher locality detection failed: {exc}")
            is_local = False
        keywords: List[str] = []
        if topic:
            try:
                keywords = engine.get_topic_keywords(topic)
            except Exception as exc:
                print(f"[WARN] Flexible matcher keywords failed: {exc}")
        # Ensure primitive types for downstream JSON serialization
        safe_topic = topic if isinstance(topic, str) else (str(topic) if topic else None)
        safe_confidence = float(confidence or 0.0)
        safe_local_flag = bool(is_local)
        return {
            "topic": safe_topic,
            "confidence": safe_confidence,
            "keywords": keywords,
            "is_local": safe_local_flag,
        }

    @staticmethod
    def _merge_keywords(*keyword_sets: List[str]) -> List[str]:
        merged: List[str] = []
        seen = set()
        for keyword_list in keyword_sets:
            if not keyword_list:
                continue
            for keyword in keyword_list:
                text = str(keyword).strip()
                if not text:
                    continue
                lowered = text.lower()
                if lowered in seen:
                    continue
                seen.add(lowered)
                merged.append(text)
        return merged

    @staticmethod
    def _normalized_query_key(text: str) -> str:
        collapsed = re.sub(r"\s+", " ", text.strip())
        return collapsed.lower()

    def _replay_duplicate_response(self, user_id: str, key: str) -> Optional[Dict[str, Any]]:
        if not key:
            return None
        entry = self._recent_requests.get(user_id)
        if not entry:
            return None
        if entry["query"] == key and (time.time() - entry["timestamp"]) <= DUPLICATE_WINDOW_SECONDS:
            cached_payload = dict(entry["result"])
            cached_payload["duplicate"] = True
            cached_payload["source"] = f"{cached_payload.get('source', 'cache')}_cached"
            return cached_payload
        return None

    def _cache_response(self, user_id: str, key: str, payload: Dict[str, Any]) -> None:
        if not key:
            return
        self._recent_requests[user_id] = {
            "query": key,
            "timestamp": time.time(),
            "result": payload,
        }

    def _auto_detect_keywords(self, query: str, limit: int = 6) -> List[str]:
        if not query or not self.travel_data:
            return []
        normalized_query = self._normalize_name_token(query)
        lowered_query = query.lower()
        detected: List[str] = []
        seen_tokens: set[str] = set()

        def consider(value: Optional[str]) -> None:
            if not value or len(detected) >= limit:
                return
            for variant in self._name_variations(str(value)):
                normalized_variant = self._normalize_name_token(variant)
                lowered_variant = variant.lower()
                if not normalized_variant or normalized_variant in seen_tokens:
                    continue
                if (
                    normalized_variant and normalized_variant in normalized_query
                ) or lowered_variant in lowered_query:
                    seen_tokens.add(normalized_variant)
                    detected.append(variant.strip())
                    break

        for entry in self.travel_data:
            consider(entry.get("place_name"))
            consider(entry.get("name"))
            consider(entry.get("name_th"))
            consider(entry.get("name_en"))
            consider(entry.get("city"))
            location = entry.get("location")
            if isinstance(location, dict):
                consider(location.get("district"))
            elif isinstance(location, str):
                consider(location)
            if len(detected) >= limit:
                break

        if len(detected) < limit:
            for entry in self.travel_data:
                types = entry.get("type") or []
                if isinstance(types, str):
                    types = [types]
                for type_value in types:
                    consider(str(type_value))
                    if len(detected) >= limit:
                        break
                if len(detected) >= limit:
                    break

        return detected

    def _load_travel_data_from_db(self) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        try:
            db_gen = get_db()
            db = next(db_gen)
            places = db.query(Place).all()
            for place in places:
                entries.append(place.to_dict())
        except Exception as e:
            print(f"[ERROR] Failed to load data from DB: {e}")
            return []

        return self._deduplicate_entries(entries)





    def _make_name_keys(self, *values: Optional[str]) -> List[str]:
        keys: List[str] = []
        for value in values:
            if not isinstance(value, str):
                continue
            for variant in self._name_variations(value):
                token = self._normalize_name_token(variant)
                if token and token not in keys:
                    keys.append(token)
        return keys

    @staticmethod
    def _name_variations(value: str) -> List[str]:
        variants: List[str] = []

        def add_variant(text: Optional[str]) -> None:
            if not text:
                return
            cleaned = text.strip()
            if cleaned and cleaned not in variants:
                variants.append(cleaned)

        add_variant(value)
        if "(" in value:
            before, _, remainder = value.partition("(")
            add_variant(before)
            inner, _, _ = remainder.partition(")")
            add_variant(inner)
        if "/" in value:
            for part in value.split("/"):
                add_variant(part)

        return variants

    @staticmethod
    def _normalize_name_token(text: Optional[str]) -> str:
        if not text:
            return ""
        normalized = re.sub(r"[^0-9a-zA-Z\u0E00-\u0E7F]+", "", text.strip().lower())
        return normalized


    @staticmethod
    def _summarize_day_plan(day_plan: Dict[str, Any]) -> str:
        title = day_plan.get("title", "")
        activities = day_plan.get("activities", []) or []
        steps: List[str] = []
        for activity in activities:
            if not isinstance(activity, dict):
                continue
            action = activity.get("action")
            description = activity.get("description")
            if action and description:
                steps.append(f"{action} ({description})")
            elif action:
                steps.append(action)
        actions = " -> ".join(steps)
        if title and actions:
            return f"{title}: {actions}"
        return title or actions

    @staticmethod
    def _summarize_route(route: Dict[str, Any]) -> str:
        start = route.get("start_point")
        order = route.get("route_order", []) or []
        if order:
            path = " -> ".join(order)
            if start:
                return f"เส้นทางแนะนำ: {start} -> {path}"
            return f"เส้นทางแนะนำ: {path}"
        return ""



    def _standardize_entry(
        self,
        entry: Dict[str, Any],
        *,
        source: str,
        priority: int,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(entry, dict):
            return None
        normalized = dict(entry)
        name_candidates = [
            normalized.get("place_name"),
            normalized.get("name"),
            normalized.get("name_th"),
            normalized.get("name_en"),
            normalized.get("title"),
        ]
        name = next((value for value in name_candidates if value), None)
        if not name:
            return None

        normalized["name"] = name
        normalized["place_name"] = normalized.get("place_name") or name
        normalized["_priority"] = priority
        normalized["source"] = source

        highlights = normalized.get("highlights")
        if isinstance(highlights, str):
            highlights = [highlights]
        elif not isinstance(highlights, list):
            highlights = []
        normalized["highlights"] = highlights

        if isinstance(normalized.get("type"), str):
            normalized["type"] = [normalized["type"]]  # type: ignore[list-item]
        elif not isinstance(normalized.get("type"), list):
            normalized["type"] = []

        description = normalized.get("description") or normalized.get("history") or ""
        normalized["description"] = description

        location = normalized.get("location")
        if not isinstance(location, dict):
            location = {}
        city = normalized.get("city")
        if not city:
            location_str = entry.get("location")
            if isinstance(location_str, str):
                city = self._extract_city_name(location_str)
        if city:
            normalized["city"] = city
            location.setdefault("district", city)
        location.setdefault("province", "สมุทรสงคราม")
        normalized["location"] = location

        info = normalized.get("place_information")
        if not isinstance(info, dict):
            info = {}
        if not info.get("detail"):
            info["detail"] = description
        if "highlights" not in info and highlights:
            info["highlights"] = highlights
        if "category_description" not in info:
            if normalized["type"]:
                info["category_description"] = ", ".join(str(t) for t in normalized["type"])
            else:
                info["category_description"] = normalized.get("category") or "travel"
        normalized["place_information"] = info

        # self._apply_image_links(normalized) # Removed

        if not normalized.get("id"):
            normalized["id"] = self._slugify_identifier(name)

        return normalized

    def _deduplicate_entries(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged: Dict[str, Dict[str, Any]] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            ident = entry.get("id") or self._slugify_identifier(entry.get("place_name", "") or "")
            if not ident:
                continue
            priority = entry.get("_priority", 0)
            existing = merged.get(ident)
            if existing and existing.get("_priority", 0) >= priority:
                continue
            normalized_entry = dict(entry)
            normalized_entry["id"] = ident
            normalized_entry["_priority"] = priority
            merged[ident] = normalized_entry

        final_entries: List[Dict[str, Any]] = []
        for entry in merged.values():
            entry.pop("_priority", None)
            final_entries.append(entry)
        return final_entries


    def _slugify_identifier(self, text: str) -> str:
        if not text:
            return hashlib.sha1(b"default").hexdigest()[:10]
        cleaned = re.sub(r"[^0-9a-zA-Z\u0E00-\u0E7F]+", "-", text.strip().lower())
        cleaned = cleaned.strip("-")
        if cleaned:
            return cleaned
        return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]

    @staticmethod
    def _extract_city_name(location_text: Optional[str]) -> str:
        if not isinstance(location_text, str):
            return ""
        text = location_text.strip()
        if not text:
            return ""
        for marker in ("อำเภอ", "อ.", "อำเภ"):
            if marker in text:
                after = text.split(marker, 1)[1].strip()
                return after.split()[0].strip(" ,")
        for marker in ("ตำบล", "ต.", "ตำบล"):
            if marker in text:
                after = text.split(marker, 1)[1].strip()
                return after.split()[0].strip(" ,")
        return text

    def _build_dataset_summary(self) -> str:
        if not self.travel_data:
            return ""
        lines = []
        for entry in self.travel_data:
            name = entry.get("name") or entry.get("place_name") or "unknown"
            city = entry.get("city") or entry.get("location", {}).get("district", "")
            entry_type = entry.get("type") or entry.get("category", "")
            if isinstance(entry_type, list):
                entry_type = ", ".join(str(t) for t in entry_type)
            lines.append(f"- {name} | city: {city} | type: {entry_type}")
        return "\n".join(lines[:50])

    def _build_local_reference_terms(self) -> List[str]:
        terms = {term.lower() for term in LOCAL_KEYWORDS}
        for entry in self.travel_data:
            for key in ("name", "place_name", "city", "type", "category"):
                value = entry.get(key)
                if isinstance(value, str):
                    terms.add(value.lower())
        return list(terms)

    def _interpret_query_keywords(self, query: str) -> Dict[str, List[str]]:
        if not self.gpt_service or not self.dataset_summary:
            return {"keywords": [], "places": []}
        try:
            return self.gpt_service.extract_query_entities(query, self.dataset_summary)
        except Exception as exc:
            print(f"[WARN] Query interpretation failed: {exc}")
            return {"keywords": [], "places": []}

    def _match_travel_data(
        self,
        query: str,
        keywords: Optional[List[str]] = None,
        limit: Optional[int] = None,
        boost_keywords: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        limit = limit or self.match_limit or 5
        
        # Use DB search
        results = search_places(query, limit=limit)
        
        # If keywords provided, try searching them too
        if keywords:
            for kw in keywords:
                if len(results) >= limit:
                    break
                kw_results = search_places(kw, limit=2)
                for res in kw_results:
                    if not any(r['id'] == res['id'] for r in results):
                        results.append(res)
                        
        return results[:limit]

    def _select_trip_guides_for_query(
        self,
        query: str,
        existing_ids: Optional[set[str]] = None,
        existing_titles: Optional[set[str]] = None,
    ) -> List[Dict[str, Any]]:
        if not getattr(self, "trip_guides", None):
            return []
        normalized = query.lower()
        matches: List[Dict[str, Any]] = []
        seen_ids = set(existing_ids or [])
        seen_titles = set(existing_titles or [])

        def add(slug: str) -> None:
            entry = self.trip_guides.get(slug)
            if not entry:
                return
            entry_id = self._entry_identifier(entry)
            if entry_id in seen_ids:
                return
            title_key = self._normalize_name_token(entry.get("place_name") or entry.get("name"))
            if title_key and title_key in seen_titles:
                return
            if entry not in matches:
                matches.append(entry)
                seen_ids.add(entry_id)
                if title_key:
                    seen_titles.add(title_key)

        if any(keyword in normalized for keyword in ("9 วัด", "๙ วัด", "ไหว้พระ", "temple tour", "nine temples")):
            add("9temples")
        if any(keyword in normalized for keyword in ("2 วัน", "สองวัน", "2-day", "2 day", "1 คืน", "ค้างคืน", "2d1n", "weekend")):
            add("2days1nighttrip")
        if any(keyword in normalized for keyword in ("1 วัน", "วันเดียว", "ครึ่งวัน", "half day", "one day")):
            add("1daytrip")
        return matches

    def _merge_structured_data(
        self,
        base: List[Dict[str, Any]],
        extras: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not extras:
            return base
        merged: Dict[str, Dict[str, Any]] = {}
        for entry in base:
            merged[self._entry_identifier(entry)] = entry
        for entry in extras:
            merged[self._entry_identifier(entry)] = entry
        return list(merged.values())

    def _trim_structured_results(
        self,
        entries: List[Dict[str, Any]],
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if not entries:
            return []
        max_count = limit or self.display_limit or self.match_limit or 5
        trimmed: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for entry in entries:
            ident = entry.get("id") or self._entry_identifier(entry)
            if ident in seen:
                continue
            seen.add(ident)
            trimmed.append(entry)
            if len(trimmed) >= max_count:
                break
        return trimmed


    def _entry_identifier(self, entry: Dict[str, Any]) -> str:
        ident = entry.get("id")
        if not ident:
            ident = self._slugify_identifier(entry.get("place_name") or entry.get("name") or repr(entry))
            entry["id"] = ident
        return ident

    def _is_trip_intent(self, normalized_query: str) -> bool:
        trip_keywords = (
            "ทริป",
            "แผนเที่ยว",
            "จัดทริป",
            "แผนการเดินทาง",
            "trip plan",
            "itinerary",
            "travel plan",
        )
        return any(keyword in normalized_query for keyword in trip_keywords)

    def _contains_local_reference(self, text: str) -> bool:
        lowered = text.lower()
        return any(term in lowered for term in self.local_reference_terms)

    def _mentions_other_province(self, query: str, keyword_pool: List[str], places: List[str]) -> bool:
        normalized = query.lower()
        province_match = re.search(r'จังหวัด\s*([^\s,.;!?]+)', normalized)
        if province_match:
            name = province_match.group(1)
            if not self._contains_local_reference(name):
                return True

        for candidate in places:
            candidate_str = str(candidate).lower()
            if candidate_str and not self._contains_local_reference(candidate_str):
                return True

        for keyword in keyword_pool:
            kw = str(keyword).lower()
            if kw and "จังหวัด" in kw and not self._contains_local_reference(kw):
                return True

        return False

    def _refresh_settings(self) -> None:
        self.chatbot_prompts = PROMPT_REPO.get_prompt("chatbot/answer", default=self.chatbot_prompts)
        self.preferences = PROMPT_REPO.get_preferences()
        self.runtime_config = PROMPT_REPO.get_runtime_config()
        self.match_limit = self.runtime_config.get("matching", {}).get("max_matches", 5)

    def _preference_context(self) -> str:
        prefs = self.preferences or {}
        components = []
        if tone := prefs.get("tone"):
            components.append(f"Preferred tone: {tone}")
        if style := prefs.get("response_style"):
            components.append(f"Response style: {style}")
        if format_hint := prefs.get("format"):
            components.append(f"Format guide: {format_hint}")
        if cta := prefs.get("call_to_action"):
            components.append(cta)
        return " | ".join(components)

    def _character_context(self) -> str:
        profile = self.character_profile or {}
        parts = []
        name = profile.get("name")
        if name:
            parts.append(f"Character: {name}")
        if profile.get("characteristics"):
            parts.extend(profile["characteristics"])
        if profile.get("knowledge_scope"):
            parts.append("Knowledge scope: " + ", ".join(profile["knowledge_scope"]))
        return " | ".join(parts)

    def _create_simple_response(self, context_data: List[Dict], language: str) -> str:
        if not context_data:
            return self._prompt_path(
                language,
                ("simple_response", "no_data"),
                default_th=(
                    "สวัสดีค่ะ! ขออภัยที่ตอนนี้ระบบ AI กำลังมีปัญหาชั่วคราว "
                    "แต่น้องปลาทูยังพร้อมให้ข้อมูลการท่องเที่ยวสมุทรสงครามให้คุณนะคะ "
                    "ลองถามเกี่ยวกับสถานที่ท่องเที่ยว ร้านอาหาร หรือที่พักในสมุทรสงครามได้เลยค่ะ"
                ),
                default_en=(
                    "Hello! I apologize for the temporary AI system issue, but I'm still ready "
                    "to provide tourism information about Samut Songkhram. Feel free to ask "
                    "about attractions, restaurants, or accommodations!"
                )
            )

        def summarize_entry(entry: Dict[str, Any], idx: int) -> str:
            name = entry.get("name") or entry.get("place_name") or "Unknown"
            location = entry.get("city") or entry.get("location", {}).get("district")
            description = (
                entry.get("description")
                or entry.get("place_information", {}).get("detail")
                or ""
            )
            highlights = entry.get("highlights") or entry.get("place_information", {}).get("highlights") or []
            best_time = entry.get("best_time") or entry.get("place_information", {}).get("best_time")
            tips = entry.get("tips") or entry.get("place_information", {}).get("tips")

            def join_highlights(items: Any) -> str:
                if isinstance(items, list):
                    return ", ".join(str(item) for item in items[:3])
                return str(items)

            if language == "th":
                lines = [f"{idx}. {name}"]
                if location:
                    lines.append(f"   พื้นที่: {location}")
                if description:
                    lines.append(f"   จุดเด่น: {description}")
                if highlights:
                    lines.append(f"   ไฮไลต์: {join_highlights(highlights)}")
                if best_time:
                    lines.append(f"   เวลาแนะนำ: {best_time}")
                if tips:
                    lines.append(f"   เคล็ดลับ: {join_highlights(tips)}")
            else:
                lines = [f"{idx}. {name}"]
                if location:
                    lines.append(f"   Area: {location}")
                if description:
                    lines.append(f"   Why visit: {description}")
                if highlights:
                    lines.append(f"   Highlights: {join_highlights(highlights)}")
                if best_time:
                    lines.append(f"   Best time: {best_time}")
                if tips:
                    lines.append(f"   Tips: {join_highlights(tips)}")
            return "\n".join(lines)

        intro_template = self._prompt_path(
            language,
            ("simple_response", "intro"),
            default_th=(
                "“น้องปลาทู” ได้เตรียมข้อมูลจากฐานข้อมูลสมุทรสงครามมาให้ {count} สถานที่ค่ะ "
                "รายละเอียดแต่ละจุดอยู่ด้านล่างเลยนะคะ:"
            ),
            default_en=(
                "Here are {count} verified Samut Songkhram spots that match your question. "
                "Check the details below:"
            )
        )
        outro = self._prompt_path(
            language,
            ("simple_response", "outro"),
            default_th="\nหากต้องการข้อมูลเพิ่มเติม สามารถถามเพิ่มได้เลยค่ะ 😊",
            default_en="\nFeel free to ask for more information! 😊"
        )

        max_entries = 3
        summaries = [
            summarize_entry(entry, idx)
            for idx, entry in enumerate(context_data[:max_entries], 1)
        ]
        if len(context_data) > max_entries:
            remaining_note = (
                f"\n... และยังมีอีก {len(context_data) - max_entries} สถานที่ที่เกี่ยวข้องค่ะ"
                if language == "th"
                else f"\n... plus {len(context_data) - max_entries} more related places."
            )
        else:
            remaining_note = ""

        body = "\n\n".join(summaries)
        return f"{intro_template.format(count=len(context_data))}\n\n{body}{remaining_note}{outro}"

    def _prompt(self, key: str, language: str, *, default_th: str = "", default_en: str = "") -> str:
        return self._prompt_path(language, (key,), default_th=default_th, default_en=default_en)

    def _prompt_path(
        self,
        language: str,
        keys: tuple[str, ...],
        *,
        default_th: str = "",
        default_en: str = ""
    ) -> str:
        default_value = default_th if language == "th" else default_en
        node: Any = self.chatbot_prompts
        for key in keys:
            if not isinstance(node, dict):
                node = None
                break
            node = node.get(key)
        if isinstance(node, dict):
            return node.get(language, default_value)
        if isinstance(node, str):
            return node
        return default_value

    def _intent_from_topic(self, topic: Optional[str]) -> str:
        if not topic:
            return "general"
        mapping = {
            "general_travel": "attractions",
            "amphawa": "attractions",
            "bang_kung": "attractions",
            "khlong_khon": "attractions",
            "food": "restaurants",
            "accommodation": "accommodation",
            "transportation": "transportation",
        }
        return mapping.get(topic, "general")

    # ------------------------------------------------------------------
    # Basic GPT-only fallback (no DB enrichment)
    # ------------------------------------------------------------------
    def _pure_gpt_response(self, user_message: str, language: str) -> Dict[str, Any]:
        """Generate a response using only GPT and character persona (no structured data)."""
        character_note = self._character_context()
        preference_note = self._preference_context()
        system_hint_th = (
            "คุณคือน้องปลาทู แอดมิน AI ผู้ช่วยแนะนำการท่องเที่ยวจังหวัดสมุทรสงคราม "
            "ตอนนี้ฐานข้อมูลภายในยังไม่พร้อม ให้ตอบโดยใช้ความรู้ทั่วไปและรักษาคาแรกเตอร์ที่อบอุ่น เป็นมิตร และช่วยเหลือดี"
        )
        system_hint_en = (
            "You are Nong Pla Too, an AI travel assistant for Samut Songkhram. "
            "The internal database is currently unavailable; respond with general helpful knowledge while preserving the friendly persona."
        )
        if self.gpt_service:
            try:
                gpt_payload = self.gpt_service.generate_response(
                    user_query=user_message,
                    context_data=[],
                    data_type='travel',
                    intent='general',
                    data_status={
                        'success': False,
                        'message': 'Database unavailable; pure GPT persona response',
                        'data_available': False,
                        'source': 'none',
                        'preference_note': preference_note,
                        'character_note': character_note,
                    },
                    system_override=system_hint_th if language == 'th' else system_hint_en,
                )
                return {
                    'response': gpt_payload.get('response', ''),
                    'structured_data': [],
                    'language': language,
                    'source': 'gpt_fallback',
                    'intent': 'general',
                    'tokens_used': gpt_payload.get('tokens_used'),
                    'data_status': {
                        'success': False,
                        'message': 'Pure GPT fallback',
                        'data_available': False,
                        'source': 'none',
                        'preference_note': preference_note,
                        'character_note': character_note,
                    }
                }
            except Exception as exc:
                print(f"[ERROR] Pure GPT fallback failed: {exc}")
        # Static persona reply if GPT path fails
        if language == 'th':
            reply = (
                "สวัสดีค่ะ น้องปลาทูขออภัย ฐานข้อมูลยังไม่พร้อมใช้งานตอนนี้ "
                "หากต้องการสถานที่เที่ยว แนะนำให้ลองระบุกลุ่มสถานที่หรือบรรยากาศที่สนใจค่ะ"
            )
        else:
            reply = (
                "Hi! The internal database is currently unavailable. "
                "If you share the type of place or vibe you want, I can still help."
            )
        return {
            'response': reply,
            'structured_data': [],
            'language': language,
            'source': 'static_persona_fallback',
            'intent': 'general',
            'data_status': {
                'success': False,
                'message': 'Static persona fallback',
                'data_available': False,
                'source': 'none',
                'preference_note': preference_note,
                'character_note': character_note,
            }
        }

    def get_response(self, user_message: str, user_id: str = "default") -> Dict[str, Any]:
        language = self._detect_language(user_message)
        self._refresh_settings()
        trimmed_query = user_message.strip()
        normalized_query = trimmed_query.lower()
        dedup_key = self._normalized_query_key(trimmed_query) if trimmed_query else ""
        cached_payload = self._replay_duplicate_response(user_id, dedup_key)
        if cached_payload:
            return cached_payload

        def finalize_response(payload: Dict[str, Any]) -> Dict[str, Any]:
            self._cache_response(user_id, dedup_key, payload)
            return payload
        greetings_th = ("สวัสดี", "หวัดดี", "ดีจ้า", "สวัสดีค่ะ", "สวัสดีครับ")
        greetings_en = ("hello", "hi", "hey", "greetings")
        if trimmed_query and any(word in normalized_query for word in greetings_th + greetings_en):
            greeting_profile = self.character_profile.get("greeting", {}) if self.character_profile else {}
            if language == "th":
                greeting_text = greeting_profile.get(
                    "th",
                    "สวัสดีค่ะ! น้องปลาทูพร้อมช่วยแนะนำทริปในสมุทรสงครามให้เลยค่ะ"
                )
            else:
                greeting_text = greeting_profile.get(
                    "en",
                    "Hello! I'm Nong Pla Too, happy to help plan your Samut Songkhram adventures!"
                )
            return finalize_response({
                'response': greeting_text,
                'structured_data': [],
                'language': language,
                'source': 'greeting',
                'intent': 'greeting',
                'data_status': {
                    'success': True,
                    'message': 'Greeting response',
                    'data_available': False,
                    'source': 'local_json',
                    'preference_note': self._preference_context(),
                    'character_note': self._character_context()
                }
            })

        analysis = self._interpret_query_keywords(user_message) if trimmed_query else {"keywords": [], "places": []}
        matcher_signals = self._matcher_analysis(user_message)
        keyword_pool = self._merge_keywords(
            analysis.get("keywords") or [],
            analysis.get("places") or [],
            matcher_signals.get("keywords") or [],
        )
        auto_keywords_used = False
        fallback_keywords: List[str] = []
        if not keyword_pool:
            fallback_keywords = self._auto_detect_keywords(user_message)
            if fallback_keywords:
                keyword_pool = self._merge_keywords(keyword_pool, fallback_keywords)
                auto_keywords_used = True

        matched_data = self._match_travel_data(
            user_message,
            keywords=keyword_pool,
            boost_keywords=matcher_signals.get("keywords"),
        )
        if not matched_data and not auto_keywords_used:
            fallback_keywords = self._auto_detect_keywords(user_message)
            if fallback_keywords:
                keyword_pool = self._merge_keywords(keyword_pool, fallback_keywords)
                matched_data = self._match_travel_data(
                    user_message,
                    keywords=keyword_pool,
                    boost_keywords=matcher_signals.get("keywords"),
                )
                auto_keywords_used = True
        existing_ids = {self._entry_identifier(entry) for entry in matched_data}
        existing_titles: set[str] = set()
        for entry in matched_data:
            if not isinstance(entry, dict):
                continue
            title = entry.get("place_name") or entry.get("name")
            title_key = self._normalize_name_token(title)
            if title_key:
                existing_titles.add(title_key)
        trip_matches = self._select_trip_guides_for_query(
            user_message,
            existing_ids,
            existing_titles,
        )
        if trip_matches:
            matched_data = self._merge_structured_data(matched_data, trip_matches)
        matched_data = self._trim_structured_results(matched_data)
        preference_note = self._preference_context()
        character_note = self._character_context()
        includes_local_term = self._contains_local_reference(user_message)
        if not includes_local_term:
            includes_local_term = any(self._contains_local_reference(str(keyword)) for keyword in keyword_pool)
        if matcher_signals.get("is_local"):
            includes_local_term = True
        mentions_other_province = (
            not includes_local_term
            and self._mentions_other_province(user_message, keyword_pool, analysis.get("places", []))
        )
        detected_intent = self._intent_from_topic(matcher_signals.get("topic"))
        data_status = {
            'success': bool(matched_data),
            'message': (
                f"Matched {len(matched_data)} Samut Songkhram entries using keywords: {keyword_pool}"
                if matched_data else
                f"No Samut Songkhram entries matched for keywords: {keyword_pool}"
            ),
            'data_available': bool(matched_data),
            'source': 'local_json',
            'preference_note': preference_note,
            'character_note': character_note,
            'matching_signals': {
                'topic': matcher_signals.get("topic"),
                'topic_confidence': round(float(matcher_signals.get("confidence", 0.0)), 3),
                'is_local': matcher_signals.get("is_local"),
                'keywords': keyword_pool,
            },
        }

        if mentions_other_province:
            warning_message = (
                "น้องปลาทูจะให้ข้อมูลได้ชัดเจนและครอบคลุม หากถามข้อมูลในจังหวัดสมุทรสงครามค่ะ ขออภัยด้วยนะคะ"
            )
            return finalize_response({
                'response': warning_message,
                'structured_data': [],
                'language': language,
                'source': 'out_of_scope',
                'intent': 'general',
                'data_status': {
                    **data_status,
                    'message': 'Out of supported province scope',
                    'data_available': False
                }
            })

        if not user_message.strip():
            simple_msg = self._prompt(
                "empty_query",
                language,
                default_th="กรุณาพิมพ์คำถามเกี่ยวกับการท่องเที่ยวในสมุทรสงครามนะคะ",
                default_en="Please share a travel question for Samut Songkhram."
            )
            return finalize_response({
                'response': simple_msg,
                'structured_data': [],
                'language': language,
                'source': 'empty_query',
                'data_status': data_status
            })

        if self.gpt_service:
            try:
                gpt_result = self.gpt_service.generate_response(
                    user_query=user_message,
                    context_data=matched_data,
                    data_type='travel',
                    intent=detected_intent,
                    data_status=data_status
                )

                return finalize_response({
                    'response': gpt_result['response'],
                    'structured_data': matched_data,
                    'language': language,
                    'source': gpt_result.get('source', 'openai'),
                    'intent': detected_intent,
                    'tokens_used': gpt_result.get('tokens_used'),
                    'data_status': data_status,
                    'character_note': character_note
                })
                
            except Exception as e:
                print(f"[ERROR] GPT generation failed: {e}")
                simple_response = self._create_simple_response(matched_data, language)
                return finalize_response({
                    'response': simple_response,
                    'structured_data': matched_data,
                    'language': language,
                    'source': 'simple_fallback',
                    'intent': detected_intent,
                    'gpt_error': str(e),
                    'data_status': data_status
                })
        else:
            simple_response = self._create_simple_response(matched_data, language)
            return finalize_response({
                'response': simple_response,
                'structured_data': matched_data,
                'language': language,
                'source': 'simple',
                'intent': detected_intent,
                'data_status': data_status
            })


_CHATBOT: Optional[TravelChatbot] = None


def chat_with_bot(message: str, user_id: str = "default") -> str:
    global _CHATBOT
    if _CHATBOT is None:
        _CHATBOT = TravelChatbot()
    
    result = _CHATBOT.get_response(message, user_id)
    return result['response']


def get_chat_response(message: str, user_id: str = "default") -> Dict[str, Any]:
    global _CHATBOT
    if _CHATBOT is None:
        _CHATBOT = TravelChatbot()
    language = _CHATBOT._detect_language(message)

    # Detect DB connectivity (adaptive branch)
    db_connected = False
    if DB_SERVICE_AVAILABLE:
        try:
            svc = get_db_service()
            db_connected = svc.test_connection()
        except Exception as exc:
            print(f"[WARN] DB connectivity check failed: {exc}")
            db_connected = False

    if not db_connected:
        result = _CHATBOT._pure_gpt_response(message, language)
    else:
        result = _CHATBOT.get_response(message, user_id)

    # Attach model + character info uniformly
    try:
        model_params = PROMPT_REPO.get_model_params()
        result['model'] = model_params.get('default_model', 'gpt-4o')
    except Exception:
        result['model'] = 'gpt-4o'
    try:
        result['character'] = (_CHATBOT.character_profile or {}).get('name', 'NongPlaToo')
    except Exception:
        result['character'] = 'NongPlaToo'
    # Add source qualifier for clarity
    if not db_connected and result.get('source') and 'fallback' in result['source']:
        result['source'] = result['source'] + '_no_db'
    elif db_connected and result.get('source') and 'openai' in result['source']:
        result['source'] = 'data+ai'
    elif db_connected and result.get('source') == 'simple':
        result['source'] = 'data+simple'
    return result


if __name__ == "__main__":
    print("NongPlaToo GPT Travel Assistant ready. Type 'quit' to exit.")
    bot = TravelChatbot()
    
    while True:
        user_text = input("\nYou: ")
        if user_text.strip().lower() in {"quit", "exit", "bye"}:
            break
        
        result = bot.get_response(user_text)
        
        print(f"\nBot ({result['source']}): {result['response']}")
        
        if result.get('structured_data'):
            print(f"\n[Structured items: {len(result['structured_data'])}]")

        
        if result.get('tokens_used'):
            print(f"[Tokens: {result['tokens_used']}]")
