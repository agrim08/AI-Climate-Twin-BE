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
    """Ensures at least one district exists. Creates it if empty."""
    district_id = None
    district_created = False
    
    async with AsyncSessionLocal() as session:
        dist_res = await session.execute(select(District).limit(1))
        district = dist_res.scalar_one_or_none()
        if district:
            district_id = district.id
            print(f"Found existing district: {district.district_name} (ID: {district.id})")
        else:
            print("No districts found. Creating temporary test district...")
            new_district = District(
                state="Maharashtra",
                district_name="Pune",
                latitude=18.52,
                longitude=73.85
            )
            session.add(new_district)
            await session.commit()
            await session.refresh(new_district)
            district_id = new_district.id
            district_created = True
            print(f"Created temporary district: {new_district.district_name} (ID: {new_district.id})")
            
    return district_id, district_created

async def cleanup_database(district_id: int, district_created: bool):
    """Cleans up temporary resources."""
    if district_created:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(District).where(District.id == district_id))
            district = result.scalar_one_or_none()
            if district:
                await session.delete(district)
                print(f"Cleaned up temporary district ID: {district_id}")
            await session.commit()

async def test_endpoints(district_id: int):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        print("\n" + "="*50)
        print("TESTING BASE TEMPERATURE ENDPOINTS")
        print("="*50)
        
        # 1. Single Temperature Predict
        payload = {"district_id": district_id, "year": 2026, "month": 6}
        print(f"POST /api/v1/temperature/predict with payload: {payload}")
        res = await client.post("/api/v1/temperature/predict", json=payload)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 200
        assert "predicted_temperature_c" in res.json()
        assert "confidence" in res.json()
        assert "model_rmse_c" in res.json()
        
        # 2. Batch Temperature Predict
        batch_payload = [
            {"district_id": district_id, "year": 2026, "month": 6},
            {"district_id": district_id, "year": 2026, "month": 7}
        ]
        print(f"\nPOST /api/v1/temperature/predict/batch with payload: {batch_payload}")
        res = await client.post("/api/v1/temperature/predict/batch", json=batch_payload)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 200
        assert len(res.json()) == 2
        assert "predicted_temperature_c" in res.json()[0]

        print("\n" + "="*50)
        print("TESTING BASE RAINFALL ENDPOINTS")
        print("="*50)
        
        # 3. Single Rainfall Predict
        payload_rain = {"district_id": district_id, "year": 2026, "month": 7}
        print(f"POST /api/v1/rainfall/predict with payload: {payload_rain}")
        res = await client.post("/api/v1/rainfall/predict", json=payload_rain)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 200
        assert "predicted_rainfall_mm" in res.json()
        assert "confidence" in res.json()
        assert "confidence_score" in res.json()
        assert "monsoon_status" in res.json()
        
        # 4. Batch Rainfall Predict
        batch_payload_rain = [
            {"district_id": district_id, "year": 2026, "month": 7},
            {"district_id": district_id, "year": 2026, "month": 8}
        ]
        print(f"\nPOST /api/v1/rainfall/predict/batch with payload: {batch_payload_rain}")
        res = await client.post("/api/v1/rainfall/predict/batch", json=batch_payload_rain)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 200
        assert len(res.json()) == 2
        assert "predicted_rainfall_mm" in res.json()[0]
        
        print("\n" + "="*50)
        print("GAP 4 BASE ENDPOINT CHECKS COMPLETED SUCCESSFULLY!")
        print("="*50)

async def main():
    district_id, district_created = await ensure_test_district()
    try:
        await test_endpoints(district_id)
    finally:
        await cleanup_database(district_id, district_created)
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
