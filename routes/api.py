from __future__ import annotations

from flask import Blueprint, jsonify, request

api_bp = Blueprint("api", __name__)


@api_bp.get("/search")
def search():
    query = request.args.get("q", "")
    return jsonify({"query": query, "results": []})
