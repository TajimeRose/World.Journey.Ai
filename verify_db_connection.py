import os
from dotenv import load_dotenv
from world_journey_ai.db import init_db, get_db, Place, search_places

# Load environment variables
load_dotenv()

def test_database():
    print("Testing Database Connection...")
    
    # 1. Initialize DB (create tables if not exist)
    try:
        init_db()
        print("[OK] Database initialized/connected.")
    except Exception as e:
        print(f"[ERROR] Could not connect to database: {e}")
        return

    # 2. Insert a test record
    print("\nInserting test data...")
    session_gen = get_db()
    session = next(session_gen)
    
    test_id = "test-place-1"
    try:
        # Check if exists
        existing = session.query(Place).filter(Place.id == test_id).first()
        if not existing:
            new_place = Place(
                id=test_id,
                name="Test Floating Market",
                place_name="Test Floating Market",
                description="A beautiful test market for verification.",
                city="Amphawa",
                province="Samut Songkhram",
                category="attraction",
                rating=5.0
            )
            session.add(new_place)
            session.commit()
            print(f"[OK] Inserted place: {new_place.name}")
        else:
            print(f"[INFO] Place already exists: {existing.name}")
    except Exception as e:
        print(f"[ERROR] Failed to insert data: {e}")
        session.close()
        return

    # 3. Test Search
    print("\nTesting Search Functionality...")
    try:
        results = search_places("Floating")
        print(f"Found {len(results)} results for 'Floating':")
        for place in results:
            print(f" - {place['name']} ({place['city']})")
            
        if any(p['id'] == test_id for p in results):
            print("\nSUCCESS: Retrieved inserted test data!")
        else:
            print("\nFAILED: Could not find the inserted test data.")
            
    except Exception as e:
        print(f"[ERROR] Search failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    test_database()
