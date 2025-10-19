from __future__ import annotations

import os
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from flask import Flask, jsonify, redirect, render_template, request, url_for

try:
    from unidecode import unidecode  # type: ignore
except ImportError:  # pragma: no cover - unidecode optional at runtime
    unidecode = None


app = Flask(__name__)

_MESSAGE_LIMIT = 30
_RECENT_SEARCH_LOCK = threading.Lock()
_recent_search_hits: List[Dict[str, Any]] = []
_messages: "deque[Dict[str, Any]]" = deque(maxlen=_MESSAGE_LIMIT)


_FALLBACK_DESTINATIONS: List[Dict[str, Any]] = [
    {"id": 1, "name": "พทยา", "city": "Pattaya", "country": "Thailand", "short_desc": "เมองชายทะเลขนชอของไทย", "hero_image_url": "", "popularity_score": 92},
    {"id": 2, "name": "Giza Pyramids", "city": "Giza", "country": "Egypt", "short_desc": "มหาพระมดและสฟงซอนยงใหญ", "hero_image_url": "", "popularity_score": 99},
    {"id": 3, "name": "Dubai", "city": "Dubai", "country": "United Arab Emirates", "short_desc": "มหานครลำสมยกลางทะเลทราย", "hero_image_url": "", "popularity_score": 95},
    {"id": 4, "name": "Japan", "city": "Tokyo", "country": "Japan", "short_desc": "แดนอาทตยอทยเมองทนสมยกบวฒนธรรมดงเดม", "hero_image_url": "", "popularity_score": 97},
    {"id": 5, "name": "Kyoto", "city": "Kyoto", "country": "Japan", "short_desc": "วดศาลเจาและสวนญปนแบบดงเดม", "hero_image_url": "", "popularity_score": 90},
    {"id": 6, "name": "Seoul", "city": "Seoul", "country": "South Korea", "short_desc": "เมองใหญทนสมยอาหารและแฟชน", "hero_image_url": "", "popularity_score": 89},
    {"id": 7, "name": "Bangkok", "city": "Bangkok", "country": "Thailand", "short_desc": "เมองหลวงใจกลางเอเชยตะวนออกเฉยงใต", "hero_image_url": "", "popularity_score": 98},
    {"id": 8, "name": "Paris", "city": "Paris", "country": "France", "short_desc": "หอไอเฟลและศลปะระดบโลก", "hero_image_url": "", "popularity_score": 96},
    {"id": 9, "name": "Rome", "city": "Rome", "country": "Italy", "short_desc": "กรงโรมอนเกาแกโคลอสเซยมและพพธภณฑ", "hero_image_url": "", "popularity_score": 91},
    {"id": 10, "name": "New York", "city": "New York", "country": "USA", "short_desc": "มหานครทไมเคยหลบใหล", "hero_image_url": "", "popularity_score": 93},
    {"id": 11, "name": "Sydney", "city": "Sydney", "country": "Australia", "short_desc": "โอเปราเฮาสและชายหาด", "hero_image_url": "", "popularity_score": 88},
    {"id": 12, "name": "Santorini", "city": "Santorini", "country": "Greece", "short_desc": "เกาะขาวฟากลางทะเลอเจยน", "hero_image_url": "", "popularity_score": 87},
]


_SYSTEM_PROMPT = (
    "You are World Journey AI, a bilingual (Thai and English) travel concierge. "
    "Offer concise, upbeat guidance about destinations, logistics, and cultural highlights. "
    "Use accessible language and short paragraphs. Provide bullet points only when they add clarity. "
)

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _set_recent_hits(hits: List[Dict[str, Any]]) -> None:
    with _RECENT_SEARCH_LOCK:
        global _recent_search_hits
        _recent_search_hits = hits[:]


def _get_recent_hits() -> List[Dict[str, Any]]:
    with _RECENT_SEARCH_LOCK:
        return list(_recent_search_hits)


