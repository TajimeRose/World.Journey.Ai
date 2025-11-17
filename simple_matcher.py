"""
Simple fallback for chatbot without semantic search
Uses keyword matching only but with better organization
"""

class SimpleMatcher:
    def __init__(self):
        """Initialize simple keyword matcher as fallback"""
        print("[FALLBACK] Using simple keyword matching (semantic search not available)")
        
        # Enhanced keyword mapping including synonyms and variations
        self.enhanced_keywords = {
            "amphawa": [
                # Direct names
                "อัมพวา", "amphawa", "ตลาดน้ำอัมพวา",
                # Descriptive terms
                "ตลาดน้ำ", "floating market", "ตลาดน้ำที่มีชื่อเสียง", "ตลาดน้ำดัง",
                "ตลาดอัมพวา", "famous floating market", "weekend market",
                "หิ่งห้อย", "firefly", "ชมหิ่งห้อย", "firefly watching"
            ],
            "bang_kung": [
                # Direct names  
                "วัดบางกุ้ง", "bang kung", "บางกุ้ง",
                # Descriptive terms
                "วัดในรากไผ่", "วัดที่มีรากไผ่", "วัดรากไผ่", 
                "temple in roots", "temple with roots", "banyan roots",
                "วัดพิเศษ", "วัดแปลก", "unique temple", "special temple"
            ],
            "khlong_khon": [
                # Direct names
                "คลองโคน", "khlong khon", "คลองช่อง", "khlong chong",
                # Descriptive terms  
                "ป่าชายเลน", "mangrove", "mangrove forest", "ป่าชายเลนคลองโคน",
                "ล่องเรือ", "boat tour", "ชมธรรมชาติ", "nature tour",
                "ชมนก", "bird watching", "ระบบนิเวศ", "ecosystem"
            ],
            "food": [
                # General food terms
                "อาหาร", "food", "กิน", "eat", "อร่อย", "delicious",
                "ของกิน", "ของกินอร่อย", "อาหารอร่อย", "อาหารท้องถิ่น",
                "local food", "local cuisine", "specialties",
                # Specific dishes
                "ก๋วยเตี๋ยวเรือ", "boat noodles", "หอยทอด", "fried mussels",
                "ปลาเผา", "grilled fish", "กุ้งเผา", "grilled shrimp"
            ],
            "general_travel": [
                "ที่เที่ยว", "เที่ยว", "เที่ยวไหนดี", "สถานที่ท่องเที่ยว",
                "แนะนำที่เที่ยว", "จุดท่องเที่ยว", "สถานที่สำคัญ",
                "attractions", "places to visit", "tourist spots", 
                "where to go", "things to do", "sightseeing"
            ],
            "accommodation": [
                "ที่พัก", "โรงแรม", "รีสอร์ท", "บ้านพัก", "ห้องพัก",
                "hotel", "resort", "accommodation", "where to stay",
                "lodging", "guesthouse"
            ],
            "transportation": [
                "ไปยังไง", "เดินทาง", "การเดินทาง", "วิธีไป",
                "how to get there", "transportation", "how to go",
                "getting around", "travel"
            ]
        }
        
        # Samutsongkhram indicators for location detection
        self.samutsongkhram_indicators = [
            "สมุทรสงคราม", "samut songkhram", "อัมพวา", "amphawa", 
            "วัดบางกุ้ง", "bang kung", "คลองโคน", "khlong khon",
            "คลองช่อง", "khlong chong", "ตลาดน้ำ", "floating market", 
            "ตลาดร่มหุบ", "maeklong", "เที่ยวสมุทรสงคราม"
        ]

    def topic_keywords(self, topic):
        """Return the keyword list for a given topic (copy to avoid mutation)."""
        if not topic:
            return []
        keywords = self.enhanced_keywords.get(topic)
        if not keywords:
            return []
        return list(keywords)
    
    def find_best_match(self, query: str, threshold: float = 0.3):
        """Find best matching topic using enhanced keyword matching"""
        query_lower = query.lower()
        
        # Count matches for each topic
        topic_scores = {}
        for topic, keywords in self.enhanced_keywords.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    score += 1
                    matched_keywords.append(keyword)
            
            if score > 0:
                # Normalize score by number of keywords in topic
                normalized_score = min(score / len(keywords), 1.0)
                topic_scores[topic] = (normalized_score, matched_keywords)
        
        if not topic_scores:
            return None, 0.0
        
        # Get best match
        best_topic = max(topic_scores.keys(), key=lambda k: topic_scores[k][0])
        best_score, matched = topic_scores[best_topic]
        
        # Safe printing for console compatibility
        try:
            print(f"[KEYWORD] Detected topic: {best_topic} (score: {best_score:.3f}, {len(matched)} matches)")
        except UnicodeEncodeError:
            print(f"[KEYWORD] Detected topic: {best_topic} (score: {best_score:.3f})")
        
        return best_topic if best_score >= threshold else None, best_score
    
    def is_samutsongkhram_related(self, query: str, threshold: float = 0.25):
        """Check if query is Samutsongkhram-related using keywords"""
        query_lower = query.lower()
        
        matches = 0
        for indicator in self.samutsongkhram_indicators:
            if indicator.lower() in query_lower:
                matches += 1
        
        # Simple scoring: any match = related
        is_related = matches > 0
        try:
            print(f"[KEYWORD] Samutsongkhram-related: {is_related} ({matches} matches)")
        except UnicodeEncodeError:
            print(f"[KEYWORD] Samutsongkhram-related: {is_related}")
        
        return is_related

