# 🚀 Easy Chatbot Setup Guide - For Non-Expert Developers

Welcome! This guide will help you modify the World Journey AI chatbot **without needing to be a programming expert**. We've created a simple system that anyone can edit.

## 📁 What Files Do You Need to Know About?

### 1. `simple_config.py` - **THE MOST IMPORTANT FILE**
- This is where you can easily change how the chatbot behaves
- You can add new places, change messages, and modify the bot's personality
- **This is the main file you'll edit most often!**

### 2. `world_journey_ai/services/simple_chatbot.py` - The Simple Chatbot
- Contains the chatbot logic in a simple, easy-to-read format
- You probably won't need to edit this often
- But if you do, the code is written to be clear and understandable

### 3. `world_journey_ai/routes/api.py` - The Connection
- Contains the `/simple-chat` endpoint
- This is where the web connects to the chatbot
- You usually won't need to edit this

## 🛠️ How to Make Changes

### Adding New Tourist Places

1. Open `simple_config.py`
2. Find the `PLACES_TO_TALK_ABOUT` list
3. Add your new place like this:
   ```python
   PLACES_TO_TALK_ABOUT = [
       "อัมพวา", "amphawa", 
       "วัดบางกุ้ง", "bang kung", 
       # Add your new place here:
       "สถานที่ใหม่", "new place",
   ]
   ```
4. Save the file
5. Restart the application

### Changing the Welcome Message

1. Open `simple_config.py`
2. Find `WELCOME_MESSAGE`
3. Edit the text between the triple quotes:
   ```python
   WELCOME_MESSAGE = """
   Your new welcome message here!
   You can use emojis: 😊
   And multiple lines!
   """
   ```
4. Save and restart

### Changing Bot Personality

1. Open `simple_config.py`
2. Change these settings:
   ```python
   BOT_NAME = "น้องปลาทู"          # Bot's name
   BOT_CREATIVITY = 0.7            # 0.0 = boring, 1.0 = very creative
   MAX_RESPONSE_LENGTH = 500       # Maximum response length
   ```

## 🧪 Testing Your Changes

### Method 1: Use the Web Interface
1. Open your browser
2. Go to `http://127.0.0.1:5000`
3. Use the chat interface
4. Test your changes

### Method 2: Use the Simple API
Send a POST request to `http://127.0.0.1:5000/api/simple-chat`:
```json
{
  "message": "สวัสดีครับ"
}
```

## 📋 Common Tasks

### Task 1: Add a New Place "วัดใหม่" (New Temple)

1. Edit `simple_config.py`:
   ```python
   PLACES_TO_TALK_ABOUT = [
       "อัมพวา", "amphawa", 
       "วัดบางกุ้ง", "bang kung", 
       "วัดใหม่", "new temple",  # ← Add this line
       # ... rest of places
   ]
   ```

2. Update the welcome message to mention the new place:
   ```python
   WELCOME_MESSAGE = """
   สวัสดีค่ะ! น้องปลาทูเป็นไกด์ท้องถิ่นจังหวัดสมุทรสงครามค่ะ ✨

   ที่นี่มีสถานที่เด็ดๆ แบบนี้:
   🛶 ตลาดน้ำอัมพวา - ตลาดน้ำสุดชิค + ชมหิ่งห้อยยามเย็น
   🌳 วัดบางกุ้ง - วัดในรากไทรยักษ์ที่สวยมหัศจรรย์
   🏛️ วัดใหม่ - วัดประวัติศาสตร์โบราณ  ← Add this
   
   อยากรู้เรื่องไหนดีคะ? 😊
   """
   ```

### Task 2: Make Bot More Playful

1. Edit `simple_config.py`:
   ```python
   BOT_NAME = "น้องมะม่วง"        # Change name
   BOT_CREATIVITY = 0.9           # Make more creative
   ```

2. Update welcome message to be more playful:
   ```python
   WELCOME_MESSAGE = """
   หวัดดีจ้า! น้องมะม่วงมาแล้วจ้า! 🥭✨
   
   มาเที่ยวสมุทรสงครามกันเถอะ! ที่นี่สนุกมากเลยน่า:
   🛶 อัมพวา - ตลาดน้ำโรแมนติก 💕
   🌳 วัดบางกุ้ง - วัดในรากไผ่ สุดมหัศจรรย์!
   
   อยากไปไหนกันจ้า? 😄
   """
   ```

## 🔧 Technical Details (For When You Need Them)

### File Structure
```
World.Journey.Ai/
├── simple_config.py              ← Edit this for changes!
├── world_journey_ai/
│   ├── services/
│   │   ├── simple_chatbot.py     ← Simple chatbot logic
│   │   └── messages.py           ← Message storage
│   └── routes/
│       └── api.py                ← API endpoints
```

### API Endpoints
- **Original chatbot**: `POST /api/messages`
- **Simple chatbot**: `POST /api/simple-chat` ← Use this for testing

### Environment Setup
1. Make sure you have Python installed
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and add your OpenAI API key
4. Run: `python run_dev.py`

## 🆘 Troubleshooting

### "Import Error" or "Module Not Found"
- Make sure you're running from the project root directory
- Try restarting the application

### Chatbot Not Responding
- Check if your OpenAI API key is set in `.env`
- Look at the terminal output for error messages

### Changes Not Working
- Make sure you saved the file
- Restart the application with `Ctrl+C` then `python run_dev.py`

### Bot Says Wrong Things
- Check `PLACES_TO_TALK_ABOUT` includes your keywords
- Test with simple messages first

## 📞 Getting Help

1. **Check the terminal output** for error messages
2. **Undo your changes** if something breaks
3. **Test one change at a time** to isolate problems
4. **Ask a developer** if you're stuck

## 🎯 Why This System is Better

✅ **Easy to modify** - All settings in one file  
✅ **Clear documentation** - Every setting explained  
✅ **Safe to edit** - Hard to break the system  
✅ **Quick testing** - Simple API endpoint  
✅ **No programming required** - Just edit configuration

---

**Happy coding! 🚀** Even non-experts can make great chatbots with this system!