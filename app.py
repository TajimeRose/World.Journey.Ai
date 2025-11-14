"""Flask app for Samut Songkhram tourism. GPT (OPENAI_MODEL, default: gpt-5)."""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from chat import chat_with_bot, get_chat_response
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat')
def chat_page():
    return render_template('chat.html')

@app.route('/guide')
def guide_page():
    return render_template('guide.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/api/query', methods=['POST'])
def api_query():
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        user_message = data['message']
        user_id = data.get('user_id', 'default')
        
        result = get_chat_response(user_message, user_id)
        
        return jsonify({
            'success': True,
            'response': result['response'],
            'structured_data': result.get('structured_data', []),
            'language': result.get('language', 'th'),
            'intent': result.get('intent'),
            'source': result.get('source'),
            'tokens_used': result.get('tokens_used'),
            'timestamp': datetime.datetime.now().isoformat()
        })
    
    except Exception as e:
        print(f"[ERROR] /api/query failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def api_chat():
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        user_message = data['message']
        user_id = data.get('user_id', 'default')
        
        bot_response = chat_with_bot(user_message, user_id)
        
        return jsonify({
            'success': True,
            'response': bot_response,
            'timestamp': datetime.datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/messages', methods=['GET'])
def get_messages():
    try:
        return jsonify({
            'success': True,
            'messages': []
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/messages', methods=['POST'])
def post_message():
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'Text is required'}), 400
        
        user_message = data['text']
        user_id = data.get('user_id', 'default')
        
        result = get_chat_response(user_message, user_id)
        
        current_time = datetime.datetime.now().isoformat()
        
        return jsonify({
            'success': True,
            'assistant': {
                'role': 'assistant',
                'text': result['response'],
                'structured_data': result.get('structured_data', []),
                'language': result.get('language', 'th'),
                'intent': result.get('intent'),
                'source': result.get('source'),
                'createdAt': current_time
            }
        })
    
    except Exception as e:
        print(f"[ERROR] /api/messages POST failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tat-data/<data_type>')
def get_tat_data(data_type):
    try:
        from tat_api import TATAPIService
        tat_service = TATAPIService()
        
        province = request.args.get('province', 'สมุทรสงคราม')
        limit = int(request.args.get('limit', 10))
        
        if data_type == 'attractions':
            data = tat_service.search_attractions(province, limit=limit)
        elif data_type == 'accommodation':
            data = tat_service.search_accommodations(province, limit=limit)
        elif data_type == 'restaurants':
            data = tat_service.search_restaurants(province, limit=limit)
        elif data_type == 'events':
            data = tat_service.search_events(province, limit=limit)
        else:
            return jsonify({'error': 'Invalid data type. Use: attractions, accommodation, restaurants, events'}), 400
        
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data),
            'province': province,
            'type': data_type
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tat-test')
def test_tat_connection():
    try:
        from tat_api import TATAPIService
        tat_service = TATAPIService()
        
        if not tat_service.api_key:
            return jsonify({
                'success': False,
                'message': 'TAT API key not configured. Please add TAT_API_KEY to your .env file',
                'configured': False
            })
        
        test_data = tat_service.search_attractions('สมุทรสงคราม', limit=1)
        
        return jsonify({
            'success': True,
            'message': 'TAT API connection successful',
            'configured': True,
            'test_result': len(test_data) > 0
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'TAT API connection failed: {str(e)}',
            'configured': False
        })

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.datetime.now().isoformat()})

if __name__ == '__main__':
    print("🚀 Samut Songkhram Travel Assistant (GPT model: OPENAI_MODEL or gpt-5)")
    print("📍 http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)