# Create a version that tries semantic first, falls back to simple
class FlexibleMatcher:
    def __init__(self):
        """Initialize with semantic search if available, otherwise use simple matching"""
        self.semantic_matcher = None
        self.simple_matcher = SimpleMatcher()
        
        # Try to initialize semantic search
        try:
            from semantic_search import SemanticMatcher, LIBRARIES_AVAILABLE
            if LIBRARIES_AVAILABLE:
                self.semantic_matcher = SemanticMatcher()
                print("[OK] Semantic search enabled")
            else:
                print("[FALLBACK] Semantic libraries not available")
        except Exception as e:
            print(f"[FALLBACK] Semantic search failed: {e}")
    
    def find_best_match(self, query: str, threshold: float = 0.3):
        """Try semantic first, fallback to keyword matching"""
        if self.semantic_matcher:
            try:
                return self.semantic_matcher.find_best_match(query, threshold)
            except Exception as e:
                print(f"[ERROR] Semantic search failed, using fallback: {e}")
        
        return self.simple_matcher.find_best_match(query, threshold)
    
    def is_samutsongkhram_related(self, query: str, threshold: float = 0.25):
        """Try semantic first, fallback to keyword matching"""
        if self.semantic_matcher:
            try:
                return self.semantic_matcher.is_samutsongkhram_related(query, threshold)
            except Exception as e:
                print(f"[ERROR] Semantic detection failed, using fallback: {e}")
        
        return self.simple_matcher.is_samutsongkhram_related(query, threshold)

    def get_topic_keywords(self, topic):
        """Expose topic keywords from whichever matcher is available."""
        if not topic:
            return []

        keywords = []
        keywords.extend(self.simple_matcher.topic_keywords(topic))

        if self.semantic_matcher and hasattr(self.semantic_matcher, "knowledge_areas"):
            keywords.extend(self.semantic_matcher.knowledge_areas.get(topic, []))

        deduped = []
        seen = set()
        for keyword in keywords:
            normalized = keyword.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(keyword)
        return deduped

# Test function
def test_flexible_matcher():
    """Test the flexible matcher with various queries"""
    print("=== Testing Flexible Matcher ===")
    
    matcher = FlexibleMatcher()
    
    test_queries = [
        "คลองช่อง",  # Original problem case
        "ป่าชายเลน",  # Mangrove (synonym)
        "วัดที่มีรากไผ่",  # Temple description
        "ตลาดน้ำดัง",  # Famous floating market
        "ที่พัก",  # Accommodation
        "อาหารอร่อย",  # Delicious food
        "ไปยังไง",  # Transportation
        "เที่ยวไหนดี",  # General travel
        "floating market",  # English
        "temple with roots",  # English
        "mangrove forest",  # English
    ]
    
    for query in test_queries:
        try:
            topic, confidence = matcher.find_best_match(query)
            related = matcher.is_samutsongkhram_related(query)
            
            print(f"Query: '{query}'")
            print(f"  Topic: {topic} (confidence: {confidence:.3f})")
            print(f"  Samutsongkhram-related: {related}")
            print()
        except Exception as e:
            print(f"Error processing '{query}': {e}")

if __name__ == "__main__":
    test_flexible_matcher()
