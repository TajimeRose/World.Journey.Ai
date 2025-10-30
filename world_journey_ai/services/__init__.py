"""Services package for World Journey AI application.

This package contains all the core business logic services including:
- ChatEngine: AI-powered chat functionality
- MessageStore: Message storage and retrieval
- Destinations: Travel destination data management
- Travel guides: HTML generation for travel recommendations
"""

from .chatbot import ChatEngine
from .destinations import DESTINATIONS, BANGKOK_KEYWORDS, get_destinations_by_type, get_destinations_count
from .guides import build_bangkok_guides_html, get_guide_categories, get_guides_by_category
from .messages import MessageStore

__all__ = [
    "ChatEngine",
    "MessageStore", 
    "DESTINATIONS",
    "BANGKOK_KEYWORDS",
    "build_bangkok_guides_html",
    "get_destinations_by_type",
    "get_destinations_count",
    "get_guide_categories",
    "get_guides_by_category",
]