def _strip_diacritics(text: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _normalize(text: str) -> str:
    if not text:
        return ""
    lowered = text.lower()
    if unidecode is not None:
        lowered = unidecode(lowered)
    else:
        lowered = _strip_diacritics(lowered)
    return lowered


def _levenshtein(a: str, b: str, *, max_distance: int = 2) -> int:
    if a == b:
        return 0
    if abs(len(a) - len(b)) > max_distance:
        return max_distance + 1
    if not a:
        return len(b)
    if not b:
        return len(a)
    if len(a) > len(b):
        a, b = b, a

    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        row_min = current[0]
        for j, char_b in enumerate(b, start=1):
            insert_cost = current[j - 1] + 1
            delete_cost = previous[j] + 1
            substitute_cost = previous[j - 1] + (char_a != char_b)
            best = min(insert_cost, delete_cost, substitute_cost)
            current.append(best)
            if best < row_min:
                row_min = best
        if row_min > max_distance:
            return max_distance + 1
        previous = current
    return previous[-1]


def is_meili_configured() -> bool:
    url = os.getenv("MEILI_URL")
    key = os.getenv("MEILI_KEY")
    if not url or not key:
        return False
    try:
        health_url = url.rstrip("/") + "/health"
        response = requests.get(
            health_url,
            headers={"Authorization": f"Bearer {key}"},
            timeout=0.8,
        )
        return response.ok
    except requests.RequestException:
        return False



def is_openai_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))

def search_meili(query: str, limit: int) -> Dict[str, Any]:
    url = os.getenv("MEILI_URL")
    key = os.getenv("MEILI_KEY")
    if not url or not key:
        raise RuntimeError("Meilisearch is not configured")
    search_url = url.rstrip("/") + "/indexes/destinations/search"
    payload = {"q": query, "limit": limit, "sort": ["popularity_score:desc"]}
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    response = requests.post(search_url, json=payload, headers=headers, timeout=1.5)
    response.raise_for_status()
    data = response.json()
    hits = data.get("hits", [])
    return {"source": "meili", "hits": hits}


def fuzzy_filter(items: List[Dict[str, Any]], query: str, limit: int) -> Dict[str, Any]:
    normalized_query = _normalize(query)
    scored: List[Dict[str, Any]] = []

    for item in items:
        combined = " ".join(
            filter(
                None,
                [
                    item.get("name", ""),
                    item.get("city", ""),
                    item.get("country", ""),
                    item.get("short_desc", ""),
                ],
            )
        )
        normalized_combined = _normalize(combined)
        distance = 0
        matches = False

        if not normalized_query:
            matches = True
        elif normalized_query in normalized_combined:
            matches = True
        else:
            name_norm = _normalize(item.get("name", ""))[:40]
            distance = _levenshtein(normalized_query[:40], name_norm, max_distance=2)
            matches = distance <= 2

        if matches:
            scored.append({"item": item, "distance": distance})

    scored.sort(key=lambda entry: (-entry["item"].get("popularity_score", 0), entry["distance"]))

    hits = [{**entry["item"]} for entry in scored[:limit]]
    return {"source": "fallback", "hits": hits}


