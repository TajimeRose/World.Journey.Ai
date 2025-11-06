# Simple AI Chatbot for Samutsongkhram Tourism
# Easy to understand and modify for anyone

from typing import Dict, List
import re
import json
import os
import sys

# Add the project root to the path so we can import the config
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

try:
    # Import the easy-to-edit configuration
    from simple_config import (
        PLACES_TO_TALK_ABOUT,
        WELCOME_MESSAGE,
        BOT_NAME,
        BOT_CREATIVITY,
        MAX_RESPONSE_LENGTH
    )
except ImportError:
    # Fallback if config file doesn't exist
    PLACES_TO_TALK_ABOUT = [
        "อัมพวา", "amphawa", "วัดบางกุ้ง", "bang kung", 
        "คลองโคน", "khlong khon", "อุทยาน", "rama", 
        "ดำเนินสะดวก", "damnoen saduak", "สมุทรสงคราม"
    ]
    WELCOME_MESSAGE = """
สวัสดีค่ะ! น้องปลาทูเป็นไกด์ท้องถิ่นจังหวัดสมุทรสงครามค่ะ ✨

ที่นี่มีสถานที่เด็ดๆ แบบนี้:
🛶 ตลาดน้ำอัมพวา - ตลาดน้ำสุดชิค + ชมหิ่งห้อยยามเย็น
🌳 วัดบางกุ้ง - วัดในรากไทรยักษ์ที่สวยมหัศจรรย์
🌲 คลองโคน - ป่าชายเลนและล่องเรือชมธรรมชาติ
🏛️ อุทยานพระราม 2 - เรียนรู้วัฒนธรรมไทยแท้

อยากรู้เรื่องไหนดีคะ? 😊
"""
    BOT_NAME = "น้องปลาทู"
    BOT_CREATIVITY = 0.7
    MAX_RESPONSE_LENGTH = 500

from .messages import MessageStore

class SimpleChatbot:
    def __init__(self, message_store: MessageStore):
        self.message_store = message_store
        self.openai_client = None
        self._setup_openai()
    
    def _setup_openai(self):
        """Setup OpenAI - simple and clear"""
        try:
            import openai
            import os
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.openai_client = openai.OpenAI(api_key=api_key)
        except Exception as e:
            print(f"OpenAI setup failed: {e}")
    
    def chat(self, user_message: str) -> Dict[str, str]:
        """Main chat function - easy to understand"""
        
        # Step 1: Check if it's about Samutsongkhram
        if self._is_about_samutsongkhram(user_message):
            return self._handle_samutsongkhram_question(user_message)
        
        # Step 2: Check if it's a general question we can redirect
        if self._is_general_question(user_message):
            return self._redirect_to_samutsongkhram(user_message)
        
        # Step 3: For other places, politely redirect
        return {"text": WELCOME_MESSAGE, "html": ""}
    
    def _is_about_samutsongkhram(self, message: str) -> bool:
        """Simple check - is the message about Samutsongkhram?"""
        message_lower = message.lower()
        return any(place in message_lower for place in PLACES_TO_TALK_ABOUT)
    
    def _is_general_question(self, message: str) -> bool:
        """Simple check - is it a general travel question?"""
        general_words = [
            "ที่เที่ยว", "travel", "แนะนำ", "recommend", "สวย", "beautiful",
            "อาหาร", "food", "ไปไหนดี", "where to go", "ทำอะไร", "what to do"
        ]
        message_lower = message.lower()
        return any(word in message_lower for word in general_words)
    
    def _handle_samutsongkhram_question(self, message: str) -> Dict[str, str]:
        """Handle questions about Samutsongkhram"""
        if not self.openai_client:
            return {"text": "ขออภัยค่ะ ระบบ AI ยังไม่พร้อมใช้งาน", "html": ""}
        
        # Simple AI prompt - easy to modify
        simple_prompt = f"""
        คุณคือน้องปลาทู ไกด์ท้องถิ่นจังหวัดสมุทรสงคราม
        
        ตอบคำถามนี้แบบเป็นกันเอง สนุกสนาน และให้ข้อมูลที่เป็นประโยชน์:
        "{message}"
        
        เฉพาะเรื่องจังหวัดสมุทรสงครามเท่านั้น:
        - ตลาดน้ำอัมพวา
        - วัดบางกุ้ง  
        - คลองโคน
        - อุทยานพระราม 2
        - บ้านดำเนินสะดวก
        
        ตอบแบบสั้นๆ เข้าใจง่าย ประมาณ 2-3 ประโยค
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": simple_prompt}],
                max_tokens=300,
                temperature=BOT_CREATIVITY
            )
            
            ai_text = response.choices[0].message.content or "ขออภัยค่ะ ไม่สามารถตอบได้"
            ai_text = ai_text.strip()
            return {"text": ai_text, "html": ""}
            
        except Exception as e:
            return {"text": f"ขออภัยค่ะ เกิดข้อผิดพลาด: {str(e)}", "html": ""}
    
    def _redirect_to_samutsongkhram(self, message: str) -> Dict[str, str]:
        """Redirect general questions to Samutsongkhram"""
        if not self.openai_client:
            return {"text": WELCOME_MESSAGE, "html": ""}
        
        # Simple redirect prompt
        redirect_prompt = f"""
        คุณคือ{BOT_NAME} ไกด์ท้องถิ่นจังหวัดสมุทรสงคราม
        
        ผู้ใช้ถาม: "{message}"
        
        นำเรื่องที่เขาถามมาเชื่อมโยงกับสมุทรสงครามแบบสร้างสรรค์ เช่น:
        - ถ้าถามเรื่องอาหาร แนะนำอาหารที่อัมพวา
        - ถ้าถามเรื่องวัด แนะนำวัดบางกุ้ง
        - ถ้าถามเรื่องธรรมชาติ แนะนำคลองโคน
        
        ตอบแบบสั้นๆ น่าสนใจ ทำให้อยากมาสมุทรสงคราม (ไม่เกิน {MAX_RESPONSE_LENGTH} ตัวอักษร)
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": redirect_prompt}],
                max_tokens=200,
                temperature=BOT_CREATIVITY
            )
            
            ai_text = response.choices[0].message.content or "ขออภัยค่ะ ไม่สามารถตอบได้"
            ai_text = ai_text.strip()
            return {"text": ai_text, "html": ""}
            
        except Exception as e:
            return {"text": WELCOME_MESSAGE, "html": ""}

# Easy way to add more places - just edit this list!
def add_new_place(place_name: str):
    """Easy function to add new places"""
    global PLACES_TO_TALK_ABOUT
    if place_name.lower() not in PLACES_TO_TALK_ABOUT:
        PLACES_TO_TALK_ABOUT.append(place_name.lower())
        print(f"Added new place: {place_name}")

# Easy way to change the redirect message
def update_redirect_message(new_message: str):
    """Easy function to update the redirect message"""
    global WELCOME_MESSAGE
    WELCOME_MESSAGE = new_message
    print("Redirect message updated!")