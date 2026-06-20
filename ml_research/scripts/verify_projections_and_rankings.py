import os
import sys
import asyncio
import httpx

# Ensure app directory is in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.main import app
from app.core.database import AsyncSessionLocal, engine
from app.models.district import District
from sqlalchemy.future import select

async def get_test_district_id():
    async with AsyncSessionLocal() as session:
        dist_res = await session.execute(select(District).limit(1))
        district = dist_res.scalar_one_or_none()
        if not district:
            print("No districts found! Please run seed_database.py first.")
            sys.exit(1)
        return district.id, district.district_name, district.state

async def test_rankings_and_projections(district_id: int, district_name: str, state_name: str):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        print("\n" + "="*60)
        print("TESTING DYNAMIC DISTRICT RANKINGS")
        print("="*60)
        
        # 1. Hottest districts overall
        print("GET /api/v1/analytics/rankings?metric=hottest&limit=5")
        res = await client.get("/api/v1/analytics/rankings?metric=hottest&limit=5")
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}\n")
        assert res.status_code == 200
        assert len(res.json()) <= 5
        assert res.json()[0]["value"] >= res.json()[-1]["value"]
        
        # 2. Driest districts in Maharashtra
        print("GET /api/v1/analytics/rankings?metric=driest&state=Maharashtra&limit=3")
        res = await client.get("/api/v1/analytics/rankings?metric=driest&state=Maharashtra&limit=3")
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}\n")
        assert res.status_code == 200
        assert len(res.json()) <= 3
        # driest should be ascending order of rainfall
        assert res.json()[0]["value"] <= res.json()[-1]["value"]

        print("\n" + "="*60)
        print("TESTING DYNAMIC ML TIME TIMELINE PROJECTIONS & SCENARIOS")
        print("="*60)
        
        # 3. 1-year monthly timeline projection
        print(f"GET /api/v1/forecasts/projections/{district_id}?timeframe=1year")
        res = await client.get(f"/api/v1/forecasts/projections/{district_id}?timeframe=1year")
        print(f"Status: {res.status_code}")
        print(f"Response size: {len(res.json())} months")
        print(f"First Month Outlook: {res.json()[0]}")
        assert res.status_code == 200
        assert len(res.json()) == 12
        assert "predicted_temperature_c" in res.json()[0]
        assert "drought_category" in res.json()[0]
        assert "extreme_weather_risk" in res.json()[0]

        # 4. Future Year (2030) Simulation with delta (+2.0C temperature anomaly)
        print(f"\nGET /api/v1/forecasts/projections/{district_id}?timeframe=2030&temperature_delta=2.0")
        res = await client.get(f"/api/v1/forecasts/projections/{district_id}?timeframe=2030&temperature_delta=2.0")
        print(f"Status: {res.status_code}")
        print(f"Response size: {len(res.json())} months")
        print(f"2030 June Outlook: {res.json()[5]}") # June is index 5
        assert res.status_code == 200
        assert len(res.json()) == 12
        
        # 5. Future Year (2050) Low Confidence warning check (year > 2040 should lower confidence)
        print(f"\nGET /api/v1/forecasts/projections/{district_id}?timeframe=2050")
        res = await client.get(f"/api/v1/forecasts/projections/{district_id}?timeframe=2050")
        print(f"Status: {res.status_code}")
        print(f"2050 June Temperature Confidence: {res.json()[5]['temperature_confidence']}")
        print(f"2050 June Rainfall Confidence: {res.json()[5]['rainfall_confidence']}")
        assert res.status_code == 200
        # Confidence should be low due to long-term extrapolation
        assert res.json()[5]['temperature_confidence'].lower() == "low"
        
        print("\n" + "="*60)
        print("ALL NEW PROJECTIONS & RANKINGS CHECKS COMPLETED SUCCESSFULLY!")
        print("="*60)

async def main():
    dist_id, dist_name, state_name = await get_test_district_id()
    try:
        await test_rankings_and_projections(dist_id, dist_name, state_name)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
