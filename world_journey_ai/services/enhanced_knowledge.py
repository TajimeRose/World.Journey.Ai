"""Minimal enhanced_knowledge stub providing contextual place data."""
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class PlaceKnowledge:
    name: str
    summary: str = ""
    details: Optional[Dict[str, Any]] = None


class EnhancedKnowledge:
    def __init__(self) -> None:
        self._cache: Dict[str, PlaceKnowledge] = {}

    def get_enhanced_prompt_context(self, place_name: str) -> str:
        pk = self._cache.get(place_name)
        if pk:
            return f"{pk.name}: {pk.summary}"
        # Basic fallback context when no cached info exists
        return f"ข้อมูลเกี่ยวกับ {place_name}"

    def add_place(
        self,
        name: str,
        summary: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._cache[name] = PlaceKnowledge(
            name=name,
            summary=summary,
            details=details or {},
        )


enhanced_knowledge = EnhancedKnowledge()
