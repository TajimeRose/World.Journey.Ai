# seed_places.py
import json
from pathlib import Path
import sys

from sqlalchemy import text
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

    # Insert into tourist_places table (not places table!)
    # Map Google Places data to tourist_places schema
    insert_sql = text("""
        INSERT INTO tourist_places
            (id, name_th, location, rating, description, images, tags)
        VALUES
            (:id, :name_th, :location, :rating, :description, :images, :tags)
        ON CONFLICT (id) DO UPDATE SET
            name_th = EXCLUDED.name_th,
            location = EXCLUDED.location,
            rating = EXCLUDED.rating,
            description = EXCLUDED.description,
            images = EXCLUDED.images,
            tags = EXCLUDED.tags
    """)

    inserted = 0
    with engine.begin() as conn:
        for idx, p in enumerate(places, start=1):
            # Transform Google Places data to tourist_places schema
            place_data = {
                "id": idx,  # Use sequential integer ID
                "name_th": p.get("name"),  # Use name as name_th
                "location": p.get("address"),  # Use address as location
                "rating": p.get("rating"),
                "description": p.get("description") or "",  # Handle null descriptions
                "images": json.dumps([p.get("featured_image")] if p.get("featured_image") else [], ensure_ascii=False),
                "tags": json.dumps(
                    [cat.strip() for cat in (p.get("categories") or "").split(",") if cat.strip()],
                    ensure_ascii=False
                ),
            }
            
            conn.execute(insert_sql, place_data)
            inserted += 1

    print(f"✅ Inserted/Updated {inserted} rows into tourist_places table.")


if __name__ == "__main__":
    main()
