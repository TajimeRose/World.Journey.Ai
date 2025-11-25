import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from chat import TravelChatbot

def test_matching():
    print("Initializing Chatbot...")
    bot = TravelChatbot()
    
    queries = ["วัด", "อาหาร", "ที่พัก", "temple", "food", "hotel", "ตลาด"]
    
    for q in queries:
        print(f"\n--- Query: '{q}' ---")
        results = bot._match_travel_data(q, limit=5)
        if not results:
            print("No matches found.")
        for i, res in enumerate(results):
            name = res.get('name') or res.get('place_name')
            desc = res.get('description', '')[:50] + "..."
            print(f"{i+1}. {name} ({desc})")

if __name__ == "__main__":
    test_matching()
