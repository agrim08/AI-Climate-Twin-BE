import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def reset_db():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL)
    async with engine.begin() as conn:
        print("Truncating districts, cascading to observations, forecasts, and simulation_results...")
        # In PostgreSQL, TRUNCATE with CASCADE clears everything fast. 
        # If SQLite, DELETE FROM districts works since CASCADE is defined in relationships
        if "sqlite" in settings.ASYNC_DATABASE_URL:
            await conn.execute(text("DELETE FROM districts;"))
        else:
            await conn.execute(text("TRUNCATE TABLE districts CASCADE;"))
        print("Database truncated successfully.")

if __name__ == "__main__":
    asyncio.run(reset_db())
