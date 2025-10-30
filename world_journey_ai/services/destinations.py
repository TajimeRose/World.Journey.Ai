from __future__ import annotations

from typing import Dict, List

from .province_guides import PROVINCE_GUIDES

DESTINATIONS: List[Dict[str, str]] = []
for province, entries in PROVINCE_GUIDES.items():
    for entry in entries[:5]:
        DESTINATIONS.append(
            {
                "name": entry["name"],
                "city": province,
                "description": entry["summary"],
                "mapUrl": entry["map_url"],
            }
        )

BANGKOK_KEYWORDS = (
    "กรุงเทพ",
    "กรุงเทพมหานคร",
    "bangkok",
    "bkk",
    "krung thep",
    "krungthep",
)
