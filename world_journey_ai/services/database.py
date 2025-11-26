"""Database service layer for PostgreSQL-backed resources.

This module wraps the SQLAlchemy helpers defined in ``world_journey_ai.db``
so the rest of the codebase (notably ``chatbot_postgres``) can talk to the
PostgreSQL database managed through pgAdmin 4 or any other PostgreSQL client.

The implementation focuses on the "places" table defined in ``db.py``.  Other
methods that were previously backed by different tables now degrade
gracefully: they return empty results and log a warning so callers can decide
how to proceed without the application crashing.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy import select, or_, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from world_journey_ai.db import Place, TouristPlace, get_session_factory, init_db


class DatabaseService:
    """High-level database helper for chatbot features."""

    def __init__(self) -> None:
        # Ensure tables exist before we start using them; harmless if already created.
        init_db()
        self._session_factory = get_session_factory()

    # ------------------------------------------------------------------
    # Session helpers
    # ------------------------------------------------------------------
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def test_connection(self) -> bool:
        """Ping the database by executing a trivial statement."""
        try:
            with self.session() as session:
                session.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError as exc:
            print(f"Database connection failed: {exc}")
            return False

    # ------------------------------------------------------------------
    # Places / destinations
    # ------------------------------------------------------------------
    def _place_to_dict(self, place: Place) -> Dict[str, Any]:
        return place.to_dict()

    def get_all_destinations(self) -> List[Dict[str, Any]]:
        with self.session() as session:
            # Get from both tables
            places_result = session.execute(select(Place).order_by(Place.rating.desc().nullslast()))
            places = places_result.scalars().all()
            
            tourist_result = session.execute(select(TouristPlace).order_by(TouristPlace.rating.desc().nullslast()))
            tourist_places = tourist_result.scalars().all()
            
            all_destinations = [self._place_to_dict(place) for place in places]
            all_destinations.extend([place.to_dict() for place in tourist_places])
            
            # Sort by rating
            all_destinations.sort(key=lambda x: float(x.get('rating', 0) or 0), reverse=True)  # type: ignore
            return all_destinations

    def search_destinations(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        pattern = f"%{query}%"
        with self.session() as session:
            # Search in places table
            places_stmt = (
                select(Place)
                .where(
                    or_(
                        Place.name.ilike(pattern),
                        Place.description.ilike(pattern),
                        Place.address.ilike(pattern),
                        Place.category.ilike(pattern),
                    )
                )
                .order_by(Place.rating.desc().nullslast())
            )
            
            # Search in tourist_places table
            tourist_stmt = (
                select(TouristPlace)
                .where(
                    or_(
                        TouristPlace.name_th.ilike(pattern),
                        TouristPlace.description.ilike(pattern),
                        TouristPlace.location.ilike(pattern),
                    )
                )
                .order_by(TouristPlace.rating.desc().nullslast())
            )
            
            places_result = session.execute(places_stmt)
            places = places_result.scalars().all()
            
            tourist_result = session.execute(tourist_stmt)
            tourist_places = tourist_result.scalars().all()
            
            results = [self._place_to_dict(place) for place in places]
            results.extend([place.to_dict() for place in tourist_places])
            
            # Sort by rating and limit
            results.sort(key=lambda x: float(x.get('rating', 0) or 0), reverse=True)  # type: ignore
            return results[:limit]

    def search_attractions_only(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search ONLY tourist_places table for tourist attractions.
        Used when user asks about attractions, tourist places, sightseeing locations.
        
        If query contains only generic terms without specific keywords, 
        returns top-rated tourist attractions.
        """
        # Generic attraction keywords that indicate a general request
        generic_patterns = [
            'แนะนำ', 'สถานที่', 'ท่องเที่ยว', 'ที่เที่ยว', 'เที่ยว', 
            'ไหน', 'บ้าง', 'อะไร', 'ชม', 'ไป'
        ]
        
        # Check if query contains specific place names/types (not generic)
        specific_keywords = ['ตลาด', 'วัด', 'ทะเล', 'ภูเขา', 'น้ำตก', 'สวน', 'พิพิธภัณฑ์', 'โบสถ์']
        has_specific = any(keyword in query for keyword in specific_keywords)
        
        # Count how many generic terms are in the query
        generic_count = sum(1 for pattern in generic_patterns if pattern in query)
        
        # If mostly generic (2+ generic terms and no specific keywords), return top places
        is_generic_query = generic_count >= 2 and not has_specific
        
        with self.session() as session:
            # If generic query, return top tourist attractions
            if is_generic_query:
                tourist_stmt = (
                    select(TouristPlace)
                    .order_by(TouristPlace.rating.desc().nullslast())
                    .limit(limit)
                )
            else:
                # Search with the full query
                pattern = f"%{query}%"
                tourist_stmt = (
                    select(TouristPlace)
                    .where(
                        or_(
                            TouristPlace.name_th.ilike(pattern),
                            TouristPlace.description.ilike(pattern),
                            TouristPlace.location.ilike(pattern),
                        )
                    )
                    .order_by(TouristPlace.rating.desc().nullslast())
                    .limit(limit)
                )
            
            tourist_result = session.execute(tourist_stmt)
            tourist_places = tourist_result.scalars().all()
            
            return [place.to_dict() for place in tourist_places]

    def get_destination_by_id(self, destination_id: str) -> Optional[Dict[str, Any]]:
        with self.session() as session:
            # Check if it's a tourist place (starts with 'tourist_')
            if destination_id.startswith('tourist_'):
                try:
                    tourist_id = int(destination_id.replace('tourist_', ''))
                    tourist_place = session.get(TouristPlace, tourist_id)
                    return tourist_place.to_dict() if tourist_place else None
                except ValueError:
                    pass
            
            # Try regular places table
            place = session.get(Place, destination_id)
            return self._place_to_dict(place) if place else None

    def get_destinations_by_type(self, dest_type: str) -> List[Dict[str, Any]]:
        pattern = f"%{dest_type}%"
        with self.session() as session:
            # Search places table
            places_rows = session.execute(
                select(Place).where(Place.category.ilike(pattern)).order_by(Place.rating.desc().nullslast())
            )
            places = places_rows.scalars().all()
            
            # Search tourist_places table (search in tags)
            from sqlalchemy import cast, Text
            tourist_rows = session.execute(
                select(TouristPlace).where(
                    cast(TouristPlace.tags, Text).ilike(pattern)
                ).order_by(TouristPlace.rating.desc().nullslast())
            )
            tourist_places = tourist_rows.scalars().all()
            
            results = [self._place_to_dict(place) for place in places]
            results.extend([place.to_dict() for place in tourist_places])
            
            results.sort(key=lambda x: float(x.get('rating', 0) or 0), reverse=True)  # type: ignore
            return results

    # ------------------------------------------------------------------
    # Trip plans & analytics (not yet backed by concrete tables)
    # ------------------------------------------------------------------
    def get_all_trip_plans(self) -> List[Dict[str, Any]]:  # pragma: no cover - placeholder
        print("[WARN] get_all_trip_plans called but trip plan storage is not implemented.")
        return []

    def get_trip_plan_by_duration(self, duration: str) -> Optional[Dict[str, Any]]:  # pragma: no cover - placeholder
        print("[WARN] get_trip_plan_by_duration called but trip plan storage is not implemented.")
        return None

    def save_message(
        self,
        user_id: str,
        message: str,
        response: str,
        session_id: Optional[str] = None,
    ) -> Optional[int]:  # pragma: no cover - placeholder
        print("[WARN] Chat logging is not implemented yet; skipping save_message call.")
        return None

    def log_search_query(
        self,
        query: str,
        results_count: int,
        user_id: Optional[str] = None,
    ) -> None:  # pragma: no cover - placeholder
        print("[WARN] Search logging is not implemented yet; skipping log_search_query call.")

    def get_user_chat_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:  # pragma: no cover - placeholder
        print("[WARN] get_user_chat_history called but chat history storage is not implemented.")
        return []

    def get_popular_destinations(self, limit: int = 10) -> List[Dict[str, Any]]:  # pragma: no cover - placeholder
        # Fall back to highest-rated destinations for now.
        return self.get_all_destinations()[:limit]


_db_service: Optional[DatabaseService] = None


def get_db_service() -> DatabaseService:
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service
