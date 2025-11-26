# seed_places.py
import json
from pathlib import Path

from sqlalchemy import text
from world_journey_ai.db import get_engine  # Fixed import path

# Try multiple possible locations for the data file
# First, try as a package resource (works in both local and Docker)
try:
    # Option 1: Using importlib.resources (Python 3.9+)
    from importlib.resources import files
    DATA_PATH = files('world_journey_ai').joinpath('data', 'tourist_places.json')
    print(f"📦 Using package resource: {DATA_PATH}")
except (ImportError, AttributeError):
    # Option 2: Fallback to file path detection
    DATA_PATH = Path(__file__).parent / "world_journey_ai" / "data" / "tourist_places.json"
    
    # Fallback to check if data is in the same directory
    if not DATA_PATH.exists():
        DATA_PATH = Path(__file__).parent / "data" / "tourist_places.json"
    
    # Final fallback - check if file still doesn't exist and show helpful error
    if not DATA_PATH.exists():
        print(f"❌ ERROR: Could not find tourist_places.json")
        print(f"Tried: {Path(__file__).parent / 'world_journey_ai' / 'data' / 'tourist_places.json'}")
        print(f"Tried: {Path(__file__).parent / 'data' / 'tourist_places.json'}")
        print(f"Current directory: {Path.cwd()}")
        print(f"Script location: {Path(__file__).parent}")
        
        # List what's actually in the directories
        print(f"\nContents of /app:")
        for item in Path('/app').iterdir():
            print(f"  - {item}")
        
        if Path('/app/world_journey_ai').exists():
            print(f"\nContents of /app/world_journey_ai:")
            for item in Path('/app/world_journey_ai').iterdir():
                print(f"  - {item}")
        
        raise FileNotFoundError(f"tourist_places.json not found in expected locations")
    
    print(f"✅ Loading data from: {DATA_PATH}")


def main():
    # โหลดข้อมูลจากไฟล์ JSON
    with DATA_PATH.open(encoding="utf-8") as f:
        places = json.load(f)

    engine = get_engine()

    insert_sql = text("""
        INSERT INTO places
            (place_id, name, category, address, rating,
             reviews, description, images, tags, link)
        VALUES
            (:place_id, :name, :category, :address, :rating,
             :reviews, :description, :images, :tags, :link)
    """)

    inserted = 0
    with engine.begin() as conn:
        for p in places:
            place_id = str(p.get("id")) if p.get("id") is not None else None
            name = p.get("name_th")
            category = None  # ถ้าจะ map จากอย่างอื่นค่อยเติมทีหลัง
            address = p.get("location")
            rating = p.get("rating")  # ถ้าไม่มีในไฟล์จะเป็น None
            reviews = None
            description = p.get("description")

            images = json.dumps(p.get("images", []), ensure_ascii=False)
            tags = json.dumps(p.get("tags", []), ensure_ascii=False)
            link = None  # ถ้ามีลิงก์ค่อยใส่ทีหลัง

            conn.execute(
                insert_sql,
                {
                    "place_id": place_id,
                    "name": name,
                    "category": category,
                    "address": address,
                    "rating": rating,
                    "reviews": reviews,
                    "description": description,
                    "images": images,
                    "tags": tags,
                    "link": link,
                },
            )
            inserted += 1

    print(f"Inserted {inserted} rows into places table.")


if __name__ == "__main__":
    main()
