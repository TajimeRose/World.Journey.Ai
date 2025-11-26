# seed_places.py
import json
from pathlib import Path

from sqlalchemy import text
from world_journey_ai.db import get_engine  # Fixed import path

DATA_PATH = Path(__file__).parent / "data" / "tourist_places.json"


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
