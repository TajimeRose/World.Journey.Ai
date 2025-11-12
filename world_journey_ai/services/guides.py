"""Travel guide HTML generation for World Journey AI.

This module provides functionality to generate HTML content for travel guides,
particularly for Bangkok tourism recommendations with proper HTML escaping.
"""

from __future__ import annotations

import html
from typing import Any, Dict, List

# Type aliases
GuideEntry = Dict[str, Any]
GuideList = List[GuideEntry]

# Bangkok travel guide data
BANGKOK_GUIDE_ENTRIES: GuideList = [
    {
        "title": "พระบรมมหาราชวัง & วัดพระแก้ว",
        "highlights": [
            "แต่งกายสุภาพ เข้าเขตพระบรมมหาราชวัง 08.30 น.",
            "ชมพระแก้วมรกตและเดินชมระเบียงคด",
            "ต่อรถไปวัดโพธิ์นวดแผนไทย 30 นาที",
        ],
        "map_url": "https://goo.gl/maps/UY4mT1qMSY7JNXvM6",
        "category": "วัฒนธรรม",
        "duration": "3-4 ชั่วโมง",
    },
    {
        "title": "วัดโพธิ์ & ท่าเตียน",
        "highlights": [
            "ไหว้พระนอนองค์ใหญ่ ถ่ายภาพใต้หลังคาลายไทย",
            "เที่ยงชิมกุ้งแม่น้ำย่าง ท่าเตียนซีฟู้ด",
            "ซื้อของหวานกลับบ้านจากร้านดังริมเจ้าพระยา",
        ],
        "map_url": "https://goo.gl/maps/B6MWgX8QuLz7c2vR8",
        "category": "วัฒนธรรม",
        "duration": "2-3 ชั่วโมง",
    },
    {
        "title": "คลองสาน & เจริญกรุง",
        "highlights": [
            "ข้ามเรือไปไอคอนสยาม ช้อปของฝากช่างทอง",
            "เดินเล่นซอยเจริญกรุง 44 ชมแกลเลอรี",
            "จิบกาแฟสโลว์บาร์มองแม่น้ำยามเย็น",
        ],
        "map_url": "https://goo.gl/maps/U3mM3v7ukEfrhK1E8",
        "category": "ช้อปปิ้ง",
        "duration": "4-5 ชั่วโมง",
    },
    {
        "title": "สวนลุมพินี & ศาลาแดง",
        "highlights": [
            "วิ่งหรือเดินยืดเส้นใต้ร่มไม้ยามเช้า",
            "ชิมโจ๊กบางลำพูสูตรรถเข็นหน้าสวน",
            "ขึ้น BTS ศาลาแดงต่อรถไปคาเฟ่สีลม",
        ],
        "map_url": "https://goo.gl/maps/nHhW5BPdEzC2",
        "category": "ธรรมชาติ",
        "duration": "2-3 ชั่วโมง",
    },
    {
        "title": "ตลาดกลางคืนสามย่าน",
        "highlights": [
            "เย็นชิมหมูสะเต๊ะและเต้าหู้นมสด",
            "เก็บภาพไฟนีออนสไตล์ย้อนยุค",
            "ต่อรถใต้ดินกลับที่พักสะดวก",
        ],
        "map_url": "https://goo.gl/maps/HrY7eyDku8zJRZyD9",
        "category": "อาหาร",
        "duration": "2-3 ชั่วโมง",
    },
]


def build_bangkok_guides_html() -> str:
    """Build HTML for Bangkok travel guides with proper escaping.
    
    Returns:
        Complete HTML string for Bangkok travel guides
    """
    try:
        cards = [_build_guide_card(entry) for entry in BANGKOK_GUIDE_ENTRIES]
        return _wrap_in_guide_container(cards)
    except Exception as e:
        # Return safe fallback HTML if generation fails
        return _build_fallback_guide_html(str(e))


