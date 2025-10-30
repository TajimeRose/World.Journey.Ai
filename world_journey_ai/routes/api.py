from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

api_bp = Blueprint("api", __name__)


def _chat_engine():
    engine = current_app.extensions.get("chat_engine")
    if engine is None:
        raise RuntimeError("Chat engine not configured")
    return engine


@api_bp.get("/search")
def search():
    query = request.args.get("q", "")
    engine = _chat_engine()
    results = engine.search_destinations(query)
    return jsonify({"places": results})


@api_bp.get("/messages")
def list_messages():
    engine = _chat_engine()
    since = request.args.get("since")
    if since:
        messages = engine.list_since(since)
    else:
        messages = engine.list_messages()
    return jsonify({"messages": messages})


@api_bp.post("/messages")
def create_message():
    engine = _chat_engine()
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text") or "").strip()
    if not text:
        return jsonify({"error": "กรุณากรอกข้อความก่อนส่ง"}), 400

    user_entry = engine.append_user(text)
    assistant_entry = engine.build_reply(text)
    return jsonify({"message": user_entry, "assistant": assistant_entry})

