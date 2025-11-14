"""GPT chatbot for Samut Songkhram tourism. OPENAI_MODEL (default: gpt-5)."""

import random
from typing import Any, Dict, List, Optional

try:
    from tat_api import TATAPIService
    TAT_AVAILABLE = True
except Exception as exc:
    print(f"[WARN] TAT API import failed: {exc}")
    TAT_AVAILABLE = False
    TATAPIService = None

try:
    from gpt_service import GPTService
    GPT_AVAILABLE = True
except Exception as exc:
    print(f"[WARN] GPT service import failed: {exc}")
    GPT_AVAILABLE = False
    GPTService = None


class TravelChatbot:
    """Chatbot with TAT + configurable GPT"""

    DEFAULT_PROVINCE = "สมุทรสงคราม"

    def __init__(self) -> None:
        self.bot_name = "NongPlaToo"
        self.tat_service: Optional[Any] = None
        self.gpt_service: Optional[Any] = None

        if TAT_AVAILABLE and TATAPIService is not None:
            try:
                self.tat_service = TATAPIService()
                print("[OK] TAT API initialized")
            except Exception as exc:
                print(f"[ERROR] Cannot initialize TAT API: {exc}")
                self.tat_service = None
        else:
            print("[WARN] TAT API unavailable")

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

    def _create_simple_response(self, tat_data: List[Dict], language: str) -> str:
        if not tat_data:
            if language == "th":
                return "สวัสดีค่ะ! ขออภัยที่ตอนนี้ระบบ AI กำลังมีปัญหาชั่วคราว แต่น้องปลาทูยังพร้อมให้ข้อมูลการท่องเที่ยวสมุทรสงครามให้คุณนะคะ ลองถามเกี่ยวกับสถานที่ท่องเที่ยว ร้านอาหาร หรือที่พักในสมุทรสงครามได้เลยค่ะ"
            return "Hello! I apologize for the temporary AI system issue, but I'm still ready to provide tourism information about Samut Songkhram. Feel free to ask about attractions, restaurants, or accommodations!"

        lines = []
        
        if language == "th":
            lines.append("“น้องปลาทู” จะให้ข้อมูลได้ชัดเจนและครอบคลุม หากถามข้อมูลในจังหวัดสมุทรสงครามค่ะ ขออภัยด้วยนะคะ\n")
            lines.append(f"พบข้อมูลที่คุณสนใจ {len(tat_data)} รายการค่ะ คุณสามารถดูรายละเอียดเพิ่มเติมด้านล่างนะคะ:")
        else:
            lines.append("Hello! I'm NongPlaToo, your Samut Songkhram travel guide \n")
            lines.append(f"I found {len(tat_data)} place(s) that might interest you. Check out the details below:")

        if language == "th":
            lines.append("\nหากต้องการข้อมูลเพิ่มเติม สามารถถามเพิ่มได้เลยค่ะ 😊")
        else:
            lines.append("\nFeel free to ask for more information! 😊")

        return "\n".join(lines)

    def get_response(self, user_message: str, user_id: str = "default") -> Dict[str, Any]:
        language = self._detect_language(user_message)

        if not user_message.strip():
            simple_msg = (
                "กรุณาพิมพ์คำถามเกี่ยวกับการท่องเที่ยวในสมุทรสงครามนะคะ"
                if language == "th"
                else "Please share a travel question for Samut Songkhram."
            )
            return {
                'response': simple_msg,
                'structured_data': [],
                'language': language,
                'source': 'empty_query'
            }

        if not self.tat_service:
            error_msg = (
                "ขออภัยค่ะ ระบบข้อมูลยังไม่พร้อมในตอนนี้"
                if language == "th"
                else "Sorry, the travel data service is not available right now."
            )
            return {
                'response': error_msg,
                'structured_data': [],
                'language': language,
                'source': 'no_tat_service'
            }

        try:
            tat_result = self.tat_service.search_by_intent(
                user_message, 
                self.DEFAULT_PROVINCE, 
                limit=5
            )
            
            tat_data = tat_result.get('data', [])
            primary_intent = tat_result.get('primary_intent', 'attractions')
            
            print(f"[INFO] Intent: {primary_intent}, Found {len(tat_data)} TAT records")
            
        except Exception as e:
            print(f"[ERROR] TAT search failed: {e}")
            error_msg = (
                "ขออภัยค่ะ เกิดข้อผิดพลาดในการค้นหาข้อมูล"
                if language == "th"
                else "Sorry, an error occurred while searching for information."
            )
            return {
                'response': error_msg,
                'structured_data': [],
                'language': language,
                'source': 'tat_error',
                'error': str(e)
            }

        if self.gpt_service:
            try:
                gpt_result = self.gpt_service.generate_response(
                    user_query=user_message,
                    tat_data=tat_data,
                    data_type=primary_intent,
                    intent=primary_intent
                )
                
                return {
                    'response': gpt_result['response'],
                    'structured_data': tat_data,
                    'language': language,
                    'source': gpt_result.get('source', 'openai'),
                    'intent': primary_intent,
                    'tokens_used': gpt_result.get('tokens_used')
                }
                
            except Exception as e:
                print(f"[ERROR] GPT generation failed: {e}")
                simple_response = self._create_simple_response(tat_data, language)
                return {
                    'response': simple_response,
                    'structured_data': tat_data,
                    'language': language,
                    'source': 'simple_fallback',
                    'intent': primary_intent,
                    'gpt_error': str(e)
                }
        else:
            simple_response = self._create_simple_response(tat_data, language)
            return {
                'response': simple_response,
                'structured_data': tat_data,
                'language': language,
                'source': 'simple',
                'intent': primary_intent
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
            print(f"\n[Found {len(result['structured_data'])} TAT records]")
        
        if result.get('tokens_used'):
            print(f"[Tokens: {result['tokens_used']}]")