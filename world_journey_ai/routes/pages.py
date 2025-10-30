from __future__ import annotations

import json
import os
from pathlib import Path

from flask import Blueprint, Response, current_app, render_template

pages_bp = Blueprint("pages", __name__)

_ENV_LOADED = False


def _load_env_file_once(base_dir: Path) -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return

    _ENV_LOADED = True
    env_path = base_dir / ".env"
    if not env_path.exists():
        return

    try:
        content = env_path.read_text(encoding="utf-8")
    except OSError:
        return

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        cleaned = value.strip()
        if cleaned.endswith(","):
            cleaned = cleaned[:-1]
        cleaned = cleaned.strip().strip('"').strip("'")
        os.environ[key] = cleaned


def _collect_firebase_config(base_dir: Path) -> tuple[dict[str, str], list[str]]:
    _load_env_file_once(base_dir)

    required = {
        "apiKey": "FIREBASE_API_KEY",
        "authDomain": "FIREBASE_AUTH_DOMAIN",
        "projectId": "FIREBASE_PROJECT_ID",
        "appId": "FIREBASE_APP_ID",
    }
    optional = {
        "messagingSenderId": "FIREBASE_MESSAGING_SENDER_ID",
        "databaseURL": "FIREBASE_DATABASE_URL",
        "storageBucket": "FIREBASE_STORAGE_BUCKET",
    }

    config: dict[str, str] = {}
    missing: list[str] = []

    def _clean(value: str) -> str:
        trimmed = value.strip()
        if trimmed.endswith(","):
            trimmed = trimmed[:-1]
        return trimmed.strip()

    for field, env_key in required.items():
        raw = os.getenv(env_key, "")
        cleaned = _clean(raw)
        if not cleaned:
            missing.append(env_key)
            continue
        config[field] = cleaned

    for field, env_key in optional.items():
        raw = os.getenv(env_key, "")
        cleaned = _clean(raw)
        if cleaned:
            config[field] = cleaned

    return config, missing


@pages_bp.get("/")
def index() -> str:
    return render_template("index.html")


@pages_bp.get("/login")
def login() -> str:
    return render_template("login.html")


@pages_bp.get("/chat")
def chat() -> str:
    return render_template("chat.html")


@pages_bp.get("/firebase_config.js")
def firebase_config() -> Response:
    base_dir = Path(current_app.root_path).parent
    config, missing = _collect_firebase_config(base_dir)

    response = Response(mimetype="application/javascript")
    response.headers["Cache-Control"] = "no-store"

    if missing:
        missing_list = ", ".join(missing)
        response.set_data(
            "console.error('Missing Firebase environment variables: {vars}');\n"
            "window.FIREBASE_CONFIG = null;\n".format(vars=missing_list)
        )
        return response

    response.set_data(
        "window.FIREBASE_CONFIG = {payload};\n".format(
            payload=json.dumps(config, ensure_ascii=False, indent=2)
        )
    )
    return response
