import sys
import os
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.getcwd())

from chat import TravelChatbot
from gpt_service import GPTService

def reproduce_error():
    print("Initializing Chatbot...")
    bot = TravelChatbot()
    
    # Mock GPTService to ensure it's used
    bot.gpt_service = GPTService()
    
    # Force pure GPT response which calls generate_response with system_override
    print("Attempting to trigger pure GPT response...")
    try:
        # We can call _pure_gpt_response directly to bypass DB checks
        result = bot._pure_gpt_response("Hello", "en")
        print("Success!")
    except TypeError as e:
        print(f"Caught expected error: {e}")
    except Exception as e:
        print(f"Caught unexpected error: {e}")

if __name__ == "__main__":
    reproduce_error()
