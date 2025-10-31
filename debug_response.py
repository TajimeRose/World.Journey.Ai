#!/usr/bin/env python3
"""Debug the failing test case"""
import sys
import os
import re
from dotenv import load_dotenv
from html import unescape

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from world_journey_ai.services.chatbot import ChatEngine
from world_journey_ai.services.messages import MessageStore
from world_journey_ai.services.destinations import DESTINATIONS

def debug_response():
    message_store = MessageStore()
    chatbot = ChatEngine(message_store, DESTINATIONS)
    
    test_input = "I want to visit Bangkok for 3 days"
    response_data = chatbot.build_reply(test_input)
    
    text_response = str(response_data.get('text', ''))
    html_response = str(response_data.get('html', ''))
    
    # Clean HTML
    clean_html = re.sub('<.*?>', '', html_response)
    clean_html = unescape(clean_html)
    clean_html = ' '.join(clean_html.split())
    
    full_response = f"{text_response} {clean_html}".strip()
    
    print(f"Input: {test_input}")
    print(f"Text Response ({len(text_response)} chars): {text_response}")
    print(f"HTML Response ({len(html_response)} chars): {html_response[:100]}...")
    print(f"Clean HTML ({len(clean_html)} chars): {clean_html[:200]}...")
    print(f"Full Response ({len(full_response)} chars): {full_response[:300]}...")
    
    # Check indicators
    response_lower = full_response.lower()
    thailand_indicators = ['thailand', 'thai', 'bangkok', 'temple', 'food', 'travel', 'visit']
    helpful_indicators = ['recommend', 'suggest', 'best', 'try', 'visit', 'popular', 'good']
    detail_indicators = ['hours', 'baht', 'map', 'location', 'time', 'cost']
    
    print(f"\nThailand context: {any(ind in response_lower for ind in thailand_indicators)}")
    print(f"Helpful content: {any(ind in response_lower for ind in helpful_indicators)}")
    print(f"Details: {any(ind in response_lower for ind in detail_indicators)}")
    print(f"Substantial (>100 chars): {len(full_response) > 100}")

if __name__ == "__main__":
    debug_response()