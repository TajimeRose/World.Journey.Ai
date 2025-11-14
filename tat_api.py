"""TAT API integration with intent detection."""

import requests
import os
from typing import Dict, List, Optional, Any
import json
import re

class IntentDetector:
    
    INTENT_PATTERNS = {
        "attractions": [
            r"ที่เที่ยว", r"สถานที่", r"แหล่งท่องเที่ยว", r"จุดท่องเที่ยว",
            r"ไปไหนดี", r"เที่ยวไหน", r"น่าไป", r"ชม", r"เห็น", r"ดู",
            r"วัด", r"ตลาด", r"ป่า", r"คลอง",
            r"visit", r"place", r"attraction", r"sight", r"see",
            r"tour", r"destination", r"temple", r"market", r"where to go"
        ],
        "restaurants": [
            r"ร้านอาหาร", r"กิน", r"อาหาร", r"ของกิน", r"อร่อย",
            r"เมนู", r"ขนม", r"ของหวาน", r"เครื่องดื่ม",
            r"restaurant", r"food", r"eat", r"dining", r"cuisine",
            r"delicious", r"menu", r"dish", r"drink", r"cafe"
        ],
        "accommodation": [
            r"ที่พัก", r"โรงแรม", r"รีสอร์ท", r"พัก", r"นอน",
            r"บ้านพัก", r"ห้องพัก",
            r"hotel", r"accommodation", r"resort", r"stay", r"lodge",
            r"guesthouse", r"hostel", r"room"
        ],
        "events": [
            r"งาน", r"เทศกาล", r"กิจกรรม", r"ประเพณี", r"ฉลอง",
            r"event", r"festival", r"activity", r"celebration", r"tradition"
        ],
        "opening_hours": [
            r"เปิด", r"ปิด", r"เวลา", r"เปิดทำการ", r"เวลาทำการ",
            r"open", r"close", r"hour", r"time", r"when", r"schedule"
        ],
        "transportation": [
            # Thai
            r"ไปยังไง", r"เดินทาง", r"รถ", r"การเดินทาง", r"วิธีไป",
            # English
            r"how to get", r"transportation", r"travel", r"bus", r"car", r"train"
        ]
    }
    
    @staticmethod
    def detect_intent(query: str) -> List[str]:
        """Detect multiple possible intents from user query"""
        query_lower = query.lower()
        detected_intents = []
        
        for intent, patterns in IntentDetector.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    detected_intents.append(intent)
                    break
        
        # Default to attractions if no specific intent detected
        if not detected_intents:
            detected_intents.append("attractions")
        
        return detected_intents


