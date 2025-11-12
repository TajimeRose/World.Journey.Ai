"""World Journey AI - Travel Assistant Application.

A Flask-based travel assistant that uses AI to help users plan their journeys
and discover travel destinations in Thailand and around the world.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING
from flask import Flask
from flask_cors import CORS

from .routes.api import api_bp
from .routes.pages import pages_bp
from .services.chatbot import ChatEngine, GuideEngine
from .services.destinations import DESTINATIONS
from .services.messages import MessageStore


def create_app(config_name: Optional[str] = None) -> Flask:
    """Create and configure the Flask application.
    
    Args:
        config_name: Optional configuration name for different environments
        
    Returns:
        Configured Flask application instance
        
    Raises:
        RuntimeError: If services fail to initialize
    """
    # Determine base path for static/template folders
    base_path = Path(__file__).resolve().parent.parent
    
    # Create Flask app with proper folder configuration
    app = Flask(
        __name__,
        static_folder=str(base_path / "static"),
        static_url_path="/static",
        template_folder=str(base_path / "templates"),
    )

    # Configure Flask app
    _configure_app(app, config_name)
    
    # Initialize services
    _initialize_services(app)
    
    # Register blueprints
    _register_blueprints(app)
    
    # Load environment variables from .env file (if exists)
    load_dotenv(base_path / ".env")

    app.logger.info("World Journey AI application created successfully")
    return app


def _configure_app(app: Flask, config_name: Optional[str] = None) -> None:
    """Configure Flask application settings."""
    # Set secret key from environment or use default for development
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key-change-in-production")
    
    # Configure CORS for development
    allowed_origins = [
        "http://localhost:*",
        "http://127.0.0.1:*",
        "https://localhost:*",
        "https://127.0.0.1:*",
    ]
    CORS(app, origins=allowed_origins)
    
    # Try to connect MongoDB if configured in environment
    try:
        mongo_uri = os.environ.get("MONGODB_URI")
        mongo_dbname = os.environ.get("MONGODB_DB")
        if mongo_uri and mongo_dbname:
            client = MongoClient(mongo_uri)
            db = client[mongo_dbname]
            events = db["usage_events"]
            # Create index if not exists (idempotent)
            events.create_index([("uid", ASCENDING), ("created_at", DESCENDING)])
            app.extensions["mongo_client"] = client
            app.extensions["mongo_events"] = events
    except Exception:
        # Don't let Mongo connection failure prevent app from starting in dev mode
        pass

    # Configure logging
    log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    
    if not app.debug:
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        app.logger.setLevel(log_level)
    
def _initialize_services(app: Flask) -> None:
    """Initialize application services with proper error handling."""
    try:
        # Initialize services
        from .services.messages import MessageStore
        
        # Initialize services
        message_store = MessageStore(limit=200)
        chat_engine = ChatEngine(message_store, DESTINATIONS)
        guide_engine = GuideEngine(message_store, DESTINATIONS)
        
        # Store in app extensions for later access
        app.extensions["message_store"] = message_store
        app.extensions["chat_engine"] = chat_engine
        app.extensions["guide_engine"] = guide_engine
        
        app.logger.info("Services initialized successfully")
        
    except ImportError as e:
        app.logger.error(f"Failed to import services: {e}")
        raise RuntimeError(f"Service import failed: {e}") from e
    except Exception as e:
        app.logger.error(f"Failed to initialize services: {e}")
        raise RuntimeError(f"Service initialization failed: {e}") from e


def _register_blueprints(app: Flask) -> None:
    """Register Flask blueprints."""
    try:
        app.register_blueprint(pages_bp)
        app.register_blueprint(api_bp, url_prefix="/api")
        app.logger.info("Blueprints registered successfully")
    except Exception as e:
        app.logger.error(f"Failed to register blueprints: {e}")
        raise RuntimeError(f"Blueprint registration failed: {e}") from e