def _build_guide_card(entry: GuideEntry) -> str:
    """Build HTML card for a single guide entry.
    
    Args:
        entry: Guide entry dictionary
        
    Returns:
        HTML string for the guide card
    """
    title = _safe_get_string(entry, "title")
    highlights = entry.get("highlights", [])
    map_url = _safe_get_string(entry, "map_url")
    category = _safe_get_string(entry, "category")
    duration = _safe_get_string(entry, "duration")
    
    # Build highlights list
    highlights_html = _build_highlights_html(highlights)
    
    # Build metadata
    metadata_html = ""
    if category or duration:
        metadata_html = f'<div class="guide-meta">'
        if category:
            metadata_html += f'<span class="guide-category">{html.escape(category)}</span>'
        if duration:
            metadata_html += f'<span class="guide-duration">{html.escape(duration)}</span>'
        metadata_html += '</div>'
    
    # Build complete card
    return (
        '<article class="guide-entry">'
        f'<h3 class="guide-title">{html.escape(title)}</h3>'
        f'{metadata_html}'
        f'<ul class="guide-highlights">{highlights_html}</ul>'
        f'{_build_map_link_html(map_url)}'
        '</article>'
    )


def _build_highlights_html(highlights: List[str]) -> str:
    """Build HTML for highlights list.
    
    Args:
        highlights: List of highlight strings
        
    Returns:
        HTML string for highlights
    """
    if not isinstance(highlights, list):
        return ""
    
    return "".join(
        f'<li class="guide-highlight">{html.escape(str(item))}</li>'
        for item in highlights
        if item  # Skip empty items
    )


def _build_map_link_html(map_url: str) -> str:
    """Build HTML for map link.
    
    Args:
        map_url: Google Maps URL
        
    Returns:
        HTML string for map link
    """
    if not map_url:
        return ""
    
    return (
        '<div class="guide-link">'
        f'<a href="{html.escape(map_url)}" target="_blank" rel="noopener noreferrer" '
        'class="guide-map-link">🗺️ เปิดใน Google Maps</a>'
        '</div>'
    )


def _wrap_in_guide_container(cards: List[str]) -> str:
    """Wrap guide cards in container HTML.
    
    Args:
        cards: List of HTML card strings
        
    Returns:
        Complete wrapped HTML
    """
    intro_text = (
        "🌟 <strong>ทริป 1 วันในกรุงเทพ</strong> ที่น้องปลาทูจัดไว้ให้ "
        "ลองสลับหรือเลือกผสมได้เลยค่า!"
    )
    
    return (
        '<div class="guide-response">'
        f'<div class="guide-intro">{intro_text}</div>'
        f'<div class="guide-cards">{"".join(cards)}</div>'
        '</div>'
    )


def _build_fallback_guide_html(error_msg: str = "") -> str:
    """Build fallback HTML when guide generation fails.
    
    Args:
        error_msg: Error message for logging
        
    Returns:
        Safe fallback HTML
    """
    return (
        '<div class="guide-response guide-error">'
        '<p>🏛️ ขออีกหน่อยนะคะ น้องปลาทูกำลังเตรียมข้อมูลเที่ยวกรุงเทพให้!</p>'
        '</div>'
    )


def _safe_get_string(data: Dict[str, Any], key: str, default: str = "") -> str:
    """Safely get string value from dictionary.
    
    Args:
        data: Dictionary to get value from
        key: Key to look up
        default: Default value if key is missing
        
    Returns:
        String value or default
    """
    value = data.get(key, default)
    return str(value) if value is not None else default


def get_guide_categories() -> List[str]:
    """Get list of available guide categories.
    
    Returns:
        List of unique categories
    """
    categories = set()
    for entry in BANGKOK_GUIDE_ENTRIES:
        category = entry.get("category")
        if category:
            categories.add(str(category))
    return sorted(list(categories))


def get_guides_by_category(category: str) -> GuideList:
    """Get guides filtered by category.
    
    Args:
        category: Category to filter by
        
    Returns:
        List of guides in the specified category
    """
    return [
        entry for entry in BANGKOK_GUIDE_ENTRIES
        if entry.get("category") == category
    ]
