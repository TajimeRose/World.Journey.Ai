#!/usr/bin/env python3
"""Check what the actual AI responses look like"""
import sys
import os
from dotenv import load_dotenv
import re
from html import unescape

# Load environment variables
load_dotenv()

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from world_journey_ai.services.chatbot import ChatEngine
from world_journey_ai.services.messages import MessageStore
from world_journey_ai.services.destinations import DESTINATIONS

def clean_html(html_text):
    """Extract clean text from HTML"""
    # Remove HTML tags
    clean = re.sub('<.*?>', '', html_text)
    # Unescape HTML entities
    clean = unescape(clean)
    # Remove extra whitespace
    clean = ' '.join(clean.split())
    return clean

def test_responses():
    try:
        # Initialize ChatEngine
        message_store = MessageStore()
        chatbot = ChatEngine(message_store, DESTINATIONS)
        
        test_cases = [
            "I want to visit Bangkok for 3 days. Can you help me plan?",
            "What are the best tourist attractions in Paris?",
            "What's the average budget for 1 week in Europe?",
            "How to get from Bangkok to Chiang Mai?"
        ]
        
        for test_input in test_cases:
            print("=" * 80)
            print(f"🔍 TESTING: {test_input}")
            print("=" * 80)
            
            response_data = chatbot.build_reply(test_input)
            
            text_response = str(response_data.get('text', ''))
            html_response = str(response_data.get('html', ''))
            clean_html_text = clean_html(html_response) if html_response else ''
            
            print(f"📝 TEXT RESPONSE ({len(text_response)} chars):")
            print(f"   {text_response}")
            print()
            
            print(f"🌐 HTML RESPONSE ({len(html_response)} chars):")
            print(f"   {html_response[:200]}...")
            print()
            
            print(f"🧹 CLEAN HTML TEXT ({len(clean_html_text)} chars):")
            print(f"   {clean_html_text[:500]}...")
            print()
            
            # Combined response
            combined = f"{text_response} {clean_html_text}".strip()
            print(f"🔗 COMBINED ({len(combined)} chars):")
            print(f"   {combined[:300]}...")
            print()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_responses()