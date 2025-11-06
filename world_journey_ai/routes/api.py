"""API routes for World Journey AI application."""

from __future__ import annotations

from typing import Any, Dict, List, Union

import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING

from flask import Blueprint, current_app, jsonify, request

# Import SimpleChatbot for easier development
from ..services.simple_chatbot import SimpleChatbot

# Create API blueprint
load_dotenv()

api_bp = Blueprint("api", __name__)

# Constants
MAX_MESSAGE_LENGTH = 1000
DEFAULT_ERROR_MESSAGE = "เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง"


def _get_chat_engine(ai_mode: str = "chat"):
    """Get chat engine from Flask app extensions with error handling.
    
    Args:
        ai_mode: The AI mode - 'chat' for general conversation or 'guide' for trip planning
    
    Returns:
        BaseAIEngine: The initialized AI engine (ChatEngine or GuideEngine)
        
    Raises:
        RuntimeError: If chat engine is not configured
    """
    if ai_mode == "guide":
        engine = current_app.extensions.get("guide_engine")
        if engine is None:
            # Fallback to chat engine if guide engine not configured
            engine = current_app.extensions.get("chat_engine")
    else:
        engine = current_app.extensions.get("chat_engine")
    
    if engine is None:
        current_app.logger.error("AI engine not found in app extensions")
        raise RuntimeError("AI engine not configured")
    return engine


def _create_error_response(message: str, status_code: int = 500) -> tuple[dict, int]:
    """Create standardized error response.
    
    Args:
        message: Error message to return
        status_code: HTTP status code
        
    Returns:
        Tuple of (json_dict, status_code)
    """
    return {"error": message}, status_code


def _validate_search_query(query: str) -> str | None:
    """Validate search query parameters.
    
    Args:
        query: Search query string
        
    Returns:
        None if valid, error message if invalid
    """
    if not query:
        return "Please provide a search query"
    
    if len(query) > MAX_MESSAGE_LENGTH:
        return "ข้อความค้นหายาวเกินไป กรุณาส่งข้อความที่สั้นกว่านี้"
    
    return None


def _validate_message_text(text: str) -> str | None:
    """Validate message text.
    
    Args:
        text: Message text to validate
        
    Returns:
        None if valid, error message if invalid
    """
    if not text:
        return "กรุณากรอกข้อความก่อนส่ง"
    
    if len(text) > MAX_MESSAGE_LENGTH:
        return "ข้อความยาวเกินไป กรุณาส่งข้อความที่สั้นกว่านี้"
    
    return None


@api_bp.route("/search", methods=["GET"])
def _get_events_collection():
    """Return the `usage_events` collection. Initialize Mongo client once and store
    references on app.extensions. Requires MONGODB_URI and MONGODB_DB in env.
    """
    if current_app.extensions.get("mongo_events"):
        return current_app.extensions["mongo_events"]

    uri = os.environ.get("MONGODB_URI")
    dbname = os.environ.get("MONGODB_DB")
    if not uri or not dbname:
        raise RuntimeError("MONGODB_URI and MONGODB_DB must be set in environment")

    client = MongoClient(uri)
    db = client[dbname]
    events = db["usage_events"]
    # ensure index (idempotent)
    events.create_index([("uid", ASCENDING), ("created_at", DESCENDING)])

    current_app.extensions["mongo_client"] = client
    current_app.extensions["mongo_events"] = events
    return events


