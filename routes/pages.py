from __future__ import annotations

from flask import Blueprint, render_template

pages_bp = Blueprint("pages", __name__)


@pages_bp.get("/")
def index() -> str:
    return render_template("index.html")


@pages_bp.get("/chat")
def chat() -> str:
    return render_template("chat.html")


@pages_bp.get("/login")
def login() -> str:
    return render_template("login.html")
