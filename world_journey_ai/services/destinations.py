from __future__ import annotations

from typing import Dict, List, Tuple

DESTINATIONS: List[Dict[str, str]] = [
    {
        "name": "กรุงเทพ",
        "city": "กรุงเทพมหานคร",
        "description": "มหานครที่ไม่เคยหลับใหล ผสมผสานวัดวาอาราม ถนนอาหาร และชีวิตริมเจ้าพระยา",
        "mapUrl": "https://www.google.com/maps/place/Bangkok",
    },
    {
        "name": "สมุทรสงคราม",
        "city": "ประเทศไทย",
        "description": "สัมผัสวิถีชุมชนแม่กลอง ตลาดน้ำอัมพวา และล่องเรือชมหิ่งห้อยตอนค่ำ",
        "mapUrl": "https://www.google.com/maps/place/Samut+Songkhram",
    },
    {
        "name": "โซล",
        "city": "เกาหลีใต้",
        "description": "เมืองหลวงสุดคึกคัก ร่วมสมัยกับพระราชวังเก่า คาเฟ่สุดชิค และย่านแฟชั่น",
        "mapUrl": "https://www.google.com/maps/place/Seoul",
    },
    {
        "name": "ปารีส",
        "city": "ฝรั่งเศส",
        "description": "เมืองแห่งแสงสว่าง เต็มไปด้วยพิพิธภัณฑ์ แฟชั่น และร้านขนมปังอบใหม่หอมกรุ่น",
        "mapUrl": "https://www.google.com/maps/place/Paris",
    },
    {
        "name": "เกียวโต",
        "city": "ญี่ปุ่น",
        "description": "เสน่ห์ญี่ปุ่นดั้งเดิม ศาลเจ้าโทริอิ ป่าไผ่อาราชิยามะ และชาเขียวพิถีพิถัน",
        "mapUrl": "https://www.google.com/maps/place/Kyoto",
    },
    {
        "name": "ดูไบ",
        "city": "สหรัฐอาหรับเอมิเรตส์",
        "description": "มหานครทะเลทรายที่ทันสมัย ตึกระฟ้า ทะเลทราย และห้างสรรพสินค้าหรู",
        "mapUrl": "https://www.google.com/maps/place/Dubai",
    },
    {
        "name": "นิวยอร์ก",
        "city": "สหรัฐอเมริกา",
        "description": "มหานครแห่งศิลปะและธุรกิจ Broadway Central Park และพิพิธภัณฑ์ระดับโลก",
        "mapUrl": "https://www.google.com/maps/place/New+York",
    },
    {
        "name": "โรม",
        "city": "อิตาลี",
        "description": "เมืองประวัติศาสตร์อันยิ่งใหญ่ โคลอสเซียม น้ำพุเทรวี และตรอกซอกซอยน่าหลงใหล",
        "mapUrl": "https://www.google.com/maps/place/Rome",
    },
    {
        "name": "ภูเก็ต",
        "city": "ประเทศไทย",
        "description": "เกาะสวรรค์น้ำทะเลใส ชายหาดยาว กิจกรรมดำน้ำ และอาหารทะเลสด",
        "mapUrl": "https://www.google.com/maps/place/Phuket",
    },
    {
        "name": "เชียงใหม่",
        "city": "ประเทศไทย",
        "description": "เมืองศิลปวัฒนธรรมบนดอย วัดโบราณ คาเฟ่ และอากาศสบาย",
        "mapUrl": "https://www.google.com/maps/place/Chiang+Mai",
    },
]

BANGKOK_KEYWORDS: Tuple[str, ...] = (
    "กรุงเทพ",
    "bangkok",
    "bkk",
    "krung thep",
    "krungthep",
)

BASE_GUIDE_LINES = [
    "Crown jewel of Rattanakosin Island",
    "Emerald Buddha revered nationwide",
    "Mirrored mosaics sparkle under sunlight",
    "Ramayana murals wrap around the cloister",
    "Best photo spot at the golden prang",
    "Guided tours available in Thai and English",
    "Dress code requires shoulders and knees covered",
    "Opening hours 08:00-16:00",
    "Easy walk to Wat Pho afterwards",
    "River pier Maharaj close by",
    "Audio guides for immersive storytelling",
    "Beware of fake ticket touts outside",
]

GUIDE_SUFFIX = [
    "Rattanakosin cultural walk",
    "Hidden cafes and river breeze",
    "Contemporary art and galleries",
    "Family-friendly experiences",
    "Local food adventures",
    "Skyline viewpoints and photo ops",
    "Nightlife and after-dark vibes",
    "Transit-friendly connections",
    "One-day express itinerary",
    "Sunrise to sunset highlights",
]
