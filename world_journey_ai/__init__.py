from __future__ import annotations

from pathlib import Path
from typing import Optional

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

    CORS(app)

    message_store = MessageStore(limit=200)
    chat_engine = ChatEngine(message_store, DESTINATIONS)

    app.extensions["message_store"] = message_store
    app.extensions["chat_engine"] = chat_engine

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
