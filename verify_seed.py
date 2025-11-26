from world_journey_ai.db import get_engine
from sqlalchemy import text

engine = get_engine()

with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) as count FROM tourist_places'))
    count = result.fetchone()[0]
    print(f'✅ Total tourist_places: {count}')
    
    result = conn.execute(text('SELECT id, name_th, rating, tags FROM tourist_places LIMIT 5'))
    print('\n📍 First 5 records:')
    for r in result:
        tags = r.tags if r.tags else []
        print(f'  {r.id}. {r.name_th} (Rating: {r.rating})')
        print(f'     Tags: {", ".join(tags) if tags else "No tags"}')
