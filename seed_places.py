# seed_places.py
import json
from pathlib import Path
import sys

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from world_journey_ai.db import get_engine

def get_data_path():
    """Get the path to tourist_places.json using multiple fallback strategies."""
    
    # Method 1: Try importlib.resources (best for packaged apps)
    try:
        if sys.version_info >= (3, 9):
            from importlib.resources import files
        else:
            from importlib_resources import files
        
        data_file = files('world_journey_ai').joinpath('data', 'tourist_places.json')
        if data_file.is_file():
            print(f"✅ Found data using importlib.resources: {data_file}")
            return data_file
    except Exception as e:
        print(f"⚠️ importlib.resources failed: {e}")
    
    # Method 2: Relative to script file (works in development)
    script_based = Path(__file__).parent / "world_journey_ai" / "data" / "tourist_places.json"
    if script_based.exists():
        print(f"✅ Found data relative to script: {script_based}")
        return script_based
    
    # Method 3: Using package __file__ location
    try:
        import world_journey_ai
        package_dir = Path(world_journey_ai.__file__).parent
        package_based = package_dir / "data" / "tourist_places.json"
        if package_based.exists():
            print(f"✅ Found data using package location: {package_based}")
            return package_based
    except Exception as e:
        print(f"⚠️ Package-based lookup failed: {e}")
    
    # If nothing worked, raise error
    raise FileNotFoundError(
        f"Cannot find tourist_places.json\n"
        f"Tried:\n"
        f"  1. importlib.resources\n"
        f"  2. {script_based}\n"
        f"  3. Package-based lookup"
    )

DATA_PATH = get_data_path()


def main():
    # Load JSON data - handle both Path and Traversable types
    try:
        # If it's a Traversable from importlib.resources, convert to string path
        if not isinstance(DATA_PATH, Path):
            # Convert Traversable to Path
            path_str = str(DATA_PATH)
            with open(path_str, encoding="utf-8") as f:
                places = json.load(f)
        else:
            # If it's a regular Path
            with open(DATA_PATH, encoding="utf-8") as f:
                places = json.load(f)
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        raise

    engine = get_engine()

    # Ensure we can upsert based on place_id for stable seeding runs
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE places ADD CONSTRAINT places_place_id_key UNIQUE (place_id)"))
            print("✅ Added unique constraint on places.place_id")
        except ProgrammingError as exc:
            # Constraint already exists or database backend doesn't support statement (ignore)
            if "already" in str(exc).lower():
                pass
            else:
                raise

    # Insert into places table using cleaned JSON schema
    insert_sql = text("""
        INSERT INTO places
            (place_id, name, category, address, rating, reviews, description, images, tags, link)
        VALUES
            (:place_id, :name, :category, :address, :rating, :reviews, :description, :images, :tags, :link)
        ON CONFLICT (place_id) DO UPDATE SET
            name = EXCLUDED.name,
            category = EXCLUDED.category,
            address = EXCLUDED.address,
            rating = EXCLUDED.rating,
            reviews = EXCLUDED.reviews,
            description = EXCLUDED.description,
            images = EXCLUDED.images,
            tags = EXCLUDED.tags,
            link = EXCLUDED.link
    """)

    processed = 0
    with engine.begin() as conn:
        for p in places:
            place_id = p.get("place_id")
            name = p.get("name")

            if not place_id or not name:
                print(f"⚠️ Skipping record without required fields: place_id={place_id}, name={name}")
                continue

            place_data = {
                "place_id": place_id,
                "name": name,
                "category": p.get("category"),
                "address": p.get("address"),
                "rating": p.get("rating"),
                "reviews": p.get("reviews"),
                "description": p.get("description") or "",
                "images": json.dumps(p.get("images") or [], ensure_ascii=False),
                "tags": json.dumps(p.get("tags") or [], ensure_ascii=False),
                "link": p.get("link"),
            }

            conn.execute(insert_sql, place_data)
            processed += 1

    print(f"✅ Inserted/Updated {processed} rows into places table.")


if __name__ == "__main__":
    main()