@api_bp.get("/search")
def search():
    """Search for destinations based on query parameter.
    
    Query Parameters:
        q (str): Search query string
        
    Returns:
        JSON response with places array or error message
    """
    try:
        query = request.args.get("q", "").strip()
        
        # Validate query
        error_msg = _validate_search_query(query)
        if error_msg:
            return jsonify({"places": [], "message": error_msg})
        
        # Perform search
        engine = _get_chat_engine()
        results = engine.search_destinations(query)
        
        return jsonify({"places": results})
        
    except RuntimeError as e:
        current_app.logger.error(f"Configuration error in search: {e}")
        return jsonify(*_create_error_response("เกิดข้อผิดพลาดในการค้นหา กรุณาลองใหม่อีกครั้ง"))
    except Exception as e:
        current_app.logger.error(f"Unexpected error in search: {e}")
        return jsonify(*_create_error_response("เกิดข้อผิดพลาดในการค้นหา กรุณาลองใหม่อีกครั้ง"))


@api_bp.route("/messages", methods=["GET"])
def list_messages():
    """List messages with optional since parameter.
    
    Query Parameters:
        since (str, optional): Return messages since this timestamp
        
    Returns:
        JSON response with messages array or error message
    """
    try:
        engine = _get_chat_engine()
        since = request.args.get("since")
        
        if since:
            messages = engine.list_since(since)
        else:
            messages = engine.list_messages()
            
        return jsonify({"messages": messages})
        
    except RuntimeError as e:
        current_app.logger.error(f"Configuration error in list_messages: {e}")
        return jsonify(*_create_error_response("เกิดข้อผิดพลาดในการโหลดข้อความ"))
    except Exception as e:
        current_app.logger.error(f"Unexpected error in list_messages: {e}")
        return jsonify(*_create_error_response("เกิดข้อผิดพลาดในการโหลดข้อความ"))


@api_bp.route("/messages", methods=["POST"])
def create_message():
    """Create a new message and generate AI response.
    
    Request Body:
        JSON object with:
        - 'text' field containing the message
        - 'mode' field (optional) specifying AI mode: 'chat' or 'guide'
        
    Returns:
        JSON response with user message and AI assistant response
    """
    try:
        # Parse and validate request
        payload = request.get_json(silent=True) or {}
        text = str(payload.get("text") or "").strip()
        ai_mode = payload.get("mode", "chat")  # default to chat mode
        
        # Validate AI mode
        if ai_mode not in ["chat", "guide"]:
            ai_mode = "chat"
        
        engine = _get_chat_engine(ai_mode)
        
        # Validate message text
        error_msg = _validate_message_text(text)
        if error_msg:
            return jsonify(*_create_error_response(error_msg, 400))

        # Process message
        user_entry = engine.append_user(text)
        assistant_entry = engine.build_reply(text)
        
        return jsonify({
            "message": user_entry, 
            "assistant": assistant_entry
        })
        
    except RuntimeError as e:
        current_app.logger.error(f"Configuration error in create_message: {e}")
        return jsonify(*_create_error_response("เกิดข้อผิดพลาดในการสร้างข้อความ กรุณาลองใหม่อีกครั้ง"))
    except Exception as e:
        current_app.logger.error(f"Unexpected error in create_message: {e}")
        return jsonify(*_create_error_response("เกิดข้อผิดพลาดในการสร้างข้อความ กรุณาลองใหม่อีกครั้ง"))


@api_bp.errorhandler(404)
def api_not_found(error):
    """Handle 404 errors for API endpoints."""
    return jsonify({"error": "ไม่พบ API endpoint ที่ร้องขอ"}), 404


