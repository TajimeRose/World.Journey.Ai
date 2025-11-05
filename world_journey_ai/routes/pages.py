"""Page routes for World Journey AI application."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Union

from flask import Blueprint, Response, current_app, render_template

# Create pages blueprint
pages_bp = Blueprint("pages", __name__)

# Global state for environment loading
_ENV_LOADED = False


def _load_env_file_once(base_dir: Path) -> None:
    """Load environment file once to avoid multiple reads.
    
    Args:
        base_dir: Base directory path to look for .env file
    """
    global _ENV_LOADED
    if _ENV_LOADED:
        return

    _ENV_LOADED = True
    env_path = base_dir / ".env"
    
    if not env_path.exists():
        current_app.logger.debug("No .env file found")
        return

    try:
        content = env_path.read_text(encoding="utf-8")
        _parse_env_content(content)
        current_app.logger.info("Environment variables loaded from .env file")
    except OSError as e:
        current_app.logger.warning(f"Could not read .env file: {e}")
    except Exception as e:
        current_app.logger.error(f"Error parsing .env file: {e}")


def _parse_env_content(content: str) -> None:
    """Parse environment file content and set environment variables.
    
    Args:
        content: Content of the .env file
    """
    for raw_line in content.splitlines():
        line = raw_line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith("#") or "=" not in line:
            continue
        
        # Split on first equals sign
        key, value = line.split("=", 1)
        key = key.strip()
        
        # Skip if key is empty or already exists
        if not key or key in os.environ:
            continue
            
        # Clean up value
        cleaned_value = _clean_env_value(value)
        os.environ[key] = cleaned_value


def _clean_env_value(value: str) -> str:
    """Clean environment variable value.
    
    Args:
        value: Raw value from .env file
        
    Returns:
        Cleaned value
    """
    cleaned = value.strip()
    
    # Remove trailing commas
    if cleaned.endswith(","):
        cleaned = cleaned[:-1]
        
    # Remove surrounding quotes
    cleaned = cleaned.strip().strip('"').strip("'")
    
    return cleaned


def _collect_firebase_config(base_dir: Path) -> Tuple[Dict[str, str], List[str]]:
    """Collect Firebase configuration from environment variables.
    
    Args:
        base_dir: Base directory path
        
    Returns:
        Tuple of (config_dict, missing_keys_list)
    """
    _load_env_file_once(base_dir)

    # Required Firebase configuration keys
    required_keys = {
        "apiKey": "FIREBASE_API_KEY",
        "authDomain": "FIREBASE_AUTH_DOMAIN",
        "projectId": "FIREBASE_PROJECT_ID",
        "appId": "FIREBASE_APP_ID",
    }
    
    # Optional Firebase configuration keys
    optional_keys = {
        "messagingSenderId": "FIREBASE_MESSAGING_SENDER_ID",
        "storageBucket": "FIREBASE_STORAGE_BUCKET",
        "databaseURL": "FIREBASE_DATABASE_URL",
    }

    config = {}
    missing = []

    # Process required keys
    for firebase_key, env_key in required_keys.items():
        value = os.getenv(env_key)
        if value:
            config[firebase_key] = value
        else:
            missing.append(env_key)

    # Process optional keys
    for firebase_key, env_key in optional_keys.items():
        value = os.getenv(env_key)
        if value:
            config[firebase_key] = value

    return config, missing


def _render_page_safely(template_name: str) -> Union[str, Tuple[str, int]]:
    """Safely render a template with error handling.
    
    Args:
        template_name: Name of the template to render
        
    Returns:
        Rendered template or error response
    """
    try:
        return render_template(template_name)
    except Exception as e:
        current_app.logger.error(f"Error rendering {template_name}: {e}")
        return "เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง", 500


@pages_bp.route("/")
def index() -> Union[str, Tuple[str, int]]:
    """Render the main index page."""
    return _render_page_safely("index.html")


@pages_bp.route("/login")
def login() -> Union[str, Tuple[str, int]]:
    """Render the login page."""
    return _render_page_safely("login.html")


@pages_bp.route("/chat")
def chat() -> Union[str, Tuple[str, int]]:
    """Render the chat page."""
    return _render_page_safely("chat.html")


@pages_bp.route("/guide")
def guide() -> Union[str, Tuple[str, int]]:
    """Render the travel guide page."""
    return _render_page_safely("guide.html")


@pages_bp.route("/feedback-test")
def feedback_test() -> Union[str, Tuple[str, int]]:
    """Render the feedback testing page."""
    return _render_page_safely("feedback_test.html")


@pages_bp.route("/firebase_config.js")
def firebase_config() -> Response:
    """Generate Firebase configuration JavaScript file.
    
    Returns:
        JavaScript response with Firebase configuration
    """
    try:
        base_dir = Path(current_app.root_path).parent
        config, missing = _collect_firebase_config(base_dir)

        response = Response(mimetype="application/javascript")
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        if missing:
            missing_list = ", ".join(missing)
            current_app.logger.warning(f"Missing Firebase env vars: {missing_list}")
            response.set_data(
                f"console.error('Missing Firebase environment variables: {missing_list}');\n"
                "window.FIREBASE_CONFIG = null;\n"
                "console.warn('Firebase features will not be available');\n"
            )
            return response

        # Generate JavaScript configuration
        config_js = _generate_firebase_js(config)
        response.set_data(config_js)
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error generating Firebase config: {e}")
        return _create_firebase_error_response()


def _generate_firebase_js(config: Dict[str, str]) -> str:
    """Generate Firebase configuration JavaScript.
    
    Args:
        config: Firebase configuration dictionary
        
    Returns:
        JavaScript configuration string
    """
    config_json = json.dumps(config, ensure_ascii=False, indent=2)
    return (
        f"// Firebase Configuration - Generated at runtime\n"
        f"window.FIREBASE_CONFIG = {config_json};\n"
        f"console.log('Firebase configuration loaded successfully');\n"
    )


def _create_firebase_error_response() -> Response:
    """Create error response for Firebase configuration.
    
    Returns:
        JavaScript error response
    """
    response = Response(mimetype="application/javascript")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.set_data(
        "console.error('Failed to load Firebase configuration');\n"
        "window.FIREBASE_CONFIG = null;\n"
        "console.warn('Firebase features will not be available');\n"
    )
    return response


@pages_bp.errorhandler(404)
def page_not_found(error):
    """Handle 404 errors for pages - redirect to homepage for SPA behavior."""
    return render_template("index.html"), 404


@pages_bp.errorhandler(500)
def page_internal_error(error):
    """Handle 500 errors for pages."""
    current_app.logger.error(f"Page internal server error: {error}")
    return "เกิดข้อผิดพลาดภายในเซิร์ฟเวอร์", 500