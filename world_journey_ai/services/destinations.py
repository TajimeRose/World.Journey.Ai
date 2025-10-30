from __future__ import annotations

from typing import Dict, List, Tuple

DESTINATIONS: List[Dict[str, str]] = [
    {
        "name": "กรุงเทพมหานคร",
        "city": "ประเทศไทย",
        "description": "มหานครที่รวมวัดสำคัญ คาเฟ่ริมเจ้าพระยา และสตรีทฟู้ดแบบจัดเต็ม",
        "mapUrl": "https://www.google.com/maps/place/Bangkok",
    },
    {
        "name": "สมุทรสงคราม",
        "city": "ประเทศไทย",
        "description": "ล่องเรือชมวิถีชุมชนอัมพวา ตลาดน้ำยามเย็น และบัวลอยไข่เค็มเจ้าเด็ด",
        "mapUrl": "https://www.google.com/maps/place/Samut+Songkhram",
    },
    {
        "name": "โซล",
        "city": "เกาหลีใต้",
        "description": "คาเฟ่ฮิปย่านอิกซอนดง สวนสนุกล็อตเต้เวิลด์ และพระราชวังเคียงบกกุง",
        "mapUrl": "https://www.google.com/maps/place/Seoul",
    },
    {
        "name": "ปารีส",
        "city": "ฝรั่งเศส",
        "description": "ถ่ายรูปกับหอไอเฟล ปิกนิกริมแม่น้ำแซน และพิพิธภัณฑ์ลูฟว์แบบไม่พลาดไฮไลต์",
        "mapUrl": "https://www.google.com/maps/place/Paris",
    },
    {
        "name": "เกียวโต",
        "city": "ญี่ปุ่น",
        "description": "เดินชมฟูชิมิ อินาริ ใส่กิโมโนเที่ยวย่านกิออน และจิบชาเขียวแบบต้นตำรับ",
        "mapUrl": "https://www.google.com/maps/place/Kyoto",
    },
    {
        "name": "ดูไบ",
        "city": "สหรัฐอาหรับเอมิเรตส์",
        "description": "ขึ้นตึกเบิร์จคาลิฟา เดินเล่นซูเปอร์มอลล์ และซาฟารีทะเลทรายสุดมัน",
        "mapUrl": "https://www.google.com/maps/place/Dubai",
    },
    {
        "name": "นิวยอร์ก",
        "city": "สหรัฐอเมริกา",
        "description": "บรอดเวย์ เซ็นทรัลพาร์ก และพิพิธภัณฑ์ระดับโลกแบบหนึ่งวันเต็ม",
        "mapUrl": "https://www.google.com/maps/place/New+York",
    },
    {
        "name": "โรม",
        "city": "อิตาลี",
        "description": "ชมโคลอสเซียมข้างใน เดินเล่นตรอกทราสเตเวเร และชิมเจลาโตสูตรโบราณ",
        "mapUrl": "https://www.google.com/maps/place/Rome",
    },
    {
        "name": "ภูเก็ต",
        "city": "ประเทศไทย",
        "description": "ดำน้ำหมู่เกาะพีพี ชมพระอาทิตย์ตกที่แหลมพรหมเทพ และคาเฟ่วิวทะเล",
        "mapUrl": "https://www.google.com/maps/place/Phuket",
    },
    {
        "name": "พัทยา",
        "city": "ประเทศไทย",
        "description": "ชายหาดจอมเทียน ถนนคนเดินวอล์คกิ้งสตรีท และเกาะล้านแบบวันเดียวเที่ยวได้",
        "mapUrl": "https://www.google.com/maps/place/Pattaya",
    },
    {
        "name": "เชียงใหม่",
        "city": "ประเทศไทย",
        "description": "คาเฟ่ดอยสุเทพ ตลาดวโรรส และขับรถเที่ยวแม่กำปองในวันเดียว",
        "mapUrl": "https://www.google.com/maps/place/Chiang+Mai",
    },
]

BANGKOK_KEYWORDS: Tuple[str, ...] = (
    "กรุงเทพ",
    "กรุงเทพมหานคร",
    "bangkok",
    "bkk",
    "krung thep",
    "krungthep",
)

