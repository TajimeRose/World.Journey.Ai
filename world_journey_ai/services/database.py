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

from world_journey_ai.db import Place, get_session_factory, init_db


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
            rows = session.execute(select(Place).order_by(Place.rating.desc().nullslast()))
            return [self._place_to_dict(place) for place in rows.scalars()]

    def search_destinations(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        pattern = f"%{query}%"
        with self.session() as session:
            stmt = (
                select(Place)
                .where(
                    or_(
                        Place.name.ilike(pattern),
                        Place.place_name.ilike(pattern),
                        Place.description.ilike(pattern),
                        Place.city.ilike(pattern),
                        Place.province.ilike(pattern),
                    )
                )
                .order_by(Place.rating.desc().nullslast())
                .limit(limit)
            )
            rows = session.execute(stmt)
            return [self._place_to_dict(place) for place in rows.scalars()]

    def get_destination_by_id(self, destination_id: str) -> Optional[Dict[str, Any]]:
        with self.session() as session:
            place = session.get(Place, destination_id)
            return self._place_to_dict(place) if place else None

    def get_destinations_by_type(self, dest_type: str) -> List[Dict[str, Any]]:
        pattern = f"%{dest_type}%"
        with self.session() as session:
            rows = session.execute(
                select(Place).where(Place.category.ilike(pattern)).order_by(Place.rating.desc().nullslast())
            )
            return [self._place_to_dict(place) for place in rows.scalars()]

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
