"""
Semantic search for tourism queries using sentence embeddings
Intelligent understanding without hardcoded keywords
"""

import os
import sys
from typing import List, Dict, Tuple, Optional

def safe_import():
    """Safely import dependencies with detailed error reporting"""
    try:
        print("[INFO] Loading semantic libraries...")
        
        import numpy as np
        print("  ✓ NumPy loaded")
        
        from sentence_transformers import SentenceTransformer
        print("  ✓ SentenceTransformers loaded")
        
        from sklearn.metrics.pairwise import cosine_similarity
        print("  ✓ Scikit-learn loaded")
        
        return True, (np, SentenceTransformer, cosine_similarity)
        
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        return False, None
    except Exception as e:
        print(f"[ERROR] Import failed: {e}")
        return False, None

# Try to load dependencies
LIBRARIES_AVAILABLE, imports = safe_import()

# Extract imports safely at module level
if LIBRARIES_AVAILABLE and imports is not None:
    np, SentenceTransformer, cosine_similarity = imports
else:
    np = None
    SentenceTransformer = None  
    cosine_similarity = None

class SemanticMatcher:
    def __init__(self):
        """Initialize the semantic matcher with multilingual model"""
        if not LIBRARIES_AVAILABLE or SentenceTransformer is None:
            raise ImportError("Semantic search libraries not available")
            
        # Use module-level imports
        self.np = np
        self.cosine_similarity = cosine_similarity
            
        try:
            # Use a smaller, faster multilingual model that works with Thai and English
            print("[INFO] Loading semantic model...")
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            print("[OK] Semantic model loaded successfully")
            
            # Define knowledge areas with diverse example phrases
            self.knowledge_areas = {
                "amphawa": [
                    # Thai variations
                    "ตลาดน้ำอัมพวา", "อัมพวา", "ตลาดน้ำที่มีชื่อเสียง", "ตลาดน้ำดัง",
                    "ตลาดอัมพวา", "อัมพวาเป็นยังไง", "ไปอัมพวา", "เที่ยวอัมพวา",
                    "ตลาดน้ำในสมุทรสงคราม", "ตลาดน้ำเก่าแก่", "ชมหิ่งห้อย",
                    # English variations
                    "Amphawa floating market", "Amphawa market", "famous floating market",
                    "tell me about Amphawa", "visit Amphawa", "Amphawa tourism",
                    "floating market in Samut Songkhram", "firefly watching", "weekend market"
                ],
                "bang_kung": [
                    # Thai variations
                    "วัดบางกุ้ง", "บางกุ้ง", "วัดในรากไผ่", "วัดที่มีรากไผ่", 
                    "วัดรากไผ่", "วัดพิเศษ", "วัดที่แปลก", "วัดที่น่าตื่นตาตื่นใจ",
                    "วัดเก่าแก่", "วัดที่มีประวัติ", "พระในรากไผ่",
                    # English variations
                    "Wat Bang Kung", "Bang Kung temple", "temple in banyan roots",
                    "temple covered by tree roots", "unique temple", "historic temple",
                    "temple with tree", "amazing temple", "special temple"
                ],
                "khlong_khon": [
                    # Thai variations
                    "คลองโคน", "คลองช่อง", "ป่าชายเลน", "ป่าชายเลนคลองโคน",
                    "ล่องเรือชมธรรมชาติ", "ชมนก", "ระบบนิเวศ", "ป่าชายเลนสมุทรสงคราม",
                    "คลองโคนเป็นยังไง", "ไปคลองโคน", "เที่ยวคลองโคน", "ธรรมชาติคลองโคน",
                    # English variations
                    "Khlong Khone", "Khlong Chong", "mangrove forest", "mangrove ecosystem",
                    "boat tour nature", "bird watching", "nature tour", "mangrove tour",
                    "Khlong Khone mangrove", "ecological tour", "wetland"
                ],
                "food": [
                    # Thai variations
                    "อาหารสมุทรสงคราม", "ของกินอร่อย", "อาหารท้องถิ่น", "อาหารดัง",
                    "กิน", "อร่อย", "ของกิน", "เมนูแนะนำ", "อาหารเด็ด", "ก๋วยเตี๋ยวเรือ",
                    "หอยทอด", "ปลาเผา", "กุ้งเผา", "ขนมหวาน", "ของฝาก",
                    # English variations
                    "Samut Songkhram food", "local cuisine", "what to eat", "delicious food",
                    "food recommendations", "local dishes", "specialties", "boat noodles",
                    "fried mussels", "grilled seafood", "local snacks", "street food"
                ],
                "general_travel": [
                    # Thai variations
                    "ที่เที่ยวสมุทรสงคราม", "เที่ยวไหนดี", "ที่เที่ยว", "สถานที่ท่องเที่ยว",
                    "แนะนำที่เที่ยว", "เที่ยวสมุทรสงคราม", "ไปไหนดี", "จุดท่องเที่ยว",
                    "สถานที่สำคัญ", "แลนด์มาร์ก", "ที่น่าไป", "ที่ต้องไป",
                    # English variations
                    "Samut Songkhram attractions", "places to visit", "tourist attractions",
                    "where to go", "sightseeing", "tourism spots", "must-visit places",
                    "travel recommendations", "things to do", "places to see"
                ],
                "accommodation": [
                    # Thai variations
                    "ที่พัก", "โรงแรม", "รีสอร์ท", "บ้านพัก", "ห้องพัก", "พักค้างคืน",
                    "จองที่พัก", "โรงแรมแนะนำ", "ที่พักดี", "ที่พักสะอาด", "ที่พักราคาถูก",
                    # English variations
                    "accommodation", "hotel", "resort", "guesthouse", "where to stay",
                    "hotel recommendations", "lodging", "overnight stay", "booking"
                ],
                "transportation": [
                    # Thai variations
                    "ไปยังไง", "เดินทาง", "การเดินทาง", "รถประจำทาง", "รถเช่า",
                    "ขับรถไป", "นั่งรถไป", "วิธีไป", "การขนส่ง", "จะไปยังไง",
                    # English variations
                    "how to get there", "transportation", "travel", "bus", "car rental",
                    "driving", "getting around", "how to go", "public transport"
                ]
            }
            
            # Pre-compute embeddings for all knowledge areas
            print("[INFO] Computing semantic embeddings...")
            self.embeddings = {}
            for area, phrases in self.knowledge_areas.items():
                self.embeddings[area] = self.model.encode(phrases)
            print("[OK] Semantic embeddings ready")
            
        except Exception as e:
            print(f"[ERROR] Failed to initialize semantic matcher: {e}")
            raise e
    
    def find_best_match(self, query: str, threshold: float = 0.3) -> Tuple[Optional[str], float]:
        """Find the best matching knowledge area using semantic similarity"""
        if not LIBRARIES_AVAILABLE or self.np is None or self.cosine_similarity is None:
            return None, 0.0
            
        try:
            query_embedding = self.model.encode([query])
            
            best_match = None
            best_score = 0.0
            
            for area, area_embeddings in self.embeddings.items():
                # Calculate similarity with all phrases in this area
                similarities = self.cosine_similarity(query_embedding, area_embeddings)[0]
                max_similarity = self.np.max(similarities)
                
                if max_similarity > best_score:
                    best_score = max_similarity
                    best_match = area
            
            # Only return if confidence is above threshold
            if best_score >= threshold:
                return best_match, best_score
            else:
                return None, best_score
                
        except Exception as e:
            print(f"[ERROR] Semantic matching failed: {e}")
            return None, 0.0
    
    def is_samutsongkhram_related(self, query: str, threshold: float = 0.25) -> bool:
        """Check if query is related to Samutsongkhram using semantic similarity"""
        if not LIBRARIES_AVAILABLE or self.np is None or self.cosine_similarity is None:
            return False
            
        try:
            samutsongkhram_phrases = [
                # Thai
                "สมุทรสงคราม", "จังหวัดสมุทรสงคราม", "เที่ยวสมุทรสงคราม",
                "อัมพวา", "วัดบางกุ้ง", "คลองโคน", "คลองช่อง", "ตลาดน้ำ", "ตลาดร่มหุบ",
                "ที่เที่ยวสมุทรสงคราม", "ท่องเที่ยวสมุทรสงคราม", "ป่าชายเลน",
                # English
                "Samut Songkhram", "Samut Songkhram province", "visit Samut Songkhram",
                "tourism in Samut Songkhram", "Amphawa", "Wat Bang Kung", "Khlong Khone",
                "floating market", "mangrove forest", "Maeklong railway market"
            ]
            
            query_embedding = self.model.encode([query])
            phrase_embeddings = self.model.encode(samutsongkhram_phrases)
            
            similarities = self.cosine_similarity(query_embedding, phrase_embeddings)[0]
            max_similarity = self.np.max(similarities)
            
            return max_similarity >= threshold
            
        except Exception as e:
            print(f"[ERROR] Samutsongkhram detection failed: {e}")
            return False
    
    def get_similarity_scores(self, query: str) -> Dict[str, float]:
        """Get similarity scores for all knowledge areas (for debugging)"""
        if not LIBRARIES_AVAILABLE or self.np is None or self.cosine_similarity is None:
            return {}
            
        try:
            query_embedding = self.model.encode([query])
            scores = {}
            
            for area, area_embeddings in self.embeddings.items():
                similarities = self.cosine_similarity(query_embedding, area_embeddings)[0]
                scores[area] = float(self.np.max(similarities))
            
            return scores
            
        except Exception as e:
            print(f"[ERROR] Failed to get similarity scores: {e}")
            return {}

# Test function
def test_semantic_matcher():
    """Test the semantic matcher with various queries"""
    if not LIBRARIES_AVAILABLE:
        print("Cannot test semantic matcher - libraries not available")
        return
        
    try:
        matcher = SemanticMatcher()
        
        test_queries = [
            "floating market",
            "temple with roots", 
            "mangrove forest",
            "where to stay",
            "delicious food"
        ]
        
        print("\n=== Semantic Matcher Test ===")
        for query in test_queries:
            try:
                topic, confidence = matcher.find_best_match(query)
                related = matcher.is_samutsongkhram_related(query)
                
                print(f"Query: '{query}'")
                print(f"  Topic: {topic} (confidence: {confidence:.3f})")
                print(f"  Samutsongkhram-related: {related}")
                print()
            except Exception as e:
                print(f"Failed to process query '{query}': {e}")
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_semantic_matcher()