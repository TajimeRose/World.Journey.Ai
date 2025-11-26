"""
Optimized Travel Chatbot with PostgreSQL Integration
Faster, smarter, database-powered chatbot
"""

from typing import Dict, List, Optional, Any
import json
import os

try:
    from world_journey_ai.services.database import get_db_service  # type: ignore[import]
except ImportError:  # Database module absent in some deployments
    get_db_service = None  # type: ignore

from world_journey_ai.configs import PromptRepo


class PostgreSQLTravelChatbot:
    """AI Travel Chatbot powered by PostgreSQL"""
    
    def __init__(self, gpt_service, language: str = "th", use_database: bool = True):
        """
        Initialize chatbot with PostgreSQL support
        
        Args:
            gpt_service: GPT service instance
            language: Response language ('th' or 'en')
            use_database: If True, use PostgreSQL; if False, fall back to JSON
        """
        self.gpt = gpt_service
        self.language = language
        self.use_database = use_database
        self.repo = PromptRepo()
        
        # Initialize database connection
        # Always require PostgreSQL now (no JSON fallback)
        try:
            if get_db_service is None:
                raise RuntimeError("Database service module not available")
            self.db = get_db_service()
            self.db_available = self.db.test_connection()
            if self.db_available:
                print("✅ PostgreSQL connected - using database for destinations only")
            else:
                raise RuntimeError("PostgreSQL unavailable - cannot operate (JSON fallback disabled)")
        except Exception as e:
            print(f"❌ Critical PostgreSQL error: {e}")
            self.db = None
            self.db_available = False
        
        # Cache character/config (loaded once)
        self._character_cache = None
        self._system_prompt_cache = None
    
    def _get_character(self) -> Dict:
        """Get character config (cached)"""
        if self._character_cache is None:
            self._character_cache = self.repo.get_character_profile()
        return self._character_cache
    
    def _get_system_prompt(self) -> str:
        """Build optimized system prompt (cached)"""
        if self._system_prompt_cache is None:
            character = self._get_character()
            persona = character.get('persona', {})
            
            self._system_prompt_cache = f"""คุณคือ {character.get('name', 'น้องปลาทู')} {character.get('system_role', '')}

บุคลิก:
{chr(10).join(f"- {p}" for p in persona.get('personality', [])[:3])}

เป้าหมาย:
- ตอบคำถามเกี่ยวกับท่องเที่ยวในสมุทรสงครามเท่านั้น
- ใช้ข้อมูลจากระบบเท่านั้น ห้ามแต่งเรื่อง
- ตอบสั้น กระชับ เป็นมิตร
- ถ้าไม่รู้ บอกตรงๆ

กฎพิเศษ:
- ถ้าถามจังหวัดอื่นนอกจากสมุทรสงคราม บอกอย่างสุภาพว่าดูแลเฉพาะสมุทรสงคราม
- ถ้าถามเรื่องไม่เกี่ยวกับท่องเที่ยว ปฏิเสธอย่างสุภาพและชี้แนะให้ถามเรื่องท่องเที่ยว
"""
        return self._system_prompt_cache
    
    def _is_attraction_query(self, query: str) -> bool:
        """
        Detect if user is asking about tourist attractions/sightseeing locations.
        Returns True if query contains attraction-related keywords.
        """
        query_lower = query.lower()
        attraction_keywords = [
            'สถานที่ท่องเที่ยว', 'แหล่งท่องเที่ยว', 'สถานที่', 'ที่เที่ยว', 
            'ท่องเที่ยว', 'เที่ยว', 'ไป', 'แนะนำ', 'น่าไป', 'ชม',
            'attraction', 'tourist', 'place', 'visit', 'sightseeing',
            'recommend', 'where to go', 'what to see'
        ]
        return any(keyword in query_lower for keyword in attraction_keywords)
    
    def _is_simple_keyword(self, query: str) -> bool:
        """
        Detect if query is a simple keyword (1-2 words without question structure).
        Returns True for simple searches like 'ตลาด', 'วัด', 'ทะเล'.
        """
        # Remove common Thai particles and spaces
        cleaned = query.strip()
        # Count words (approximate for Thai)
        word_count = len(cleaned.split())
        # Simple keyword: short (<=10 chars) or 1-2 words, no question marks
        is_short = len(cleaned) <= 10
        is_few_words = word_count <= 2
        no_question = '?' not in cleaned and 'ไหน' not in cleaned and 'อะไร' not in cleaned
        
        return (is_short or is_few_words) and no_question
    
    def _get_destinations(self, query: Optional[str] = None, limit: int = 3) -> List[Dict]:
        """
        Get destinations - intelligently choose search method based on query type.
        
        - For attraction queries: Use tourist_places table only
        - For simple keywords: Use all tables
        - For general queries: Use all tables
        """
        if not (self.db_available and self.db):
            return []
        
        if query:
            # Check if asking about attractions/tourist places FIRST (higher priority)
            if self._is_attraction_query(query):
                # Attraction query: use tourist_places table only
                return self.db.search_attractions_only(query, limit=limit)
            # Then check if this is a simple keyword search
            elif self._is_simple_keyword(query):
                # Simple keyword: search all tables (cafes, restaurants, attractions, etc.)
                return self.db.search_destinations(query, limit=limit)
            else:
                # Other queries: search all tables
                return self.db.search_destinations(query, limit=limit)
        
        return self.db.get_all_destinations()[:limit]
    
    def _get_trip_plans(self, duration: Optional[str] = None) -> List[Dict]:
        """Get trip plans - from PostgreSQL or JSON fallback"""
        if not (self.db_available and self.db):
            return []
        if duration:
            plan = self.db.get_trip_plan_by_duration(duration)
            return [plan] if plan else []
        return self.db.get_all_trip_plans()
    
    def _build_context(self, user_message: str) -> str:
        """
        Build minimal, relevant context for this specific query
        SMART: Only includes what's needed, not everything!
        """
        context_parts = []
        query_lower = user_message.lower()
        
        # 1. Get ONLY relevant destinations (not all!)
        relevant_destinations = self._get_destinations(user_message, limit=3)
        
        if relevant_destinations:
            context_parts.append("สถานที่ที่เกี่ยวข้อง:")
            for dest in relevant_destinations:
                name = dest.get('name', dest.get('name_th', ''))
                dest_type = dest.get('type', '')
                description = dest.get('description', '')[:120]
                rating = dest.get('rating', '')
                
                # Compact format
                info = f"• {name}"
                if dest_type:
                    info += f" ({dest_type})"
                if rating:
                    info += f" ⭐{rating}"
                if description:
                    info += f": {description}..."
                
                context_parts.append(info)
        
        # 2. Trip plans - only if asked about planning
        if any(kw in query_lower for kw in ['แผน', 'ทริป', 'วาง', 'เที่ยว', 'plan', 'trip']):
            trip_plans = self._get_trip_plans()
            if trip_plans:
                plan_names = [p.get('name', '') for p in trip_plans]
                context_parts.append(f"\nแผนทริปแนะนำ: {', '.join(plan_names)}")
        
        # 3. Database stats
        if self.db_available:
            context_parts.append("\n[ข้อมูลจาก PostgreSQL Database]")
        
        return "\n".join(context_parts) if context_parts else "ไม่พบข้อมูลที่เกี่ยวข้อง"
    
    def chat(self, user_message: str, user_id: Optional[str] = None, 
             session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Main chat method - optimized with PostgreSQL
        
        Args:
            user_message: User's question
            user_id: User ID for logging
            session_id: Session ID for tracking
        
        Returns:
            Dict with response and metadata
        """
        try:
            # Get relevant destinations based on query
            destinations = self._get_destinations(user_message, limit=3)
            
            # Call GPT with optimized settings
            result = self.gpt.generate_response(
                user_query=user_message,
                context_data=destinations,
                data_type="attractions"
            )
            
            response = result.get("response", "")
            
            # Log to database if available
            if self.db_available and self.db and user_id:
                self.db.save_message(user_id, user_message, response, session_id)
                
                # Log search query for analytics
                self.db.log_search_query(user_message, len(destinations), user_id)
            
            return {
                "success": True,
                "response": response,
                "language": self.language,
                "data_source": "postgresql",
                "destinations_used": len(destinations)
            }
            
        except Exception as e:
            print(f"❌ Chat error: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": self._get_fallback_message(),
                "language": self.language
            }
    
    def get_chat_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get user's chat history from database"""
        if self.db_available and self.db:
            return self.db.get_user_chat_history(user_id, limit)
        return []
    
    def get_popular_destinations(self, limit: int = 5) -> List[Dict]:
        """Get most popular/searched destinations"""
        if self.db_available and self.db:
            return self.db.get_popular_destinations(limit)
        return self._get_destinations(limit=limit)
    
    def search_destinations(self, query: str, limit: int = 5) -> List[Dict]:
        """Search destinations (exposed for API)"""
        return self._get_destinations(query, limit)
    
    def _get_fallback_message(self) -> str:
        """Fallback message when AI fails"""
        if self.language == "th":
            return "ขออภัยค่ะ ขณะนี้น้องปลาทูมีปัญหาเล็กน้อย กรุณาลองใหม่อีกครั้งนะคะ 🐟"
        return "Sorry, I'm experiencing technical difficulties. Please try again."


# Factory function for backward compatibility
def create_chatbot(gpt_service, language: str = "th", use_database: bool = True):
    """
    Create chatbot instance
    
    Args:
        gpt_service: GPT service
        language: Response language
        use_database: Use PostgreSQL (True) or JSON fallback (False)
    """
    # Check if PostgreSQL is configured
    postgres_configured = bool(os.getenv('POSTGRES_HOST') or os.getenv('DATABASE_URL'))
    if not postgres_configured:
        print("❌ PostgreSQL not configured - chatbot will return empty results")
    return PostgreSQLTravelChatbot(gpt_service, language, True)
