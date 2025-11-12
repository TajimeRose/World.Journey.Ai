"""Destination data management for World Journey AI.

This module provides destination data for both domestic (Thailand) and 
international travel locations, built from province guides and curated lists.
"""

from __future__ import annotations

from typing import Dict, List

from .province_guides import PROVINCE_GUIDES

# Type aliases
DestinationDict = Dict[str, str]
DestinationList = List[DestinationDict]

# Keywords for Bangkok identification
BANGKOK_KEYWORDS = (
    "กรุงเทพ",
    "กรุงเทพมหานคร",
    "bangkok",
    "bkk", 
    "krung thep",
    "krungthep",
)

# International destinations data
INTERNATIONAL_DESTINATIONS: DestinationList = [
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
]


def _build_domestic_destinations() -> DestinationList:
    """Build domestic destinations from province guides.
    
    Returns:
        List of domestic destination dictionaries
    """
    destinations = []
    
    for province, entries in PROVINCE_GUIDES.items():
        # Take first 5 entries per province to avoid overwhelming the list
        for entry in entries[:5]:
            destinations.append({
                "name": entry["name"],
                "city": province,
                "description": entry["summary"],
                "mapUrl": entry["map_url"],
            })
    
    return destinations


def _combine_all_destinations() -> DestinationList:
    """Combine domestic and international destinations.
    
    Returns:
        Complete list of all available destinations
    """
    domestic = _build_domestic_destinations()
    all_destinations = domestic + INTERNATIONAL_DESTINATIONS
    return all_destinations


# Main destinations list - combining domestic and international
DESTINATIONS: DestinationList = _combine_all_destinations()


def get_destinations_by_type(destination_type: str = "all") -> DestinationList:
    """Get destinations filtered by type.
    
    Args:
        destination_type: "domestic", "international", or "all"
        
    Returns:
        Filtered list of destinations
        
    Raises:
        ValueError: If destination_type is not valid
    """
    if destination_type == "all":
        return DESTINATIONS
    elif destination_type == "domestic":
        return _build_domestic_destinations()
    elif destination_type == "international":
        return INTERNATIONAL_DESTINATIONS
    else:
        raise ValueError(f"Invalid destination type: {destination_type}")


def get_destinations_count() -> Dict[str, int]:
    """Get count of destinations by type.
    
    Returns:
        Dictionary with counts for each destination type
    """
    domestic_count = len(_build_domestic_destinations())
    international_count = len(INTERNATIONAL_DESTINATIONS)
    
    return {
        "domestic": domestic_count,
        "international": international_count,
        "total": domestic_count + international_count,
    }
