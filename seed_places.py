# seed_places.py
import json
import os
import sys
from pathlib import Path
from typing import Iterable, Union

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from world_journey_ai.db import get_engine

DEFAULT_REMOTE_URL = (
    "https://raw.githubusercontent.com/TajimeRose/NongPlato.Ai/krakenv2/"
    "world_journey_ai/data/tourist_places.json"
)


def find_data_path() -> Union[Path, "Traversable", None]:  # type: ignore[name-defined]
    """Locate tourist_places.json if it exists on disk."""

    # Method 1: Try importlib.resources (best for packaged apps)
    try:
        if sys.version_info >= (3, 9):
            from importlib.resources import files
        else:  # pragma: no cover - backport for <3.9
            from importlib_resources import files  # type: ignore

        data_file = files("world_journey_ai").joinpath("data", "tourist_places.json")
        if getattr(data_file, "is_file", lambda: False)():
            print(f"✅ Found data using importlib.resources: {data_file}")
            return data_file
    except Exception as exc:  # pragma: no cover - informative only
        print(f"⚠️ importlib.resources failed: {exc}")

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
    except Exception as exc:  # pragma: no cover - informative only
        print(f"⚠️ Package-based lookup failed: {exc}")

    return None


def download_data_to_temp() -> Path:
    """Download tourist_places.json to a temporary location and return the path."""

    import urllib.request

    url = os.getenv("TOURIST_PLACES_JSON_URL", DEFAULT_REMOTE_URL)
    target_dir = Path(os.getenv("TMPDIR", "/tmp"))
    target_dir.mkdir(parents=True, exist_ok=True)
    temp_path = target_dir / "tourist_places.json"

    print(f"🌐 Downloading tourist_places.json from {url}")
    with urllib.request.urlopen(url) as response:  # nosec - controlled URL
        if response.status != 200:
            raise RuntimeError(f"Failed to download data: HTTP {response.status}")
        payload = response.read()

    temp_path.write_bytes(payload)
    print(f"✅ Downloaded data to temporary location: {temp_path}")
    return temp_path


def load_places() -> Iterable[dict]:
    """Load place records from disk or remote fallback."""

    data_path = find_data_path()

    if data_path is None:
        print("⚠️ tourist_places.json not found locally; attempting remote download")
        data_path = download_data_to_temp()

    try:
        if hasattr(data_path, "open"):
            with data_path.open(encoding="utf-8") as handle:  # type: ignore[call-arg]
                return json.load(handle)

        with open(data_path, encoding="utf-8") as handle:  # type: ignore[arg-type]
            return json.load(handle)
    except AttributeError:
        # Traversable from importlib.resources does not always expose open()
        with open(str(data_path), encoding="utf-8") as handle:  # type: ignore[arg-type]
            return json.load(handle)


def main():
    try:
        places = load_places()
    except Exception as exc:
        print(f"❌ Error loading data: {exc}")
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
