import asyncio
import sys
from sqlalchemy.sql import text
from app.core.database import engine

async def test_connection():
    print("Attempting to connect to database...")
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            value = result.scalar()
            print(f"Connection Successful! Database response: {value}")
            return True
    except Exception as e:
        print(f"Connection Failed: {e}", file=sys.stderr)
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
