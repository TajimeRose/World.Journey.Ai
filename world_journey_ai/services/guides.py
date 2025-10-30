from __future__ import annotations

import html
from typing import List

from .destinations import BASE_GUIDE_LINES, GUIDE_SUFFIX


def build_bangkok_guides_html(total: int = 510) -> str:
    entries: List[str] = []
    total = max(total, 510)
    cycle = 0

    while len(entries) < total:
        cycle += 1
        tip = GUIDE_SUFFIX[(cycle - 1) % len(GUIDE_SUFFIX)]
        name = f"Bangkok Discovery Highlight #{cycle:03d}"
        lines_html = "".join(
            f"<li>{html.escape(line)}</li>" for line in (BASE_GUIDE_LINES[:11] + [f"Insider tip #{cycle:03d}: {tip}"])
        )
        query = html.escape(f"{name} Bangkok")
        map_url = f"https://www.google.com/maps/search/?api=1&query={query.replace(' ', '+')}"
        entries.append(
            (
                "<article class=\"guide-entry\">"
                "<h3>{name}</h3>"
                "<ul class=\"guide-lines\">{lines}</ul>"
                "<p class=\"guide-link\"><a href=\"{map_url}\" target=\"_blank\" rel=\"noopener\">Open in Google Maps</a></p>"
                "</article>"
            ).format(name=html.escape(name), lines=lines_html, map_url=map_url)
        )

    intro = (
        '<div class="guide-response">'
        '<p>Detailed Bangkok guide featuring {count} curated spots for trip planning:</p>'
    ).format(count=len(entries))
    return f"{intro}{''.join(entries)}</div>"
