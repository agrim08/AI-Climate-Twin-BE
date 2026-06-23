import asyncio
from app.core.database import AsyncSessionLocal, engine
from sqlalchemy import text

async def f():
    async with AsyncSessionLocal() as s:
        for table in ['climate_observations', 'districts', 'users', 'climate_records']:
            try:
                res = await s.execute(text(f'select count(*) from {table}'))
                print(f'{table}: {res.scalar()}')
            except Exception as e:
                print(f'{table}: Error: {e}')

if __name__ == '__main__':
    asyncio.run(f())
