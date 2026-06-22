import asyncio
from sqlalchemy.future import select
from sqlalchemy import func
from app.core.database import engine
from app.models.district import District
from app.models.climate_observation import ClimateObservation
from app.models.forecast import Forecast
from app.models.simulation import SimulationResult

async def test():
    async with engine.connect() as conn:
        print("Connected.")
        
        # Test District count
        try:
            print("Querying District count...")
            res = await conn.scalar(select(func.count(District.id)))
            print(f"District count: {res}")
        except Exception as e:
            print(f"Error District: {e}")
            
        # Test ClimateObservation count
        try:
            print("Querying ClimateObservation count...")
            res = await conn.scalar(select(func.count(ClimateObservation.id)))
            print(f"ClimateObservation count: {res}")
        except Exception as e:
            print(f"Error ClimateObservation: {e}")
            
        # Test Forecast count
        try:
            print("Querying Forecast count...")
            res = await conn.scalar(select(func.count(Forecast.id)))
            print(f"Forecast count: {res}")
        except Exception as e:
            print(f"Error Forecast: {e}")
            
        # Test SimulationResult count
        try:
            print("Querying SimulationResult count...")
            res = await conn.scalar(select(func.count(SimulationResult.id)))
            print(f"SimulationResult count: {res}")
        except Exception as e:
            print(f"Error SimulationResult: {e}")

if __name__ == '__main__':
    asyncio.run(test())
