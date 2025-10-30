from __future__ import annotations

import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING

from flask import Blueprint, current_app, jsonify, request

load_dotenv()

api_bp = Blueprint("api", __name__)


def _chat_engine():
    engine = current_app.extensions.get("chat_engine")
    if engine is None:
        raise RuntimeError("Chat engine not configured")
    return engine


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