def _sanitize_card(card: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(card, dict):
        return None
    allowed = {"title", "subtitle", "popularity", "short_desc", "hero_image_url"}
    sanitized = {key: card[key] for key in allowed if key in card and card[key] is not None}
    return sanitized or None


def _build_destination_card(selected: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not selected:
        return None
    return {
        "title": selected.get("name"),
        "subtitle": ", ".join(filter(None, [selected.get("city"), selected.get("country")])),
        "popularity": selected.get("popularity_score"),
        "short_desc": selected.get("short_desc"),
        "hero_image_url": selected.get("hero_image_url"),
    }


def _fallback_assistant_text(selected: Optional[Dict[str, Any]]) -> str:
    if selected:
        return (
            f"It sounds like you're thinking about {selected.get('name')} - great choice! "
            "Want tips for planning?"
        )
    return "Tell me where you'd like to go next and I'll bring ideas."


def _find_destination_match(user_text: str) -> Optional[Dict[str, Any]]:
    normalized_user = _normalize(user_text)
    if not normalized_user:
        return None

    for hit in _get_recent_hits():
        name = hit.get("name", "")
        if not name:
            continue
        normalized_name = _normalize(name)
        if normalized_name and (normalized_name in normalized_user or normalized_user in normalized_name):
            return hit

    for candidate in _FALLBACK_DESTINATIONS:
        normalized_name = _normalize(candidate.get("name", ""))
        if normalized_name and normalized_name in normalized_user:
            return candidate

    return None


def _prepare_model_messages(limit: int = 8) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = [{"role": "system", "content": _SYSTEM_PROMPT}]
    history = list(_messages)[-limit:]
    for entry in history:
        text_value = (entry.get("text") or "").strip()
        if not text_value:
            continue
        role = entry.get("role") or "user"
        if role not in {"assistant", "user", "system"}:
            role = "user"
        openai_role = "assistant" if role == "assistant" else ("system" if role == "system" else "user")
        messages.append({"role": openai_role, "content": text_value})
    return messages


def _request_openai_completion(messages: List[Dict[str, str]]) -> Optional[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    endpoint = base_url.rstrip("/") + "/chat/completions"
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
    }

    temperature = os.getenv("OPENAI_TEMPERATURE")
    try:
        payload["temperature"] = float(temperature) if temperature is not None else 0.4
    except ValueError:
        payload["temperature"] = 0.4

    max_tokens = os.getenv("OPENAI_MAX_TOKENS")
    if max_tokens:
        try:
            payload["max_tokens"] = int(max_tokens)
        except ValueError:
            pass

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    org_id = os.getenv("OPENAI_ORG_ID")
    if org_id:
        headers["OpenAI-Organization"] = org_id

    response = requests.post(endpoint, json=payload, headers=headers, timeout=8)
    response.raise_for_status()
    data = response.json()
    choices = data.get("choices")
    if not choices:
        return None
    message = choices[0].get("message", {})
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    return None


def _append_message(role: str, text: str, *, card: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    entry: Dict[str, Any] = {
        "role": role,
        "text": text,
        "createdAt": _now_iso(),
    }
    sanitized_card = _sanitize_card(card)
    if sanitized_card:
        entry["card"] = sanitized_card
    _messages.append(entry)
    return entry


def _build_assistant_reply(user_text: str) -> Dict[str, Any]:
    selected = _find_destination_match(user_text)
    response_text: Optional[str] = None

    if is_openai_configured():
        try:
            model_messages = _prepare_model_messages()
            if selected:
                summary = selected.get("short_desc") or ""
                location = ", ".join(filter(None, [selected.get("city"), selected.get("country")]))
                hint = "Relevant destination: {}{}. {}".format(
                    selected.get("name", ""),
                    f" ({location})" if location else "",
                    summary,
                ).strip()
                model_messages.append({"role": "system", "content": hint})
            response_text = _request_openai_completion(model_messages)
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            app.logger.warning("OpenAI completion failed: %s", exc)

    if not response_text:
        response_text = _fallback_assistant_text(selected)

    card = _build_destination_card(selected)
    return _append_message("assistant", response_text, card=card)




@app.get("/")
def root() -> Any:
    return redirect(url_for("chat_page"))


@app.get("/favicon.ico")
def favicon() -> Any:
    return ("", 204)

@app.get("/index")
def chat_page() -> Any:
    return render_template("index.html", fallback_destinations=_FALLBACK_DESTINATIONS)


@app.get("/api/search")
def api_search() -> Any:
    query = request.args.get("q", "").strip()
    limit_raw = request.args.get("limit", "20")
    try:
        limit = max(1, min(int(limit_raw), 50))
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400

    if is_meili_configured():
        try:
            result = search_meili(query, limit)
            hits = result.get("hits", [])
            _set_recent_hits(hits)
            return jsonify(result)
        except requests.RequestException as exc:
            fallback = fuzzy_filter(_FALLBACK_DESTINATIONS, query, limit)
            _set_recent_hits(fallback["hits"])
            return jsonify({"source": "fallback", "hits": fallback["hits"], "error": str(exc)})

    fallback = fuzzy_filter(_FALLBACK_DESTINATIONS, query, limit)
    _set_recent_hits(fallback["hits"])
    return jsonify(fallback)


@app.get("/api/messages")
def list_messages() -> Any:
    since_param = request.args.get("since")
    since_dt: Optional[datetime] = None
    if since_param:
        try:
            since_dt = datetime.fromisoformat(since_param)
            if since_dt.tzinfo is None:
                since_dt = since_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return jsonify({"error": "since must be an ISO datetime"}), 400

    filtered = []
    for message in list(_messages):
        if since_dt is None:
            filtered.append(message)
            continue
        try:
            created = datetime.fromisoformat(message["createdAt"])
        except (KeyError, ValueError):
            filtered.append(message)
            continue
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created > since_dt:
            filtered.append(message)

    return jsonify({"messages": filtered})


@app.post("/api/messages")
def create_message() -> Any:
    payload = request.get_json(silent=True) or {}
    role = payload.get("role")
    text = (payload.get("text") or "").strip()
    if role not in {"user", "system"}:
        return jsonify({"error": "role must be 'user' or 'system'"}), 400
    if not text:
        return jsonify({"error": "text is required"}), 400

    card_payload = payload.get("card") if isinstance(payload.get("card"), dict) else None
    stored = _append_message(role, text, card=card_payload)

    if role != "user":
        return jsonify({"message": stored, "assistant": None})

    assistant_entry = _build_assistant_reply(text)
    return jsonify({"message": stored, "assistant": assistant_entry})


if __name__ == "__main__":
    app.run(debug=True)
