from __future__ import annotations

from pathlib import Path
from typing import Optional

import os
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING

from flask import Flask
from flask_cors import CORS

from .routes.api import api_bp
from .routes.pages import pages_bp
from .services.chatbot import ChatEngine
from .services.destinations import DESTINATIONS
from .services.messages import MessageStore


def create_app(config_name: Optional[str] = None) -> Flask:
    base_path = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        static_folder=str(base_path / "static"),
        static_url_path="/static",
        template_folder=str(base_path / "templates"),
    )

    # โหลดค่าในไฟล์ .env (ถ้ามี) เพื่อให้ตัวแปรแวดล้อมพร้อมใช้
    load_dotenv(base_path / ".env")

    CORS(app)

    message_store = MessageStore(limit=200)
    chat_engine = ChatEngine(message_store, DESTINATIONS)

    app.extensions["message_store"] = message_store
    app.extensions["chat_engine"] = chat_engine

    # พยายามเชื่อม MongoDB ถ้ามีการตั้งค่าใน environment
    try:
        mongo_uri = os.environ.get("MONGODB_URI")
        mongo_dbname = os.environ.get("MONGODB_DB")
        if mongo_uri and mongo_dbname:
            client = MongoClient(mongo_uri)
            db = client[mongo_dbname]
            events = db["usage_events"]
            # สร้าง index ถ้ายังไม่มี (idempotent)
            events.create_index([("uid", ASCENDING), ("created_at", DESCENDING)])
            app.extensions["mongo_client"] = client
            app.extensions["mongo_events"] = events
    except Exception:
        # ไม่ควรให้การเชื่อม Mongo ทำให้แอปไม่สามารถเริ่มได้ใน dev mode
        pass

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