class TATAPIService:
    def __init__(self):
        # TAT API endpoint - Updated to correct URL format
        self.base_url = "https://tatapi.tourismthailand.org/tatapi/v5"
        self.api_key = os.getenv('TAT_API_KEY')
        
        # Updated headers format for TAT API
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Add API key to headers if available
        if self.api_key:
            self.headers['Authorization'] = f'Bearer {self.api_key}'
    
    def search_attractions(self, province: str = "สมุทรสงคราม", 
                          category: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Search for attractions in a specific province"""
        try:
            # Updated endpoint and parameters based on TAT API documentation
            endpoint = f"{self.base_url}/places/search"
            params = {
                'keyword': province,
                'location': province,
                'categorycodes': 'ATTRACTION',
                'provincename': province,
                'numberofresult': limit,
                'pagenumber': 1
            }
            
            if category:
                params['categorycodes'] = category
            
            print(f"[DEBUG] Making request to: {endpoint}")
            print(f"[DEBUG] Parameters: {params}")
            
            response = requests.get(endpoint, headers=self.headers, params=params, timeout=10)
            
            print(f"[DEBUG] Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"[DEBUG] Response data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                # Handle different response formats
                if isinstance(data, dict):
                    results = data.get('result', data.get('data', data.get('places', [])))
                elif isinstance(data, list):
                    results = data
                else:
                    results = []
                
                print(f"[DEBUG] Found {len(results)} results")
                
                # If no results from API, use mock data
                if not results:
                    print("[INFO] No results from TAT API, using mock data")
                    return self.get_mock_data("attractions", province, limit)
                
                # Filter and enhance results
                return self._filter_and_enhance_results(results[:limit])
            else:
                print(f"[ERROR] TAT API Error: {response.status_code} - {response.text[:200]}")
                return self.get_mock_data("attractions", province, limit)
                
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Network error fetching attractions: {e}")
            return self.get_mock_data("attractions", province, limit)
        except Exception as e:
            print(f"[ERROR] Error fetching attractions: {e}")
            return self.get_mock_data("attractions", province, limit)
    
    def _filter_and_enhance_results(self, results: List[Dict]) -> List[Dict]:
        """Filter out incomplete results and enhance data quality"""
        enhanced = []
        
        for item in results:
            # Skip items with insufficient data
            if not item.get('place_name') and not item.get('name'):
                continue
            
            place_info = item.get('place_information', {}) or {}
            if not place_info.get('detail'):
                continue
            
            # Ensure consistent structure
            enhanced_item = {
                'place_name': item.get('place_name') or item.get('name'),
                'location': item.get('location', {}),
                'place_information': place_info,
                'category': item.get('category') or place_info.get('category_description', 'Attraction'),
                'source': item.get('source', 'tat')
            }
            
            enhanced.append(enhanced_item)
        
        return enhanced
    
    def search_by_intent(self, query: str, province: str = "สมุทรสงคราม", 
                        limit: int = 10) -> Dict[str, Any]:
        """
        Search TAT data based on detected user intent
        
        Returns:
            Dict with 'intents', 'primary_intent', 'data', and 'query'
        """
        # Detect user intent
        intents = IntentDetector.detect_intent(query)
        primary_intent = intents[0] if intents else "attractions"
        
        print(f"[INFO] Detected intents: {intents}, Primary: {primary_intent}")
        
        # Fetch data based on primary intent
        data = []
        
        if primary_intent == "attractions":
            data = self.search_attractions(province, limit=limit)
        elif primary_intent == "restaurants":
            data = self.search_restaurants(province, limit=limit)
        elif primary_intent == "accommodation":
            data = self.search_accommodations(province, limit=limit)
        elif primary_intent == "events":
            data = self.search_events(province, limit=limit)
        else:
            # Default to attractions for other intents
            data = self.search_attractions(province, limit=limit)
        
        return {
            'intents': intents,
            'primary_intent': primary_intent,
            'data': data,
            'query': query,
            'province': province
        }

    def get_mock_data(self, data_type: str, province: str = "สมุทรสงคราม", limit: int = 10) -> List[Dict]:
        """Provide mock data when TAT API is not working"""
        if data_type == "attractions":
            return [
                {
                    "place_name": "Amphawa Floating Market",
                    "location": {"district": "Amphawa", "province": "Samut Songkhram"},
                    "place_information": {"detail": "Famous floating market open Friday-Sunday from 4 PM. You can enjoy local food and firefly watching tours in the evening."},
                    "source": "mock"
                },
                {
                    "place_name": "Wat Bang Kung",
                    "location": {"district": "Bang Khonthi", "province": "Samut Songkhram"},
                    "place_information": {"detail": "Historic temple surrounded by massive banyan tree roots. A unique and mystical temple experience."},
                    "source": "mock"
                },
                {
                    "place_name": "Khlong Khone Mangrove Forest",
                    "location": {"district": "Muang", "province": "Samut Songkhram"},
                    "place_information": {"detail": "Beautiful mangrove ecosystem perfect for boat tours and bird watching."},
                    "source": "mock"
                },
                {
                    "place_name": "Khlong Chong",
                    "location": {"district": "Khlong Khone", "province": "Samut Songkhram"},
                    "place_information": {"detail": "Peaceful sub-district of Khlong Khone with pristine mangrove nature, walking trails, and bird watching opportunities."},
                    "source": "mock"
                }
            ]
        elif data_type == "accommodation":
            return [
                {
                    "name": "Amphawa Na Non Hotel & Spa",
                    "location": {"district": "Amphawa", "province": "Samut Songkhram"},
                    "place_information": {"detail": "Boutique hotel near the floating market with traditional Thai design."},
                    "source": "mock"
                },
                {
                    "name": "Baan Amphawa Resort",
                    "location": {"district": "Amphawa", "province": "Samut Songkhram"},
                    "place_information": {"detail": "Riverside resort with comfortable rooms and garden views."},
                    "source": "mock"
                }
            ]
        elif data_type == "restaurant":
            return [
                {
                    "name": "Amphawa Floating Market Food Stalls",
                    "location": {"district": "Amphawa", "province": "Samut Songkhram"},
                    "place_information": {"detail": "Traditional boat noodles, grilled seafood, and local desserts."},
                    "source": "mock"
                },
                {
                    "name": "Local Riverside Restaurants",
                    "location": {"district": "Amphawa", "province": "Samut Songkhram"},
                    "place_information": {"detail": "Fresh seafood restaurants along the Mae Klong River."},
                    "source": "mock"
                }
            ]
        else:
            return []
    
    def get_place_details(self, place_id: str) -> Optional[Dict]:
        """Get detailed information about a specific place"""
        try:
            endpoint = f"{self.base_url}/places/{place_id}"
            response = requests.get(endpoint, headers=self.headers)
            
            if response.status_code == 200:
                return response.json().get('result')
            return None
            
        except Exception as e:
            print(f"Error fetching place details: {e}")
            return None
    
    def search_accommodations(self, province: str = "สมุทรสงคราม", 
                            limit: int = 5) -> List[Dict]:
        """Search for accommodations"""
        try:
            endpoint = f"{self.base_url}/accommodation/search"
            params = {
                'keyword': province,
                'provincename': province,
                'numberofresult': limit,
                'pagenumber': 1
            }
            
            response = requests.get(endpoint, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('result', data.get('data', data.get('accommodations', [])))
                
                if not results:
                    return self.get_mock_data("accommodation", province, limit)
                return self._filter_and_enhance_results(results[:limit])
            else:
                print(f"[ERROR] TAT API Error for accommodations: {response.status_code}")
                return self.get_mock_data("accommodation", province, limit)
            
        except Exception as e:
            print(f"[ERROR] Error fetching accommodations: {e}")
            return self.get_mock_data("accommodation", province, limit)
    
    def search_restaurants(self, province: str = "สมุทรสงคราม", 
                          limit: int = 5) -> List[Dict]:
        """Search for restaurants"""
        try:
            endpoint = f"{self.base_url}/restaurant/search"
            params = {
                'keyword': province,
                'provincename': province,
                'numberofresult': limit,
                'pagenumber': 1
            }
            
            response = requests.get(endpoint, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('result', data.get('data', data.get('restaurants', [])))
                
                if not results:
                    return self.get_mock_data("restaurant", province, limit)
                return self._filter_and_enhance_results(results[:limit])
            else:
                print(f"[ERROR] TAT API Error for restaurants: {response.status_code}")
                return self.get_mock_data("restaurant", province, limit)
            
        except Exception as e:
            print(f"[ERROR] Error fetching restaurants: {e}")
            return self.get_mock_data("restaurant", province, limit)

    def search_events(self, province: str = "สมุทรสงคราม", 
                     limit: int = 5) -> List[Dict]:
        """Search for events and festivals"""
        try:
            endpoint = f"{self.base_url}/events"
            params = {
                'provinceName': province,
                'numberOfResult': limit
            }
            
            response = requests.get(endpoint, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('result', [])
            return []
            
        except Exception as e:
            print(f"Error fetching events: {e}")
            return []

    def get_province_info(self, province: str = "สมุทรสงคราม") -> Optional[Dict]:
        """Get general information about a province"""
        try:
            endpoint = f"{self.base_url}/provinces"
            params = {
                'provinceName': province
            }
            
            response = requests.get(endpoint, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('result', [])
                return results[0] if results else None
            return None
            
        except Exception as e:
            print(f"Error fetching province info: {e}")
            return None

# Test function for development
def test_tat_api():
    """Test function to verify TAT API connection"""
    print("🧪 Testing TAT API Connection...")
    
    tat_service = TATAPIService()
    
    if not tat_service.api_key:
        print("❌ No TAT API key found. Please add TAT_API_KEY to your .env file")
        return False
    
    # Test attractions search
    print("🏛️ Testing attractions search...")
    attractions = tat_service.search_attractions(limit=2)
    if attractions:
        print(f"✅ Found {len(attractions)} attractions")
        for attraction in attractions[:1]:
            print(f"   - {attraction.get('place_name', 'Unknown')}")
    else:
        print("❌ No attractions found")
    
    return len(attractions) > 0

if __name__ == "__main__":
    test_tat_api()