"""API routes for World Journey AI application."""

from __future__ import annotations

from typing import Any, Dict, List, Union

from flask import Blueprint, current_app, jsonify, request

# Create API blueprint
api_bp = Blueprint("api", __name__)

# Constants
MAX_MESSAGE_LENGTH = 1000
DEFAULT_ERROR_MESSAGE = "เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง"


def _get_chat_engine():
    """Get chat engine from Flask app extensions with error handling.
    
    Returns:
        ChatEngine: The initialized chat engine
        
    Raises:
        RuntimeError: If chat engine is not configured
    """
    engine = current_app.extensions.get("chat_engine")
    if engine is None:
        current_app.logger.error("Chat engine not found in app extensions")
        raise RuntimeError("Chat engine not configured")
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
        JSON object with 'text' field containing the message
        
    Returns:
        JSON response with user message and AI assistant response
    """
    try:
        engine = _get_chat_engine()
        
        # Parse and validate request
        payload = request.get_json(silent=True) or {}
        text = str(payload.get("text") or "").strip()
        
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

