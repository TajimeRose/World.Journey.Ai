"""OpenAI service for travel assistant. TAT data + GPT (OPENAI_MODEL, default: gpt-5)."""

import os
import json
from typing import Dict, List, Optional, Any
from openai import OpenAI

class GPTService:
    """Generate travel guidance using OpenAI + TAT data"""
    
    SYSTEM_PROMPT = """You are a friendly and knowledgeable travel assistant specialized in Samut Songkhram Province, Thailand.
Your name is "น้องปลาทู" (NongPlaToo).

CRITICAL RULES:
1. Use ONLY the verified data from the Tourism Authority of Thailand (TAT) provided below
2. NEVER make up or assume details not found in the TAT data
3. If information is missing from TAT data, politely say you don't have that specific information
4. Paraphrase and summarize naturally - don't quote data directly
5. Write in a conversational, friendly tone as if talking to a traveler
6. Match the user's language (Thai or English)
7. Be factually accurate - this is official tourism information

When TAT data is provided:
- Use it as your single source of truth
- Organize information clearly and helpfully
- Add context and travel tips based on the data
- Suggest related places when relevant

When no TAT data matches:
- Apologize politely
- Suggest asking about attractions, restaurants, accommodations, or events in Samut Songkhram
- Never fabricate information

Remember: You're helping real travelers make real plans. Accuracy matters."""

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
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=800,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            ai_response = response.choices[0].message.content
            
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
            prompt = "Generate a warm, friendly greeting as NongPlaToo, introducing yourself as a Samut Songkhram travel guide." + (
                " Respond in Thai." if language == "th" else " Respond in English."
            )
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=150
            )
            
            greeting_text = response.choices[0].message.content or (
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
