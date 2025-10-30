from __future__ import annotations

import html
from typing import List

BANGKOK_GUIDE_ENTRIES = [
    {
        "title": "พระบรมมหาราชวัง & วัดพระแก้ว",
        "highlights": [
            "แต่งกายสุภาพ เข้าเขตพระบรมมหาราชวัง 08.30 น.",
            "ชมพระแก้วมรกตและเดินชมระเบียงคด",
            "ต่อรถไปวัดโพธิ์นวดแผนไทย 30 นาที",
        ],
        "map_url": "https://goo.gl/maps/UY4mT1qMSY7JNXvM6",
    },
    {
        "title": "วัดโพธิ์ & ท่าเตียน",
        "highlights": [
            "ไหว้พระนอนองค์ใหญ่ ถ่ายภาพใต้หลังคาลายไทย",
            "เที่ยงชิมกุ้งแม่น้ำย่าง ท่าเตียนซีฟู้ด",
            "ซื้อของหวานกลับบ้านจากร้านดังริมเจ้าพระยา",
        ],
        "map_url": "https://goo.gl/maps/B6MWgX8QuLz7c2vR8",
    },
    {
        "title": "คลองสาน & เจริญกรุง",
        "highlights": [
            "ข้ามเรือไปไอคอนสยาม ช้อปของฝากช่างทอง",
            "เดินเล่นซอยเจริญกรุง 44 ชมแกลเลอรี",
            "จิบกาแฟสโลว์บาร์มองแม่น้ำยามเย็น",
        ],
        "map_url": "https://goo.gl/maps/U3mM3v7ukEfrhK1E8",
    },
    {
        "title": "สวนลุมพินี & ศาลาแดง",
        "highlights": [
            "วิ่งหรือเดินยืดเส้นใต้ร่มไม้ยามเช้า",
            "ชิมโจ๊กบางลำพูสูตรรถเข็นหน้าสวน",
            "ขึ้น BTS ศาลาแดงต่อรถไปคาเฟ่สีลม",
        ],
        "map_url": "https://goo.gl/maps/nHhW5BPdEzC2",
    },
    {
        "title": "ตลาดกลางคืนสามย่าน",
        "highlights": [
            "เย็นชิมหมูสะเต๊ะและเต้าหู้นมสด",
            "เก็บภาพไฟนีออนสไตล์ย้อนยุค",
            "ต่อรถใต้ดินกลับที่พักสะดวก",
        ],
        "map_url": "https://goo.gl/maps/HrY7eyDku8zJRZyD9",
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
