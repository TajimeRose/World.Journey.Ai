"""Province guides and synonyms loaded from JSON configs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

CONFIG_DIR = Path(__file__).resolve().parent.parent / "configs"
SAMUT_FILE = CONFIG_DIR / "SamutSongkhram.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        print(f"[WARN] Province config not found: {path}")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[WARN] Cannot load province config {path}: {exc}")
        return {}


def _extract_city_name(location_text: Any) -> str:
    if not isinstance(location_text, str):
        return ""
    text = location_text.strip()
    if not text:
        return ""
    for marker in ("อำเภอ", "อ.", "อำเภ"):
        if marker in text:
            after = text.split(marker, 1)[1].strip()
            return after.split()[0].strip(" ,")
    for marker in ("ตำบล", "ต.", "ตำบล"):
        if marker in text:
            after = text.split(marker, 1)[1].strip()
            return after.split()[0].strip(" ,")
    return text


def _build_province_guides(data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    if not data:
        return {}
    province = data.get("province", "สมุทรสงคราม")
    guides: List[Dict[str, Any]] = []
    for place in data.get("places", []) or []:
        name_th = place.get("name_th")
        name_en = place.get("name_en")
        highlights = place.get("highlights", [])
        description = place.get("history") or ", ".join(highlights)
        guides.append(
            {
                "name": name_th or name_en or "Unknown",
                "english_name": name_en,
                "city": _extract_city_name(place.get("location")),
                "description": description,
                "summary": ", ".join(highlights) if highlights else description,
                "map_url": place.get("map_url"),
            }
        )
    return {province: guides} if guides else {}


def _build_synonyms(data: Dict[str, Any]) -> Dict[str, List[str]]:
    province = data.get("province", "สมุทรสงคราม")
    synonyms = [
        province,
        province.replace(" ", ""),
        "Samut Songkhram",
        "SamutSongkhram",
        "Mae Klong",
    ]
    for place in data.get("places", []) or []:
        for value in (
            _extract_city_name(place.get("location")),
            place.get("name_th"),
            place.get("name_en"),
        ):
            if value:
                synonyms.append(value)
    unique_synonyms = list(dict.fromkeys(value for value in synonyms if value))
    return {province: unique_synonyms}


_PROVINCE_DATA = _load_json(SAMUT_FILE)
PROVINCE_GUIDES = _build_province_guides(_PROVINCE_DATA) or {"สมุทรสงคราม": []}
PROVINCE_SYNONYMS = _build_synonyms(_PROVINCE_DATA) or {"สมุทรสงคราม": ["สมุทรสงคราม", "Samut Songkhram"]}
