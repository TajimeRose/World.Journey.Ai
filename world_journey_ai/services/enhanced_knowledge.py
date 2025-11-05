"""Enhanced knowledge system for World Journey AI.

This module provides comprehensive place knowledge including:
- Detailed geographical information
- Cultural and historical context
- Practical travel information
- Real-time data integration capabilities
"""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import hashlib

# Type aliases
PlaceInfo = Dict[str, Any]
KnowledgeData = Dict[str, Any]


@dataclass
class PlaceKnowledge:
    """Comprehensive place knowledge structure"""
    name: str
    name_local: str
    country: str
    admin_levels: Dict[str, str]  # province, district, sub_district
    coordinates: Optional[Tuple[float, float]]
    place_type: str  # city, district, landmark, attraction, etc.
    
    # Detailed information
    description: str
    highlights: List[str]
    cultural_info: Dict[str, Any]
    practical_info: Dict[str, Any]
    
    # Travel specifics
    best_time_to_visit: Dict[str, str]
    transportation: Dict[str, List[str]]
    accommodation_types: List[str]
    food_specialties: List[str]
    
    # Meta information
    confidence_level: str  # High, Medium, Low
    last_updated: str
    sources: List[str]


class EnhancedKnowledgeSystem:
    """Enhanced knowledge system with comprehensive place information"""
    
    def __init__(self):
        self._knowledge_cache: Dict[str, PlaceKnowledge] = {}
        self._init_enhanced_thailand_knowledge()
        self._init_international_knowledge()
    
    def _init_enhanced_thailand_knowledge(self):
        """Initialize comprehensive Thailand knowledge base"""
        
        # Enhanced Bangkok knowledge
        bangkok_knowledge = PlaceKnowledge(
            name="Bangkok",
            name_local="กรุงเทพมหานคร",
            country="Thailand",
            admin_levels={
                "province": "กรุงเทพมหานคร",
                "district": "50 districts",
                "sub_district": "169 khwaeng"
            },
            coordinates=(13.7563, 100.5018),
            place_type="capital_city",
            description="Thailand's vibrant capital and largest city, known for its ornate shrines, bustling street life, and cultural landmarks.",
            highlights=[
                "Grand Palace and Wat Phra Kaew (Temple of the Emerald Buddha)",
                "Wat Pho (Reclining Buddha Temple)",
                "Chatuchak Weekend Market",
                "Floating Markets (Damnoen Saduak, Amphawa)",
                "Khao San Road nightlife",
                "Chao Phraya River and canal tours",
                "Modern shopping centers (Siam Paragon, Central World)",
                "Street food culture",
                "Lumpini Park",
                "Bangkok National Museum"
            ],
            cultural_info={
                "religion": "Buddhism (primary), with Hindu and Chinese influences",
                "festivals": ["Songkran (April)", "Loy Krathong (November)", "Chinese New Year"],
                "etiquette": "Remove shoes before entering temples, dress modestly, show respect to Buddha images",
                "language": "Thai (primary), English widely understood in tourist areas",
                "currency": "Thai Baht (THB)"
            },
            practical_info={
                "visa": "Visa on arrival for many countries, 30-day exemption for tourists",
                "vaccination": "No required vaccinations, recommended: Hepatitis A/B, Typhoid",
                "safety": "Generally safe for tourists, watch for pickpockets in crowded areas",
                "climate": "Tropical monsoon climate",
                "emergency_numbers": "Tourist Police: 1155, Emergency: 191"
            },
            best_time_to_visit={
                "cool_season": "November-February (best weather, 18-32°C)",
                "hot_season": "March-May (very hot, 25-40°C)",
                "rainy_season": "June-October (humid, frequent rain, 24-33°C)"
            },
            transportation={
                "public_transport": [
                    "BTS Skytrain (covers central Bangkok)",
                    "MRT Subway (Blue, Purple lines)",
                    "Airport Rail Link (to Suvarnabhumi)",
                    "Buses (local and air-conditioned)",
                    "Chao Phraya Express Boats",
                    "Canal boats (khlong)"
                ],
                "taxis": ["Meter taxis", "Grab app", "Motorcycle taxis"],
                "airports": ["Suvarnabhumi (BKK)", "Don Mueang (DMK)"]
            },
            accommodation_types=[
                "Luxury hotels (Mandarin Oriental, The Oriental)",
                "Boutique hotels",
                "Hostels (Khao San Road area)", 
                "Guesthouses",
                "Serviced apartments",
                "Floating hotels"
            ],
            food_specialties=[
                "Pad Thai",
                "Tom Yum Goong (spicy shrimp soup)",
                "Green Curry (Gaeng Keow Wan)",
                "Mango Sticky Rice (Khao Niao Mamuang)",
                "Som Tam (papaya salad)",
                "Street food (Chinatown, Yaowarat Road)",
                "Boat noodles",
                "Thai desserts (Thong Yip, Foi Thong)"
            ],
            confidence_level="High",
            last_updated=datetime.now().isoformat(),
            sources=["TAT", "Local expertise", "Google Maps", "Official tourism data"]
        )
        
        self._knowledge_cache["bangkok"] = bangkok_knowledge
        self._knowledge_cache["กรุงเทพ"] = bangkok_knowledge
        self._knowledge_cache["krung thep"] = bangkok_knowledge
        
        # Enhanced Chiang Mai knowledge
        chiang_mai_knowledge = PlaceKnowledge(
            name="Chiang Mai",
            name_local="เชียงใหม่",
            country="Thailand",
            admin_levels={
                "province": "เชียงใหม่",
                "district": "Mueang Chiang Mai",
                "sub_district": "Various tambon"
            },
            coordinates=(18.7877, 98.9931),
            place_type="city",
            description="Northern Thailand's cultural capital, known for ancient temples, mountain landscapes, and traditional crafts.",
            highlights=[
                "Wat Phra That Doi Suthep",
                "Old City and ancient walls",
                "Night Bazaar and Sunday Walking Street",
                "Elephant Nature Park",
                "Doi Inthanon National Park",
                "Traditional handicraft villages",
                "Cooking classes",
                "Monk chat programs",
                "Mountain tribe villages",
                "Coffee plantations"
            ],
            cultural_info={
                "heritage": "Lanna Kingdom heritage (1296-1558)",
                "crafts": "Handicrafts, wood carving, silk weaving, silverware",
                "festivals": ["Yi Peng Lantern Festival", "Songkran", "Flower Festival"],
                "dialect": "Northern Thai (Kam Muang) alongside standard Thai"
            },
            practical_info={
                "altitude": "310 meters above sea level",
                "pollution": "Burning season (Feb-April) causes air quality issues",
                "connectivity": "Good WiFi, coworking spaces available"
            },
            best_time_to_visit={
                "cool_season": "November-February (perfect weather, 15-28°C)",
                "hot_season": "March-May (hot and smoky, 20-36°C)",
                "rainy_season": "June-October (cooler, regular rain, 22-30°C)"
            },
            transportation={
                "airport": ["Chiang Mai International Airport"],
                "local": ["Songthaews (red trucks)", "Tuk-tuks", "Motorbike taxis", "Grab"],
                "rental": ["Motorbikes", "Cars", "Bicycles"]
            },
            accommodation_types=[
                "Boutique resorts",
                "Traditional Lanna-style hotels",
                "Mountain resorts",
                "Hostels in old city",
                "Eco-lodges"
            ],
            food_specialties=[
                "Khao Soi (curry noodles)",
                "Sai Ua (northern sausage)",
                "Nam Prik Noom (green chili dip)",
                "Gaeng Hang Lay (Burmese-style curry)",
                "Khantoke dinner (traditional Northern feast)"
            ],
            confidence_level="High",
            last_updated=datetime.now().isoformat(),
            sources=["TAT Northern Office", "Local cultural centers", "Tourism guides"]
        )
        
        self._knowledge_cache["chiang mai"] = chiang_mai_knowledge
        self._knowledge_cache["เชียงใหม่"] = chiang_mai_knowledge
        
        # Add more Thai destinations
        self._add_phuket_knowledge()
        self._add_krabi_knowledge()
        self._add_pattaya_knowledge()
    
    def _add_phuket_knowledge(self):
        """Add comprehensive Phuket knowledge"""
        phuket_knowledge = PlaceKnowledge(
            name="Phuket",
            name_local="ภูเก็ต",
            country="Thailand",
            admin_levels={
                "province": "ภูเก็ต",
                "district": "Mueang Phuket",
                "sub_district": "17 tambon"
            },
            coordinates=(7.8804, 98.3923),
            place_type="island_province",
            description="Thailand's largest island and premier beach destination, known for stunning beaches, nightlife, and water activities.",
            highlights=[
                "Patong Beach (main beach and nightlife)",
                "Phi Phi Islands day trips",
                "Big Buddha statue",
                "Old Phuket Town (Sino-Portuguese architecture)",
                "Wat Chalong temple",
                "Phang Nga Bay (James Bond Island)",
                "Kata and Karon beaches",
                "Bangla Road nightlife",
                "Phuket FantaSea cultural show",
                "Tiger Kingdom"
            ],
            cultural_info={
                "heritage": "Tin mining history, Chinese-Portuguese influence",
                "festivals": ["Phuket Vegetarian Festival", "Songkran"],
                "architecture": "Sino-Portuguese shophouses in Old Town"
            },
            practical_info={
                "airport": "Phuket International Airport (HKT)",
                "medical": "Bangkok Hospital Phuket, international standard healthcare",
                "safety": "Beach safety: strong currents during monsoon"
            },
            best_time_to_visit={
                "high_season": "November-March (dry, sunny, 24-32°C)",
                "low_season": "May-October (monsoon, cheaper prices, 25-31°C)",
                "shoulder": "April (hot but dry, 26-34°C)"
            },
            transportation={
                "airport": ["Phuket International Airport"],
                "local": ["Tuk-tuks", "Songthaews", "Motorbike taxis", "Car rentals"],
                "inter_island": ["Speedboats", "Ferries", "Long-tail boats"]
            },
            accommodation_types=[
                "Luxury beach resorts",
                "Boutique hotels",
                "Budget hostels",
                "Villa rentals",
                "Beachfront bungalows"
            ],
            food_specialties=[
                "Fresh seafood",
                "Phuket-style noodles",
                "Massaman curry",
                "Tropical fruits",
                "Beach BBQ"
            ],
            confidence_level="High",
            last_updated=datetime.now().isoformat(),
            sources=["Phuket Tourism Authority", "Hotel associations", "Travel guides"]
        )
        
        self._knowledge_cache["phuket"] = phuket_knowledge
        self._knowledge_cache["ภูเก็ต"] = phuket_knowledge
    
    def _add_krabi_knowledge(self):
        """Add comprehensive Krabi knowledge"""
        krabi_knowledge = PlaceKnowledge(
            name="Krabi",
            name_local="กระบี่",
            country="Thailand",
            admin_levels={
                "province": "กระบี่",
                "district": "Mueang Krabi",
                "sub_district": "Multiple tambon"
            },
            coordinates=(8.0863, 98.9063),
            place_type="province",
            description="Southern Thailand province famous for limestone cliffs, pristine beaches, and rock climbing.",
            highlights=[
                "Railay Beach (rock climbing mecca)",
                "Ao Nang Beach",
                "Tiger Cave Temple (Wat Tham Sua)",
                "Four Islands Tour",
                "Hot Springs and Emerald Pool",
                "Phi Phi Islands",
                "Koh Lanta",
                "Mangrove kayaking",
                "Rock climbing",
                "Island hopping"
            ],
            cultural_info={
                "heritage": "Traditional fishing communities",
                "festivals": ["Krabi Boek Fa Andaman Festival"],
                "activities": "Rock climbing, traditional boat making"
            },
            practical_info={
                "airport": "Krabi Airport (KBV)",
                "access": "Accessible by bus, plane, or boat from Phuket"
            },
            best_time_to_visit={
                "dry_season": "November-April (ideal weather, 23-32°C)",
                "rainy_season": "May-October (monsoon, 24-30°C)"
            },
            transportation={
                "airport": ["Krabi Airport"],
                "local": ["Songthaews", "Long-tail boats", "Motorbike rentals"],
                "water": ["Boats to islands", "Kayaks"]
            },
            accommodation_types=[
                "Beach resorts",
                "Rock climbing lodges",
                "Eco-resorts",
                "Backpacker hostels",
                "Floating bungalows"
            ],
            food_specialties=[
                "Fresh seafood",
                "Gaeng Som (sour curry)",
                "Crab curry",
                "Coconut-based dishes",
                "Tropical fruit"
            ],
            confidence_level="High",
            last_updated=datetime.now().isoformat(),
            sources=["Krabi Tourism", "Adventure tour operators", "Local guides"]
        )
        
        self._knowledge_cache["krabi"] = krabi_knowledge
        self._knowledge_cache["กระบี่"] = krabi_knowledge
    
    def _add_pattaya_knowledge(self):
        """Add comprehensive Pattaya knowledge"""
        pattaya_knowledge = PlaceKnowledge(
            name="Pattaya",
            name_local="พัทยา",
            country="Thailand",
            admin_levels={
                "province": "ชลบุรี",
                "district": "Bang Lamung",
                "sub_district": "Nong Prue"
            },
            coordinates=(12.9236, 100.8825),
            place_type="beach_city",
            description="Popular beach resort city known for nightlife, water sports, and family attractions.",
            highlights=[
                "Walking Street (nightlife)",
                "Sanctuary of Truth temple",
                "Coral Island (Koh Larn)",
                "Nong Nooch Tropical Garden",
                "Art in Paradise 3D museum",
                "Pattaya Beach",
                "Jomtien Beach",
                "Cabaret shows",
                "Water sports",
                "Golf courses"
            ],
            cultural_info={
                "character": "Resort town atmosphere, international community",
                "entertainment": "Cabaret shows, live music, international cuisine"
            },
            practical_info={
                "distance": "150km from Bangkok (1.5-2 hours by car)",
                "medical": "Good hospitals, international clinics available"
            },
            best_time_to_visit={
                "cool_season": "November-February (best weather, 20-30°C)",
                "hot_season": "March-May (very hot, 25-35°C)",
                "rainy_season": "June-October (occasional heavy rain, 25-32°C)"
            },
            transportation={
                "from_bangkok": ["Bus", "Minivan", "Taxi", "Train"],
                "local": ["Songthaews", "Motorbike taxis", "Baht buses"],
                "airport": ["U-Tapao Airport (nearby)"]
            },
            accommodation_types=[
                "Beach resorts",
                "High-rise hotels",
                "Boutique hotels",
                "Serviced apartments",
                "Budget guesthouses"
            ],
            food_specialties=[
                "Seafood restaurants",
                "International cuisine",
                "Street food",
                "Beach BBQ",
                "Thai fusion dishes"
            ],
            confidence_level="High",
            last_updated=datetime.now().isoformat(),
            sources=["Pattaya Tourism", "Hotel industry", "Local businesses"]
        )
        
        self._knowledge_cache["pattaya"] = pattaya_knowledge
        self._knowledge_cache["พัทยา"] = pattaya_knowledge
    
    def _init_international_knowledge(self):
        """Initialize international destination knowledge"""
        
        # Enhanced Tokyo knowledge
        tokyo_knowledge = PlaceKnowledge(
            name="Tokyo",
            name_local="東京",
            country="Japan",
            admin_levels={
                "prefecture": "Tokyo Metropolis",
                "special_wards": "23 special wards",
                "cities": "26 cities, 5 towns, 8 villages"
            },
            coordinates=(35.6762, 139.6503),
            place_type="capital_metropolis",
            description="Japan's bustling capital, blending ultra-modern technology with traditional culture.",
            highlights=[
                "Senso-ji Temple (Asakusa)",
                "Tokyo Skytree and Tokyo Tower",
                "Shibuya Crossing",
                "Meiji Shrine",
                "Tsukiji Outer Market",
                "Harajuku fashion district",
                "Ginza luxury shopping",
                "Akihabara electronics",
                "Imperial Palace East Gardens",
                "Teamlab Borderless digital art"
            ],
            cultural_info={
                "etiquette": "Bowing, removing shoes, quiet on trains, no eating while walking",
                "festivals": ["Cherry Blossom (Sakura)", "Golden Week", "Obon"],
                "traditions": "Tea ceremony, traditional crafts, modern pop culture"
            },
            practical_info={
                "language": "Japanese (English signage in tourist areas)",
                "currency": "Japanese Yen (JPY)",
                "tipping": "Not expected, can be considered rude",
                "wifi": "Free WiFi widely available"
            },
            best_time_to_visit={
                "spring": "March-May (cherry blossoms, 10-20°C)",
                "summer": "June-August (hot and humid, 20-30°C)",
                "autumn": "September-November (mild, fall colors, 10-20°C)",
                "winter": "December-February (cold but clear, 0-10°C)"
            },
            transportation={
                "airports": ["Narita (NRT)", "Haneda (HND)"],
                "trains": ["JR Yamanote Line", "Tokyo Metro", "Toei Subway"],
                "passes": ["JR Pass", "Tokyo Metro Pass"]
            },
            accommodation_types=[
                "Luxury hotels",
                "Capsule hotels", 
                "Ryokan (traditional inns)",
                "Business hotels",
                "Hostels"
            ],
            food_specialties=[
                "Sushi and sashimi",
                "Ramen",
                "Tempura",
                "Wagyu beef",
                "Mochi",
                "Street food (yakitori, takoyaki)"
            ],
            confidence_level="High",
            last_updated=datetime.now().isoformat(),
            sources=["JNTO", "Tokyo Metropolitan Government", "Travel guides"]
        )
        
        self._knowledge_cache["tokyo"] = tokyo_knowledge
        self._knowledge_cache["東京"] = tokyo_knowledge
        
        # Add more international destinations
        self._add_paris_knowledge()
        self._add_seoul_knowledge()
    
    def _add_paris_knowledge(self):
        """Add comprehensive Paris knowledge"""
        paris_knowledge = PlaceKnowledge(
            name="Paris",
            name_local="Paris",
            country="France",
            admin_levels={
                "region": "Île-de-France",
                "department": "Paris",
                "arrondissements": "20 arrondissements"
            },
            coordinates=(48.8566, 2.3522),
            place_type="capital_city",
            description="The City of Light, renowned for art, fashion, gastronomy, and culture.",
            highlights=[
                "Eiffel Tower",
                "Louvre Museum",
                "Notre-Dame Cathedral",
                "Arc de Triomphe",
                "Champs-Élysées",
                "Montmartre and Sacré-Cœur",
                "Seine River cruises",
                "Versailles Palace (day trip)",
                "Latin Quarter",
                "Marais district"
            ],
            cultural_info={
                "art": "World's largest art collection at Louvre",
                "cuisine": "French culinary capital",
                "fashion": "Global fashion center",
                "etiquette": "Greet with 'Bonjour/Bonsoir', dress well"
            },
            practical_info={
                "language": "French (some English in tourist areas)",
                "currency": "Euro (EUR)",
                "visa": "Schengen visa for most non-EU visitors"
            },
            best_time_to_visit={
                "spring": "April-June (mild weather, blooming parks, 8-20°C)",
                "summer": "July-August (warm, peak season, 15-25°C)",
                "autumn": "September-November (comfortable, fewer crowds, 8-18°C)",
                "winter": "December-March (cold, magical atmosphere, 3-8°C)"
            },
            transportation={
                "airports": ["Charles de Gaulle (CDG)", "Orly (ORY)"],
                "metro": ["Metro lines 1-14", "RER suburban trains"],
                "other": ["Buses", "Vélib' bike sharing", "Batobus (river bus)"]
            },
            accommodation_types=[
                "Luxury hotels",
                "Boutique hotels",
                "Apartments",
                "Hostels",
                "B&Bs"
            ],
            food_specialties=[
                "Croissants and pastries",
                "French cheese",
                "Wine",
                "Escargot",
                "Coq au vin",
                "Macarons",
                "French onion soup"
            ],
            confidence_level="High",
            last_updated=datetime.now().isoformat(),
            sources=["Paris Tourism Office", "Official city guides", "Cultural institutions"]
        )
        
        self._knowledge_cache["paris"] = paris_knowledge
        self._knowledge_cache["ปารีส"] = paris_knowledge
    
    def _add_seoul_knowledge(self):
        """Add comprehensive Seoul knowledge"""
        seoul_knowledge = PlaceKnowledge(
            name="Seoul",
            name_local="서울",
            country="South Korea",
            admin_levels={
                "metropolitan": "Seoul Special City",
                "districts": "25 districts (gu)",
                "neighborhoods": "467 neighborhoods (dong)"
            },
            coordinates=(37.5665, 126.9780),
            place_type="capital_city",
            description="South Korea's dynamic capital, blending cutting-edge technology with traditional culture.",
            highlights=[
                "Gyeongbokgung Palace",
                "Bukchon Hanok Village",
                "Myeongdong shopping district",
                "Hongdae nightlife area",
                "N Seoul Tower",
                "Dongdaemun Design Plaza",
                "Gangnam district",
                "Han River parks",
                "Insadong traditional culture street",
                "Lotte World Tower"
            ],
            cultural_info={
                "heritage": "Joseon Dynasty palaces and traditions",
                "modern_culture": "K-pop, K-drama, technology hub",
                "etiquette": "Bow when greeting, use both hands when giving/receiving",
                "festivals": ["Cherry blossom festivals", "Seoul Lantern Festival"]
            },
            practical_info={
                "language": "Korean (English in major areas)",
                "currency": "Korean Won (KRW)",
                "internet": "Excellent WiFi coverage, very fast speeds"
            },
            best_time_to_visit={
                "spring": "April-June (cherry blossoms, mild weather, 10-22°C)",
                "summer": "July-August (hot and humid, monsoon season, 22-30°C)",
                "autumn": "September-November (comfortable, fall colors, 8-20°C)",
                "winter": "December-March (cold but dry, 5 to -10°C)"
            },
            transportation={
                "airport": ["Incheon International (ICN)", "Gimpo (GMP)"],
                "subway": ["9 subway lines", "Excellent coverage"],
                "other": ["Buses", "Taxis", "KakaoTaxi app"]
            },
            accommodation_types=[
                "Luxury hotels",
                "Hanok guesthouses",
                "Jjimjilbangs (spa hotels)",
                "Hostels",
                "Serviced residences"
            ],
            food_specialties=[
                "Korean BBQ",
                "Kimchi",
                "Bibimbap",
                "Korean fried chicken",
                "Hotteok (street pancakes)",
                "Korean street food",
                "Soju (traditional alcohol)"
            ],
            confidence_level="High",
            last_updated=datetime.now().isoformat(),
            sources=["Korea Tourism Organization", "Seoul Tourism", "Cultural centers"]
        )
        
        self._knowledge_cache["seoul"] = seoul_knowledge
        self._knowledge_cache["โซล"] = seoul_knowledge
        self._knowledge_cache["서울"] = seoul_knowledge
    
    def get_place_knowledge(self, place_name: str) -> Optional[PlaceKnowledge]:
        """Get comprehensive knowledge about a place"""
        normalized_name = place_name.lower().strip()
        return self._knowledge_cache.get(normalized_name)
    
    def search_places(self, query: str) -> List[PlaceKnowledge]:
        """Search for places matching the query"""
        query_lower = query.lower().strip()
        results = []
        
        for key, knowledge in self._knowledge_cache.items():
            # Check name matches
            if query_lower in key or query_lower in knowledge.name.lower():
                results.append(knowledge)
                continue
                
            # Check description matches
            if query_lower in knowledge.description.lower():
                results.append(knowledge)
                continue
                
            # Check highlights
            for highlight in knowledge.highlights:
                if query_lower in highlight.lower():
                    results.append(knowledge)
                    break
        
        return results
    
    def get_enhanced_prompt_context(self, place_name: str) -> str:
        """Get enhanced context for AI prompts"""
        knowledge = self.get_place_knowledge(place_name)
        if not knowledge:
            return ""
        
        context = f"""
ENHANCED PLACE KNOWLEDGE FOR: {knowledge.name} ({knowledge.name_local})

ADMINISTRATIVE INFO:
{json.dumps(knowledge.admin_levels, indent=2, ensure_ascii=False)}

TOP ATTRACTIONS & HIGHLIGHTS:
{chr(10).join(f"• {highlight}" for highlight in knowledge.highlights[:10])}

CULTURAL CONTEXT:
{json.dumps(knowledge.cultural_info, indent=2, ensure_ascii=False)}

PRACTICAL TRAVEL INFO:
{json.dumps(knowledge.practical_info, indent=2, ensure_ascii=False)}

BEST TIME TO VISIT:
{json.dumps(knowledge.best_time_to_visit, indent=2, ensure_ascii=False)}

TRANSPORTATION OPTIONS:
{json.dumps(knowledge.transportation, indent=2, ensure_ascii=False)}

ACCOMMODATION TYPES:
{chr(10).join(f"• {acc_type}" for acc_type in knowledge.accommodation_types)}

FOOD SPECIALTIES:
{chr(10).join(f"• {food}" for food in knowledge.food_specialties)}

CONFIDENCE LEVEL: {knowledge.confidence_level}
LAST UPDATED: {knowledge.last_updated}
"""
        return context
    
    def get_all_place_names(self) -> List[str]:
        """Get all available place names in the knowledge base"""
        places = set()
        for knowledge in self._knowledge_cache.values():
            places.add(knowledge.name)
            places.add(knowledge.name_local)
        return list(places)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        unique_places = len(set(k.name for k in self._knowledge_cache.values()))
        countries = len(set(k.country for k in self._knowledge_cache.values()))
        
        confidence_counts = {}
        for knowledge in self._knowledge_cache.values():
            conf = knowledge.confidence_level
            confidence_counts[conf] = confidence_counts.get(conf, 0) + 1
        
        return {
            "total_entries": len(self._knowledge_cache),
            "unique_places": unique_places,
            "countries_covered": countries,
            "confidence_distribution": confidence_counts,
            "last_update": max(k.last_updated for k in self._knowledge_cache.values())
        }


# Global knowledge system instance
enhanced_knowledge = EnhancedKnowledgeSystem()