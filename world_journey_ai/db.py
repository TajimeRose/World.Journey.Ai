"""Lightweight database helpers used across the project.

The module exposes a SQLAlchemy ``Place`` model together with engine/session
helpers that other packages (for example ``services.database``) rely on.  A
small ``search_places`` utility is also provided for quick manual testing via
scripts or notebooks.
"""

from __future__ import annotations

import os
from typing import Dict, Generator, Iterable, List

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
    """Search the ``places`` table for records containing ``keyword``."""

    init_db()
    session_factory = get_session_factory()
    kw = f"%{keyword}%"
    stmt = (
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
        .limit(limit)
    )

    with session_factory() as session:
        rows: Iterable[Place] = session.scalars(stmt)
        return [place.to_dict() for place in rows]
