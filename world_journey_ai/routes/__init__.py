"""Routes package for World Journey AI application."""

from .api import api_bp
from .pages import pages_bp

__all__ = ["api_bp", "pages_bp"]