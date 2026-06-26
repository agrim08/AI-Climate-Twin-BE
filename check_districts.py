import asyncio
from sqlalchemy import text
from app.core.database import create_async_engine
from app.core.config import settings

async def check_districts():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT district_name, state, latitude, longitude FROM districts ORDER BY latitude DESC LIMIT 10"))
        print("Top 10 Northernmost Districts in DB:")
        for r in res:
            print(r)
            
        res = await conn.execute(text("SELECT COUNT(*) FROM districts WHERE state = 'India'"))
        c = res.scalar()
        print(f"\nDistricts with state 'India': {c}")
        
if __name__ == "__main__":
    asyncio.run(check_districts())
