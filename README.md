# World Journey AI – Samut Songkhram Tourism

GPT + TAT API travel assistant for Samut Songkhram Province.

## Features

- **GPT-powered chat** (OPENAI_MODEL, default: gpt-5)
- **TAT verified data** (Tourism Authority of Thailand)
- **Intent detection** (attractions, restaurants, accommodation, events, etc.)
- **Bilingual** (Thai/English)
- **Place cards** (structured data + AI narrative)

## Quick Start

1. **Install**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure** `.env`:
   ```env
   TAT_API_KEY=your_tat_key
   OPENAI_API_KEY=your_openai_key
   OPENAI_MODEL=gpt-4o
   ```

3. **Run**:
   ```bash
   python app.py
   ```
   Visit: http://localhost:5000

**Example Interaction**:
```
You: แนะนำที่เที่ยวสมุทรสงครามหน่อย
AI: สมุทรสงครามมีแหล่งท่องเที่ยวที่น่าสนใจมากมายค่ะ...

[Place Card: ตลาดน้ำอัมพวา]
📍 Location: อัมพวา, สมุทรสงคราม
🕐 Hours: 15:00-21:00 (ศุกร์-อาทิตย์)
Description: ตลาดน้ำที่มีชื่อเสียง...

[Place Card: วัดบางกุ้ง]
...
```

## 📁 Project Structure

```
World.Journey.Ai/
├── app.py                    # Flask web server + API endpoints
├── chat.py                   # TravelChatbot orchestration
├── gpt_service.py            # GPT-4 integration service
├── tat_api.py                # TAT API client + intent detection
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
├── static/
│   ├── css/
│   │   ├── chat.css          # Chat UI + place card styles
│   │   ├── index.css
│   │   └── ...
│   ├── js/
│   │   ├── chat.js           # Chat interface + structured data rendering
│   │   ├── firebase-init.js
│   │   └── ...
│   └── img/
└── templates/
    ├── chat.html             # Main chat interface
    ├── index.html
    └── ...
```

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TAT_API_KEY` | Yes | Tourism Authority of Thailand API key |
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT-4 access |
| `FLASK_ENV` | No | `development` or `production` (default: development) |
| `PORT` | No | Server port (default: 5000) |

### Intent Categories

The system detects 6 types of user intents:

1. **Attractions** - Tourist sites, landmarks, temples
2. **Restaurants** - Food venues, cafes, dining
3. **Accommodation** - Hotels, resorts, homestays
4. **Events** - Festivals, activities, cultural events
5. **Opening Hours** - Business hours queries
6. **Transportation** - Travel directions, routes

## 🌐 API Endpoints

### POST `/api/messages`
Send a chat message and receive AI response.

## API

### POST `/api/messages`
```json
{"text": "แนะนำที่พักสมุทรสงคราม"}
```
Returns AI text + structured place cards.

### POST `/api/query`
```json
{"query": "ร้านอาหารอัมพวา", "language": "th"}
```
Returns response + intent + token count.

## Usage

```python
from chat import get_chat_response

result = get_chat_response("แนะนำที่เที่ยวอัมพวา")
print(result['response'])
for place in result['structured_data']:
    print(f"📍 {place['place_name']}")
```

## 🔒 Security & Best Practices

- API keys stored in `.env` file (never commit to git)
- Input sanitization on all user queries
- Rate limiting on API endpoints (recommended in production)
- TAT data as single source of truth (prevents AI hallucination)

## 🛠️ Technologies

- **Backend**: Python 3.8+, Flask
- **AI**: OpenAI GPT-4o
- **Data Source**: TAT Open API
- **Frontend**: Vanilla JavaScript, CSS3
- **Authentication**: Firebase Auth
- **Database**: Firebase Realtime Database

## 📄 License

This project uses:
- TAT (Tourism Authority of Thailand) Open API - governed by TAT terms
- OpenAI API - governed by OpenAI terms of service

## 🤝 Contributing

This is a demonstration project for Samut Songkhram tourism. For improvements:

1. Test changes thoroughly with actual TAT API
2. Ensure responses maintain accuracy with TAT data
3. Update documentation for new features
4. Follow existing code style and patterns

## 📞 Support

For TAT API issues: [TAT API Documentation](https://www.tatapi.tourismthailand.org/)  
For OpenAI issues: [OpenAI Help Center](https://help.openai.com/)

---

Built with ❤️ for Samut Songkhram Province Tourism

**Web API**:
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "user_id": "user123"}'
```

## Customization

To add more knowledge or modify responses, edit the `knowledge_base` in `chat.py`:

```python
self.knowledge_base = {
    "your_topic": {
        "th": "Thai response",
        "en": "English response"
    }
}
```

## Bot Character

**น้องปลาทู** (Nong Pla Tu) - A friendly local guide for Samutsongkhram province who knows all the best spots for tourism, food, and culture.

---

## Files

- `app.py` – Flask server
- `chat.py` – Chatbot logic
- `gpt_service.py` – OpenAI integration
- `tat_api.py` – TAT API client
- `static/` – CSS/JS
- `templates/` – HTML pages

## License

MIT