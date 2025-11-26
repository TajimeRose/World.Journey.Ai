"""Lightweight database helpers used across the project.

The module exposes a SQLAlchemy ``Place`` model together with engine/session
helpers that other packages (for example ``services.database``) rely on.  A
small ``search_places`` utility is also provided for quick manual testing via
scripts or notebooks.
"""

from __future__ import annotations

import os
from typing import Dict, Generator, Iterable, List, cast as typing_cast

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency during runtime
    load_dotenv = None  # type: ignore

from sqlalchemy import JSON, Column, Float, Integer, String, Text, cast, create_engine, or_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

if load_dotenv:
    # Automatically pull DATABASE_URL, OPENAI_API_KEY, etc. from .env files.
    load_dotenv()


Base = declarative_base()


class Place(Base):
    """ORM model mapping the ``places`` table (existing schema)."""

    __tablename__ = "places"

    # Actual columns in the database
    id = Column(Integer, primary_key=True)
    place_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String)
    address = Column(Text)
    rating = Column(Float)
    reviews = Column(Integer)
    description = Column(Text)
    images = Column(JSON)
    tags = Column(JSON)  # list[str]
    link = Column(String)

    def to_dict(self) -> Dict[str, object]:
        """Convert to dict with chatbot-compatible field names and defaults."""
        # Extract city from address if available
        city_value = ""
        if self.address is not None:
            # Try to extract city/district from address
            import re
            city_match = re.search(r'(อำเภอ|อ\.)\s*([^\s,]+)', str(self.address))
            if city_match:
                city_value = city_match.group(2)
        
        # Build type list from category
        type_value = [self.category] if self.category is not None else []
        
        return {
            "id": str(self.id),
            "place_id": self.place_id,
            "name": self.name,
            "place_name": self.name,  # Use name as place_name
            "description": self.description,
            "address": self.address,
            "city": city_value,
            "province": "สมุทรสงคราม",  # Default province
            "type": type_value,
            "category": self.category,
            "rating": self.rating,
            "reviews": self.reviews,
            "tags": self.tags if self.tags is not None else [],
            "link": self.link,
            "highlights": self.tags if self.tags is not None else [],  # Use tags as highlights
            "place_information": {
                "detail": self.description,
                "category_description": self.category,
            },
            "images": self.images if self.images is not None else [],
            "source": "database",
        }

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Place(id={self.id!r}, name={self.name!r}, rating={self.rating!r})"


class TouristPlace(Base):
    """ORM model mapping the ``tourist_places`` table (Thai tourism data)."""

    __tablename__ = "tourist_places"

    # Actual columns in the database
    id = Column(Integer, primary_key=True)
    name_th = Column(Text, nullable=False)
    location = Column(Text)
    rating = Column(Float)
    images = Column(JSON)  # list[str]
    tags = Column(JSON)  # list[str]
    description = Column(Text)

    def to_dict(self) -> Dict[str, object]:
        """Convert to dict with chatbot-compatible field names and defaults."""
        # Extract city from location if available
        city_value = ""
        location_str = str(self.location) if self.location is not None else ""
        if location_str:
            # Remove 'อำเภอ' prefix if present
            import re
            city_match = re.search(r'(?:อำเภอ|อ\.)\s*([^\s,]+)', location_str)
            if city_match:
                city_value = city_match.group(1)
            else:
                city_value = location_str
        
        # Build type list from tags
        tags_list = list(self.tags) if self.tags is not None else []  # type: ignore
        type_value = tags_list[:2] if len(tags_list) > 0 else []
        
        rating_val = typing_cast(float | None, self.rating)
        rating_value = float(rating_val) if rating_val is not None else 0.0
        images_list = list(self.images) if self.images is not None else []  # type: ignore
        
        return {
            "id": f"tourist_{self.id}",
            "place_id": f"tourist_{self.id}",
            "name": self.name_th,
            "place_name": self.name_th,
            "description": self.description,
            "address": location_str,
            "city": city_value,
            "province": "สมุทรสงคราม",
            "type": type_value,
            "category": type_value[0] if len(type_value) > 0 else "สถานที่ท่องเที่ยว",
            "rating": rating_value,
            "reviews": 0,
            "tags": tags_list,
            "link": None,
            "highlights": tags_list,
            "place_information": {
                "detail": self.description,
                "category_description": type_value[0] if len(type_value) > 0 else "สถานที่ท่องเที่ยว",
            },
            "images": images_list,
            "source": "tourist_places",
        }

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"TouristPlace(id={self.id!r}, name_th={self.name_th!r}, rating={self.rating!r})"


def get_db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    print("[WARN] DATABASE_URL is not set; falling back to the default postgres URL")
    # Adjust the fallback to match your actual database name if needed.
    return "postgresql://postgres:password@localhost:5432/worldjourney"


_ENGINE: Engine | None = None
_SESSION_FACTORY: sessionmaker | None = None


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine(get_db_url(), future=True, pool_pre_ping=True)
    return _ENGINE


def get_session_factory() -> sessionmaker:
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        _SESSION_FACTORY = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)
    return _SESSION_FACTORY


def init_db() -> None:
    """Create tables if they do not exist yet."""
    Base.metadata.create_all(get_engine())


def get_db() -> Generator[Session, None, None]:
    """Yield a managed SQLAlchemy session (FastAPI-compatible helper)."""
    session_factory = get_session_factory()
    session: Session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def search_places(keyword: str, limit: int = 10) -> List[Dict[str, object]]:
    """Search both ``places`` and ``tourist_places`` tables for records containing ``keyword``."""

    init_db()
    session_factory = get_session_factory()
    kw = f"%{keyword}%"
    
    # Search regular places
    places_stmt = (
        select(Place)
        .where(
            or_(
                Place.name.ilike(kw),
                Place.category.ilike(kw),
                Place.address.ilike(kw),
                Place.description.ilike(kw),
                cast(Place.tags, Text).ilike(kw),  # tags stored as JSON/array
            )
        )
        .order_by(Place.rating.desc().nullslast())
    )
    
    # Search tourist places
    tourist_stmt = (
        select(TouristPlace)
        .where(
            or_(
                TouristPlace.name_th.ilike(kw),
                TouristPlace.location.ilike(kw),
                TouristPlace.description.ilike(kw),
                cast(TouristPlace.tags, Text).ilike(kw),
            )
        )
        .order_by(TouristPlace.rating.desc().nullslast())
    )

    with session_factory() as session:
        places_rows: Iterable[Place] = session.scalars(places_stmt)
        tourist_rows: Iterable[TouristPlace] = session.scalars(tourist_stmt)
        
        results = [place.to_dict() for place in places_rows]
        results.extend([place.to_dict() for place in tourist_rows])
        
        # Sort by rating and limit
        results.sort(key=lambda x: float(x.get('rating', 0) or 0), reverse=True)  # type: ignore
        return results[:limit]
