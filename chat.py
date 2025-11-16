"""GPT chatbot for Samut Songkhram tourism. OPENAI_MODEL (default: gpt-5)."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from world_journey_ai.configs import PromptRepo

try:
    from gpt_service import GPTService
    GPT_AVAILABLE = True
except Exception as exc:
    print(f"[WARN] GPT service import failed: {exc}")
    GPT_AVAILABLE = False
    GPTService = None

PROMPT_REPO = PromptRepo()
DATA_FILE = Path(__file__).resolve().parent / "world_journey_ai" / "data" / "travel_data.json"


class TravelChatbot:
    """Chatbot powered solely by GPT (local data + prompts)."""

    def __init__(self) -> None:
        self.bot_name = "NongPlaToo"
        self.chatbot_prompts = PROMPT_REPO.get_prompt("chatbot/answer", default={})
        self.preferences = PROMPT_REPO.get_preferences()
        self.runtime_config = PROMPT_REPO.get_runtime_config()
        self.match_limit = self.runtime_config.get("matching", {}).get("max_matches", 5)
        self.gpt_service: Optional[Any] = None
        self.travel_data = self._load_travel_data()
        self.dataset_summary = self._build_dataset_summary()

        if GPT_AVAILABLE and GPTService is not None:
            try:
                self.gpt_service = GPTService()
                print("[OK] GPT service initialized")
            except Exception as exc:
                print(f"[ERROR] Cannot initialize GPT service: {exc}")
                self.gpt_service = None
        else:
            print("[WARN] GPT service unavailable")

    @staticmethod
    def _detect_language(text: str) -> str:
        thai_chars = sum(1 for ch in text if "\u0e00" <= ch <= "\u0e7f")
        return "th" if thai_chars > max(1, len(text) // 3) else "en"

    def _load_travel_data(self) -> List[Dict[str, Any]]:
        if not DATA_FILE.exists():
            print(f"[WARN] Travel data file not found: {DATA_FILE}")
            return []
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                if isinstance(data, list):
                    return data
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[WARN] Cannot load travel data: {exc}")
        return []

    def _build_dataset_summary(self) -> str:
        if not self.travel_data:
            return ""
        lines = []
        for entry in self.travel_data:
            name = entry.get("name") or entry.get("place_name") or "unknown"
            city = entry.get("city") or entry.get("location", {}).get("district", "")
            entry_type = entry.get("type", entry.get("category", ""))
            lines.append(f"- {name} | city: {city} | type: {entry_type}")
        return "\n".join(lines[:50])

    def _interpret_query_keywords(self, query: str) -> Dict[str, List[str]]:
        if not self.gpt_service or not self.dataset_summary:
            return {"keywords": [], "places": []}
        try:
            return self.gpt_service.extract_query_entities(query, self.dataset_summary)
        except Exception as exc:
            print(f"[WARN] Query interpretation failed: {exc}")
            return {"keywords": [], "places": []}

    def _match_travel_data(self, query: str, keywords: Optional[List[str]] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        if not self.travel_data:
            return []
        limit = limit or self.match_limit or 5
        normalized = query.lower()
        tokens = [tok for tok in normalized.split() if tok]
        keyword_list = [kw.lower() for kw in (keywords or []) if kw]
        scored: List[tuple[Dict[str, Any], int]] = []
        for entry in self.travel_data:
            haystack = " ".join(
                str(entry.get(field, "")).lower()
                for field in ("name", "description", "city", "highlights")
            )
            score = 0
            if normalized in haystack:
                score += 3
            for token in tokens:
                if token in haystack:
                    score += 1
            for kw in keyword_list:
                if kw in haystack:
                    score += 3
            if score > 0:
                scored.append((entry, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        if not scored:
            return []
        return [item for item, _ in scored[:limit]]

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
        intro_template = self._prompt_path(
            language,
            ("simple_response", "intro"),
            default_th=(
                "“น้องปลาทู” จะให้ข้อมูลได้ชัดเจนและครอบคลุม หากถามข้อมูลในจังหวัดสมุทรสงครามค่ะ ขออภัยด้วยนะคะ\n\n"
                "พบข้อมูลที่คุณสนใจ {count} รายการค่ะ คุณสามารถดูรายละเอียดเพิ่มเติมด้านล่างนะคะ:"
            ),
            default_en=(
                "Hello! I'm NongPlaToo, your Samut Songkhram travel guide \n\n"
                "I found {count} place(s) that might interest you. Check out the details below:"
            )
        )
        outro = self._prompt_path(
            language,
            ("simple_response", "outro"),
            default_th="\nหากต้องการข้อมูลเพิ่มเติม สามารถถามเพิ่มได้เลยค่ะ 😊",
            default_en="\nFeel free to ask for more information! 😊"
        )
        return f"{intro_template.format(count=len(context_data))}{outro}"

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

    def get_response(self, user_message: str, user_id: str = "default") -> Dict[str, Any]:
        language = self._detect_language(user_message)
        self._refresh_settings()
        analysis = self._interpret_query_keywords(user_message) if user_message.strip() else {"keywords": [], "places": []}
        keyword_pool = (analysis.get("keywords") or []) + (analysis.get("places") or [])
        matched_data = self._match_travel_data(user_message, keywords=keyword_pool)
        preference_note = self._preference_context()
        data_status = {
            'success': bool(matched_data),
            'message': (
                f"Matched local entries using keywords: {keyword_pool}"
                if matched_data else
                f"No local entries matched for keywords: {keyword_pool}"
            ),
            'data_available': bool(matched_data),
            'source': 'local_json',
            'preference_note': preference_note
        }

        if not user_message.strip():
            simple_msg = self._prompt(
                "empty_query",
                language,
                default_th="กรุณาพิมพ์คำถามเกี่ยวกับการท่องเที่ยวในสมุทรสงครามนะคะ",
                default_en="Please share a travel question for Samut Songkhram."
            )
            return {
                'response': simple_msg,
                'structured_data': [],
                'language': language,
                'source': 'empty_query',
                'data_status': data_status
            }

        if self.gpt_service:
            try:
                gpt_result = self.gpt_service.generate_response(
                    user_query=user_message,
                    context_data=matched_data,
                    data_type='travel',
                    intent='general',
                    data_status=data_status
                )

                return {
                    'response': gpt_result['response'],
                    'structured_data': matched_data,
                    'language': language,
                    'source': gpt_result.get('source', 'openai'),
                    'intent': 'general',
                    'tokens_used': gpt_result.get('tokens_used'),
                    'data_status': data_status
                }
                
            except Exception as e:
                print(f"[ERROR] GPT generation failed: {e}")
                simple_response = self._create_simple_response(matched_data, language)
                return {
                    'response': simple_response,
                    'structured_data': matched_data,
                    'language': language,
                    'source': 'simple_fallback',
                    'intent': 'general',
                    'gpt_error': str(e),
                    'data_status': data_status
                }
        else:
            simple_response = self._create_simple_response(matched_data, language)
            return {
                'response': simple_response,
                'structured_data': matched_data,
                'language': language,
                'source': 'simple',
                'intent': 'general',
                'data_status': data_status
            }


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
    
    return _CHATBOT.get_response(message, user_id)


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
