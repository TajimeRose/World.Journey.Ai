"""OpenAI service for travel assistant. TAT data + GPT (OPENAI_MODEL, default: gpt-5)."""

import os
import json
from typing import Dict, List, Optional, Any
from openai import OpenAI

class GPTService:
    """Generate travel guidance using OpenAI + TAT data"""
    
    # System prompt removed per user request
    SYSTEM_PROMPT = ""

    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model_name = os.getenv('OPENAI_MODEL', 'gpt-5')
        
        if not self.api_key:
            print("[WARN] OPENAI_API_KEY not found")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=self.api_key)
                print(f"[OK] OpenAI client init (model: {self.model_name})")
                if self.model_name.lower() == 'gpt-5':
                    print("[WARN] gpt-5 not available yet; expect fallback")
            except Exception as e:
                print(f"[ERROR] OpenAI client init failed: {e}")
                self.client = None
    
    def _format_messages_for_input(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert legacy chat messages into the Responses API input format."""
        formatted: List[Dict[str, Any]] = []
        for message in messages:
            role = message.get('role', 'user')
            content = message.get('content', '')
            parts: List[Dict[str, str]] = []

            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get('type'):
                        parts.append(item)
                    elif isinstance(item, dict) and 'text' in item:
                        parts.append({
                            'type': 'text',
                            'text': str(item.get('text', ''))
                        })
                    else:
                        parts.append({'type': 'text', 'text': str(item)})
            else:
                parts.append({'type': 'text', 'text': str(content or '')})

            formatted.append({'role': role, 'content': parts})
        return formatted

    def _create_chat_completion(self, **kwargs):
        """Call responses.create while preserving previous call signature compatibility."""
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")

        messages = kwargs.pop('messages', None)
        if not messages:
            raise ValueError("messages are required for OpenAI calls")

        request_kwargs = dict(kwargs)
        model = request_kwargs.pop('model', self.model_name)

        max_completion = request_kwargs.pop('max_completion_tokens', None)
        max_tokens = request_kwargs.pop('max_tokens', None)
        if max_completion is not None:
            request_kwargs['max_output_tokens'] = max_completion
        elif max_tokens is not None:
            request_kwargs['max_output_tokens'] = max_tokens

        request_kwargs['model'] = model
        request_kwargs['input'] = self._format_messages_for_input(messages)
        return self.client.responses.create(**request_kwargs)

    def _extract_response_text(self, response: Any) -> str:
        """Extract plain text from a Responses API call (with chat.completions fallback)."""
        if not response:
            return ""

        output_text = getattr(response, 'output_text', None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        text_chunks: List[str] = []

        output_attr = getattr(response, 'output', None)
        if output_attr:
            for output_item in output_attr:
                content_list = getattr(output_item, 'content', None) or []
                for content_item in content_list:
                    text_value = None
                    if hasattr(content_item, 'text'):
                        text_field = getattr(content_item, 'text')
                        if isinstance(text_field, str):
                            text_value = text_field
                        else:
                            text_value = getattr(text_field, 'value', None) or getattr(text_field, 'text', None)
                    elif isinstance(content_item, dict):
                        if isinstance(content_item.get('text'), dict):
                            text_value = content_item['text'].get('value') or content_item['text'].get('text')
                        elif isinstance(content_item.get('text'), str):
                            text_value = content_item['text']
                        elif content_item.get('type') == 'text':
                            text_value = content_item.get('content') or content_item.get('value')
                    elif isinstance(content_item, str):
                        text_value = content_item

                    if text_value:
                        text_chunks.append(text_value)

            if text_chunks:
                return "\n".join(chunk for chunk in text_chunks if chunk).strip()

        choices = getattr(response, 'choices', None)
        if choices:
            first_choice = choices[0]
            message = getattr(first_choice, 'message', None)
            if message:
                content = getattr(message, 'content', '')
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    combined = [str(part) for part in content if part]
                    if combined:
                        return "\n".join(combined)

        response_dump = None
        if hasattr(response, 'model_dump'):
            try:
                response_dump = response.model_dump()
            except Exception:
                response_dump = None
        elif isinstance(response, dict):
            response_dump = response

        if isinstance(response_dump, dict):
            outputs = response_dump.get('output') or response_dump.get('outputs')
            if outputs:
                text_chunks = []
                for output_item in outputs:
                    for content in output_item.get('content') or []:
                        text = content.get('text')
                        if isinstance(text, dict):
                            value = text.get('value') or text.get('text')
                        else:
                            value = text
                        if value:
                            text_chunks.append(value)
                if text_chunks:
                    return "\n".join(text_chunks).strip()

        return ""

    def _detect_language(self, text: str) -> str:
        thai_chars = sum(1 for ch in text if '\u0e00' <= ch <= '\u0e7f')
        return "th" if thai_chars > len(text) * 0.3 else "en"
    
    def _format_tat_data_for_context(self, tat_data: List[Dict], data_type: str) -> str:
        if not tat_data:
            return "No TAT data available for this query."
        
        context_parts = [f"=== VERIFIED TAT DATA ({data_type.upper()}) ===\n"]
        
        for idx, item in enumerate(tat_data[:5], 1):
            context_parts.append(f"\n[Place {idx}]")
            
            name = item.get('place_name') or item.get('name') or 'Unknown'
            context_parts.append(f"Name: {name}")
            
            location = item.get('location', {})
            if location:
                district = location.get('district', '')
                province = location.get('province', '')
                if district:
                    context_parts.append(f"Location: {district}, {province}")
                elif province:
                    context_parts.append(f"Location: {province}")
            
            place_info = item.get('place_information', {})
            if place_info:
                detail = place_info.get('detail', '')
                if detail:
                    context_parts.append(f"Description: {detail}")
                
                opening_hours = place_info.get('opening_hours', '')
                if opening_hours:
                    context_parts.append(f"Opening Hours: {opening_hours}")
                
                contact = place_info.get('contact', {})
                if contact:
                    phones = contact.get('phones', [])
                    if phones:
                        context_parts.append(f"Contact: {', '.join(phones)}")
            
            category = item.get('category') or place_info.get('category_description', '')
            if category:
                context_parts.append(f"Category: {category}")
            
            if location:
                lat = location.get('latitude')
                lon = location.get('longitude')
                if lat and lon:
                    context_parts.append(f"Coordinates: {lat}, {lon}")
        
        context_parts.append("\n=== END TAT DATA ===")
        return "\n".join(context_parts)
    
    def _create_fallback_response(self, language: str, query: str) -> str:
        if language == "th":
            return f"""ขออภัยค่ะ ขณะนี้ระบบ AI ไม่พร้อมให้บริการ 
            
กรุณาลองใหม่อีกครั้งในภายหลัง หรือติดต่อสอบถามข้อมูลเพิ่มเติมได้ที่การท่องเที่ยวแห่งประเทศไทย (TAT)

คำถามของคุณ: {query}"""
        
        return f"""Sorry, the AI system is currently unavailable.

Please try again later or contact the Tourism Authority of Thailand (TAT) for more information.

Your question: {query}"""
    
    def generate_response(
        self, 
        user_query: str, 
        tat_data: List[Dict], 
        data_type: str = "attractions",
        intent: Optional[str] = None
    ) -> Dict[str, Any]:
        language = self._detect_language(user_query)
        
        if not self.client:
            return {
                'response': self._create_fallback_response(language, user_query),
                'data': tat_data,
                'language': language,
                'source': 'fallback'
            }
        
        try:
            tat_context = self._format_tat_data_for_context(tat_data, data_type)
            
            user_message = f"User Query: {user_query}"
            if intent:
                user_message += f"\nDetected Intent: {intent}"
            user_message += f"\n\n{tat_context}"
            
            response = self._create_chat_completion(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_completion_tokens=800,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            ai_response = self._extract_response_text(response)
            
            return {
                'response': ai_response,
                'data': tat_data,
                'language': language,
                'source': self.model_name,
                'model': self.model_name,
                'tokens_used': response.usage.total_tokens if response.usage else None
            }
            
        except Exception as e:
            print(f"[ERROR] GPT generation failed: {e}")
            return {
                'response': self._create_fallback_response(language, user_query),
                'data': tat_data,
                'language': language,
                'source': 'fallback_error',
                'error': str(e)
            }
    
    def generate_greeting(self, language: str = "th") -> str:
        if not self.client:
            if language == "th":
                return "สวัสดีค่ะ! น้องปลาทูพร้อมช่วยวางแผนการเที่ยวสมุทรสงครามให้คุณค่ะ"
            return "Hello! I'm NongPlaToo, ready to help you plan your Samut Songkhram trip!"
        
        try:
            # user prompt removed per user request
            prompt = ""
            
            response = self._create_chat_completion(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_completion_tokens=150
            )
            
            greeting_text = self._extract_response_text(response) or (
                "สวัสดีค่ะ! น้องปลาทูพร้อมช่วยวางแผนการเที่ยวสมุทรสงครามให้คุณค่ะ"
                if language == "th"
                else "Hello! I'm NongPlaToo, ready to help you plan your Samut Songkhram trip!"
            )
            
            return greeting_text
            
        except Exception as e:
            print(f"[ERROR] Greeting generation failed: {e}")
            if language == "th":
                return "สวัสดีค่ะ! น้องปลาทูพร้อมช่วยวางแผนการเที่ยวสมุทรสงครามให้คุณค่ะ"
            return "Hello! I'm NongPlaToo, ready to help you plan your Samut Songkhram trip!"


def test_gpt_service():
    print("Testing GPT Service...")
    
    service = GPTService()
    
    if not service.client:
        print("❌ GPT service not available - check OPENAI_API_KEY")
        return
    
    sample_data = [{
            "place_name": "Amphawa Floating Market",
            "location": {
                "district": "Amphawa",
                "province": "Samut Songkhram",
                "latitude": 13.4138,
                "longitude": 100.0091
            },
            "place_information": {
                "detail": "Famous floating market open Friday-Sunday from 4 PM. Enjoy local food and firefly watching tours.",
                "opening_hours": "Friday-Sunday, 4:00 PM - 9:00 PM"
            },
            "category": "Market"
        }
    ]
    
    # Test query
    result = service.generate_response(
        user_query="Tell me about floating markets in Samut Songkhram",
        tat_data=sample_data,
        data_type="attractions"
    )
    
    print("\n=== GPT Response ===")
    print(f"Language: {result['language']}")
    print(f"Source: {result['source']}")
    print(f"\n{result['response']}")
    
    if result.get('tokens_used'):
        print(f"\nTokens used: {result['tokens_used']}")


if __name__ == "__main__":
    test_gpt_service()


