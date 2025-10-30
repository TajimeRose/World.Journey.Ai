from __future__ import annotations

import html
from typing import List

BANGKOK_GUIDE_ENTRIES = [
    {
        "title": "พระบรมมหาราชวัง & วัดพระแก้ว",
        "highlights": [
            "ชมพระแก้วมรกตและสถาปัตยกรรมรัตนโกสินทร์ในหนึ่งชั่วโมง",
            "แนะนำแต่งกายสุภาพ เปิดทุกวัน 08.30-15.30 น.",
            "เดินต่อไปวัดโพธิ์ได้ภายใน 5 นาที",
        ],
        "map_url": "https://goo.gl/maps/UY4mT1qMSY7JNXvM6",
    },
    {
        "title": "ล่องเจ้าพระยาช่วงเย็น + ไชน่าทาวน์",
        "highlights": [
            "ขึ้นเรือด่วนเจ้าพระยาเที่ยวชมวิวพระปรางค์วัดอรุณ",
            "แวะทานสตรีทฟู้ดย่านเยาวราช เช่น หอยทอด ขนมปังไส้ไหล",
            "ปิดท้ายด้วยคาเฟ่ดาดฟ้าริมแม่น้ำ",
        ],
        "map_url": "https://goo.gl/maps/DrDcq3SSUdWADW7E7",
    },
    {
        "title": "ตลาดนัดจตุจักร & Ari Coffee Hop",
        "highlights": [
            "เลือกซื้อของฝาก งานออกแบบ และต้นไม้ในตลาดนัดจตุจักร",
            "นั่ง BTS ต่อไปอารีย์ แวะคาเฟ่สุดชิคและร้านกาแฟสเปเชียลตี",
            "จองร้านอาหารค่ำสไตล์อีสานโมเดิร์นปิดทริป",
        ],
        "map_url": "https://goo.gl/maps/v2GgfwGNPfPSZreK9",
    },
]


def build_bangkok_guides_html() -> str:
    cards: List[str] = []
    for entry in BANGKOK_GUIDE_ENTRIES:
        lines_html = ''.join(f"<li>{html.escape(item)}</li>" for item in entry['highlights'])
        cards.append(
            (
                "<article class=\"guide-entry\">"
                "<h3>{title}</h3>"
                "<ul class=\"guide-lines\">{lines}</ul>"
                "<p class=\"guide-link\"><a href=\"{map_url}\" target=\"_blank\" rel=\"noopener\">เปิดใน Google Maps</a></p>"
                "</article>"
            ).format(title=html.escape(entry['title']), lines=lines_html, map_url=html.escape(entry['map_url']))
        )

    intro = '<div class=\"guide-response\"><p>ทริป 1 วันในกรุงเทพที่น้องปลาทูจัดไว้ให้ ลองสลับหรือเลือกผสมได้เลย:</p>'
    return f"{intro}{''.join(cards)}</div>"

