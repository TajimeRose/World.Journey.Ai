# ============================================================================
# SIMPLE CHATBOT CONFIGURATION - Easy to Edit for Anyone!
# ============================================================================

"""
This file contains all the settings you can easily change for the chatbot.
You don't need to be a programming expert to modify these settings.

IMPORTANT: After making changes, save this file and restart the application.
"""

# ============================================================================
# 1. PLACES AND KEYWORDS (What the chatbot knows about)
# ============================================================================

# Add new places here! Just add them to the list with both Thai and English names
PLACES_TO_TALK_ABOUT = [
    # Format: Add places like this: "place name", "english name"
    "อัมพวา", "amphawa", 
    "วัดบางกุ้ง", "bang kung", 
    "คลองโคน", "khlong khon", 
    "อุทยานพระราม 2", "rama", 
    "ดำเนินสะดวก", "damnoen saduak", 
    "สมุทรสงคราม", "samut songkhram",
    
    # Want to add more places? Just add them like this:
    # "ชื่อสถานที่ไทย", "english name",
]

# ============================================================================
# 2. WELCOME MESSAGE (What bot says when redirecting conversation)
# ============================================================================

WELCOME_MESSAGE = """
สวัสดีค่ะ! น้องปลาทูเป็นไกด์ท้องถิ่นจังหวัดสมุทรสงครามค่ะ ✨

ที่นี่มีสถานที่เด็ดๆ แบบนี้:
🛶 ตลาดน้ำอัมพวา - ตลาดน้ำสุดชิค + ชมหิ่งห้อยยามเย็น
🌳 วัดบางกุ้ง - วัดในรากไทรยักษ์ที่สวยมหัศจรรย์
🌲 คลองโคน - ป่าชายเลนและล่องเรือชมธรรมชาติ
🏛️ อุทยานพระราม 2 - เรียนรู้วัฒนธรรมไทยแท้

อยากรู้เรื่องไหนดีคะ? 😊
"""

# ============================================================================
# 3. CHATBOT PERSONALITY (How the bot behaves)
# ============================================================================

# The bot's name - you can change this!
BOT_NAME = "น้องปลาทู"

# How creative should the bot be? (0.0 = very predictable, 1.0 = very creative)
BOT_CREATIVITY = 0.7

# How many words should the bot use at most?
MAX_RESPONSE_LENGTH = 500

# ============================================================================
# 4. EASY CUSTOMIZATION FUNCTIONS
# ============================================================================

def add_new_place(thai_name: str, english_name: str):
    """
    Use this function to easily add a new place the bot should know about.
    
    Example:
        add_new_place("วัดใหม่", "new temple")
    """
    PLACES_TO_TALK_ABOUT.extend([thai_name, english_name])
    print(f"Added new place: {thai_name} ({english_name})")

def update_welcome_message(new_message: str):
    """
    Use this function to change what the bot says when redirecting conversation.
    
    Example:
        update_welcome_message("Hello! I'm your new guide...")
    """
    global WELCOME_MESSAGE
    WELCOME_MESSAGE = new_message
    print("Welcome message updated!")

def change_bot_name(new_name: str):
    """
    Use this function to change the bot's name.
    
    Example:
        change_bot_name("น้องมะม่วง")
    """
    global BOT_NAME
    BOT_NAME = new_name
    print(f"Bot name changed to: {new_name}")

# ============================================================================
# 5. HOW TO USE THIS FILE
# ============================================================================

"""
TO MODIFY THE CHATBOT:

1. CHANGE PLACES:
   - Edit the PLACES_TO_TALK_ABOUT list above
   - Add new places in both Thai and English
   - Save the file and restart the app

2. CHANGE WELCOME MESSAGE:
   - Edit the WELCOME_MESSAGE text above
   - Use emojis and line breaks to make it friendly
   - Save the file and restart the app

3. CHANGE BOT PERSONALITY:
   - Change BOT_NAME to give your bot a new name
   - Adjust BOT_CREATIVITY (0.0 to 1.0)
   - Change MAX_RESPONSE_LENGTH for longer/shorter responses

4. TEST YOUR CHANGES:
   - Save this file
   - Restart the application
   - Send a message to the bot
   - See your changes in action!

NEED HELP?
- If something breaks, undo your changes
- Make sure all quotes match: "like this"
- Keep the commas in the right places
- Ask a developer if you're stuck!
"""