@api_bp.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors for API endpoints."""
    return jsonify({"error": "HTTP method ไม่ได้รับอนุญาต"}), 405


@api_bp.errorhandler(500)
def api_internal_error(error):
    """Handle 500 errors for API endpoints."""
    current_app.logger.error(f"API internal server error: {error}")
    return jsonify({"error": "เกิดข้อผิดพลาดภายในเซิร์ฟเวอร์"}), 500
    user_entry = engine.append_user(text)
    assistant_entry = engine.build_reply(text)
    # พยายามบันทึกประวัติการสนทนาไปยัง MongoDB (ไม่ให้ล้มการตอบกลับถ้า Mongo ผิดพลาด)
    try:
        # uid อาจถูกส่งมาจากไคลเอนต์ใน payload หรือ header
        uid = payload.get("uid") or request.headers.get("X-User-Id") or None
        events = None
        try:
            events = _get_events_collection()
        except RuntimeError:
            events = None

        if events is not None:
            doc = {
                "uid": uid,
                "user_text": text,
                "assistant_text": assistant_entry.get("text") if isinstance(assistant_entry, dict) else str(assistant_entry),
                "created_at": datetime.now(timezone.utc),
            }
            # insert asynchronously-like (blocking here but wrapped in try/except)
            events.insert_one(doc)
    except Exception:
        # ไม่ต้องโยน error กลับไปยัง client ถ้า Mongo เกิดปัญหา
        pass

    return jsonify({"message": user_entry, "assistant": assistant_entry})


@api_bp.get("/mongo-test")
def mongo_test():
    """Simple route to verify MongoDB connection and count documents."""
    try:
        events = _get_events_collection()
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    try:
        count = events.count_documents({})
    except Exception as exc:
        return jsonify({"ok": False, "error": f"mongo error: {exc}"}), 500

    return jsonify({"ok": True, "docs": count})


@api_bp.get("/history")
def get_history():
    """Return recent documents from the usage_events collection.

    Query params:
      - limit: number of documents to return (default 50)
    """
    try:
        events = _get_events_collection()
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    try:
        limit = int(request.args.get("limit", 50))
    except Exception:
        limit = 50

    try:
        cursor = events.find({}, sort=[("created_at", DESCENDING)]).limit(limit)
        docs = []
        for d in cursor:
            # convert non-JSON types
            d = dict(d)
            if "_id" in d:
                d["_id"] = str(d["_id"])
            ca = d.get("created_at")
            if ca is not None:
                try:
                    d["created_at"] = ca.isoformat()
                except Exception:
                    d["created_at"] = str(ca)
            docs.append(d)
    except Exception as exc:
        return jsonify({"ok": False, "error": f"mongo error: {exc}"}), 500

    return jsonify({"ok": True, "count": len(docs), "docs": docs})


# =============================================================================
# SIMPLE CHATBOT ENDPOINT - Easy to modify for non-experts
# =============================================================================

@api_bp.route("/simple-chat", methods=["POST"])
def simple_chat():
    """
    Simple chat endpoint using SimpleChatbot - easier for non-experts to modify.
    
    This endpoint is designed to be simple and accessible for developers who
    are not advanced Python programmers. All the chatbot logic is contained
    in the SimpleChatbot class which has clear, easy-to-edit methods.
    
    Request Body:
        JSON object with:
        - 'message' field containing the user's message
        
    Returns:
        JSON response with bot reply
    """
    try:
        # Get the user's message
        data = request.get_json(silent=True) or {}
        user_message = str(data.get("message", "")).strip()
        
        # Basic validation
        if not user_message:
            return jsonify({
                "error": "กรุณาใส่ข้อความ",
                "success": False
            }), 400
            
        if len(user_message) > 1000:  # Simple limit
            return jsonify({
                "error": "ข้อความยาวเกินไป กรุณาใส่ข้อความสั้นกว่านี้",
                "success": False
            }), 400
        
        # Create simple chatbot with a temporary message store
        # For production, you might want to use a persistent store
        from ..services.messages import MessageStore
        temp_message_store = MessageStore()  # Simple temporary storage
        chatbot = SimpleChatbot(temp_message_store)
        
        # Get bot response (all the logic is in SimpleChatbot class)
        bot_response = chatbot.chat(user_message)
        
        # Return response
        return jsonify({
            "message": user_message,
            "response": bot_response,
            "success": True
        })
        
    except Exception as e:
        # Log the error for debugging
        current_app.logger.error(f"Simple chat error: {e}")
        
        # Return a simple error message
        return jsonify({
            "error": "เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง",
            "success": False
        }), 500

