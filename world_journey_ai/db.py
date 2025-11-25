import os
from sqlalchemy import create_engine, Column, String, Text, Float, JSON
from sqlalchemy.orm import sessionmaker, declarative_base, Session

Base = declarative_base()

class Place(Base):
    __tablename__ = 'places'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    place_name = Column(String)
    description = Column(Text)
    city = Column(String)
    province = Column(String)
    type = Column(JSON)  # List of strings
    highlights = Column(JSON)  # List of strings
    place_information = Column(JSON)  # Dict
    images = Column(JSON)  # List of strings
    category = Column(String)
    rating = Column(Float)
    source = Column(String)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "place_name": self.place_name,
            "description": self.description,
            "city": self.city,
            "province": self.province,
            "type": self.type,
            "highlights": self.highlights,
            "place_information": self.place_information,
            "images": self.images,
            "category": self.category,
            "rating": self.rating,
            "source": self.source
        }

def get_db_url():
    return os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/worldjourney")

_engine = None
_SessionLocal = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(get_db_url())
    return _engine

def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal

def init_db():
    """Initialize database tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)

def get_db():
    """Dependency for getting a DB session."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
