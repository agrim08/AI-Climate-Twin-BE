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

async def ensure_test_district():
    """Ensures at least one district exists in the database. Creates one if empty."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(District).limit(1))
        district = result.scalar_one_or_none()
        
        if district:
            print(f"Found existing district: {district.district_name} (ID: {district.id})")
            return district.id, False
            
        print("No districts found. Creating temporary test district...")
        new_district = District(
            state="Delhi",
            district_name="New Delhi",
            latitude=28.61,
            longitude=77.20
        )
        session.add(new_district)
        await session.commit()
        await session.refresh(new_district)
        print(f"Created temporary district: {new_district.district_name} (ID: {new_district.id})")
        return new_district.id, True

async def delete_test_district(district_id: int):
    """Deletes the temporary test district."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(District).where(District.id == district_id))
        district = result.scalar_one_or_none()
        if district:
            await session.delete(district)
            await session.commit()
            print(f"Deleted temporary test district ID: {district_id}")

async def test_endpoints(district_id: int):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        print("\n" + "="*50)
        print("TESTING DROUGHT INTELLIGENCE BACKEND ENDPOINTS")
        print("="*50)
        
        # 1. Drought Predict
        payload = {"district_id": district_id, "year": 2024, "month": 6}
        print(f"POST /api/v1/drought/predict with payload: {payload}")
        res = await client.post("/api/v1/drought/predict", json=payload)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 200
        assert "drought_category" in res.json()
        assert "severity_score" in res.json()
        
        # 2. Drought Predict Batch
        payload_batch = [payload, {"district_id": district_id, "year": 2024, "month": 7}]
        print(f"\nPOST /api/v1/drought/predict/batch")
        res = await client.post("/api/v1/drought/predict/batch", json=payload_batch)
        print(f"Status: {res.status_code}")
        assert res.status_code == 200
        assert len(res.json()) == 2
        
        # 3. Drought Simulate
        payload_sim = {"district_id": district_id, "year": 2024, "month": 6, "temperature_delta": 2.5, "rainfall_delta": -15.0}
        print(f"\nPOST /api/v1/drought/simulate with payload: {payload_sim}")
        res = await client.post("/api/v1/drought/simulate", json=payload_sim)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 200
        assert "baseline_category" in res.json()
        assert "scenario_category" in res.json()
        
        # 4. Drought Twin State
        print(f"\nPOST /api/v1/drought/twin-state")
        res = await client.post("/api/v1/drought/twin-state", json=payload)
        print(f"Status: {res.status_code}")
        assert res.status_code == 200
        assert "drought_prediction" in res.json()
        assert "agriculture_intelligence" in res.json()
        
        print("\n" + "="*50)
        print("TESTING EXTREME WEATHER BACKEND ENDPOINTS")
        print("="*50)
        
        # 5. Extreme Weather Predict
        print(f"POST /api/v1/extreme-weather/predict")
        res = await client.post("/api/v1/extreme-weather/predict", json=payload)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 200
        assert "heatwave" in res.json()
        assert "extreme_rainfall" in res.json()
        
        # 6. Extreme Weather Predict Batch
        print(f"\nPOST /api/v1/extreme-weather/predict/batch")
        res = await client.post("/api/v1/extreme-weather/predict/batch", json=payload_batch)
        print(f"Status: {res.status_code}")
        assert res.status_code == 200
        assert len(res.json()) == 2
        
        # 7. Extreme Weather Simulate
        print(f"\nPOST /api/v1/extreme-weather/simulate")
        res = await client.post("/api/v1/extreme-weather/simulate", json=payload_sim)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 200
        assert "baseline_risk" in res.json()
        assert "scenario_risk" in res.json()
        
        # 8. Extreme Weather Twin-State
        print(f"\nPOST /api/v1/extreme-weather/twin-state")
        res = await client.post("/api/v1/extreme-weather/twin-state", json=payload)
        print(f"Status: {res.status_code}")
        assert res.status_code == 200
        assert "overall_extreme_weather" in res.json()
        assert "impact_assessment" in res.json()
        
        print("\n" + "="*50)
        print("ALL INTEGRATION ENDPOINT CHECKS PASSED SUCCESSFULLY!")
        print("="*50)

async def main():
    district_id, created = await ensure_test_district()
    try:
        await test_endpoints(district_id)
    finally:
        if created:
            await delete_test_district(district_id)
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
