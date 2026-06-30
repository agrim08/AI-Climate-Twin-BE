import os
import sys
import asyncio
import uuid
from datetime import date
import httpx

# Ensure app directory is in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.main import app
from app.core.database import AsyncSessionLocal, engine
from app.models.district import District
from app.models.user import User, UserRole
from app.core.auth import get_current_user
from sqlalchemy.future import select

# Global placeholder for the active test user
active_test_user = None

async def override_get_current_user():
    return active_test_user

app.dependency_overrides[get_current_user] = override_get_current_user

async def ensure_test_user_and_district():
    """Ensures at least one district and one user exist. Creates them if empty."""
    global active_test_user
    district_id = None
    district_created = False
    user_created = False
    
    async with AsyncSessionLocal() as session:
        # 1. Ensure User
        user_res = await session.execute(select(User).limit(1))
        db_user = user_res.scalar_one_or_none()
        if db_user:
            active_test_user = db_user
            print(f"Found existing user for auth: {db_user.email} (ID: {db_user.id})")
        else:
            print("No users found. Creating temporary test user...")
            active_test_user = User(
                id=uuid.uuid4(),
                email="integration_admin@example.com",
                full_name="Integration Test Admin",
                role=UserRole.ADMIN
            )
            session.add(active_test_user)
            await session.commit()
            await session.refresh(active_test_user)
            user_created = True
            print(f"Created temporary user: {active_test_user.email} (ID: {active_test_user.id})")
            
        # 2. Ensure District
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
            
    return district_id, district_created, user_created

async def cleanup_database(district_id: int, district_created: bool, user_created: bool):
    """Cleans up temporary resources."""
    async with AsyncSessionLocal() as session:
        if district_created:
            result = await session.execute(select(District).where(District.id == district_id))
            district = result.scalar_one_or_none()
            if district:
                await session.delete(district)
                print(f"Cleaned up temporary district ID: {district_id}")
                
        if user_created and active_test_user:
            result = await session.execute(select(User).where(User.id == active_test_user.id))
            db_user = result.scalar_one_or_none()
            if db_user:
                await session.delete(db_user)
                print(f"Cleaned up temporary user: {db_user.email}")
                
        await session.commit()

async def test_endpoints(district_id: int):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        print("\n" + "="*50)
        print("TESTING ML FORECAST GENERATION ENDPOINTS")
        print("="*50)
        
        # 1. Single Forecast Generate
        payload = {"district_id": district_id, "target_date": "2024-06-15"}
        print(f"POST /api/v1/forecasts/generate with payload: {payload}")
        res = await client.post("/api/v1/forecasts/generate", json=payload)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 201
        assert "predicted_rainfall" in res.json()
        assert "predicted_temperature" in res.json()
        
        # 2. 7-Day Forecast Generate
        print(f"\nPOST /api/v1/forecasts/generate/{district_id}")
        res = await client.post(f"/api/v1/forecasts/generate/{district_id}")
        print(f"Status: {res.status_code}")
        print(f"Response size: {len(res.json())} forecasts")
        assert res.status_code == 201
        assert len(res.json()) == 7
        assert "predicted_rainfall" in res.json()[0]
        
        print("\n" + "="*50)
        print("TESTING ML SIMULATION RESULTS ENDPOINTS")
        print("="*50)
        
        # 3. Custom Delta Simulation
        sim_payload = {
            "district_id": district_id,
            "rainfall_change": -10.0,
            "temperature_change": 2.0,
            "humidity_change": -5.0
        }
        print(f"POST /api/v1/simulations/run with payload: {sim_payload}")
        res = await client.post("/api/v1/simulations/run", json=sim_payload)
        print(f"Status: {res.status_code}")
        print(f"Response Projections: {res.json().get('result_json', {}).get('projections')}")
        print(f"Response Impacts: {res.json().get('result_json', {}).get('impacts')}")
        assert res.status_code == 201
        assert "baseline" in res.json()["result_json"]
        assert "projections" in res.json()["result_json"]
        assert "impacts" in res.json()["result_json"]
        
        # 4. Predefined Scenario Simulation
        scenario_payload = {
            "scenario": "temperature_plus_2"
        }
        print(f"\nPOST /api/v1/simulations/run/{district_id} with payload: {scenario_payload}")
        res = await client.post(f"/api/v1/simulations/run/{district_id}", json=scenario_payload)
        print(f"Status: {res.status_code}")
        print(f"Response Projections: {res.json().get('result_json', {}).get('projections')}")
        assert res.status_code == 201
        assert res.json()["temperature_change"] == 2.0
        
        print("\n" + "="*50)
        print("GAP 2 BACKEND ENDPOINT CHECKS COMPLETED SUCCESSFULLY!")
        print("="*50)

async def main():
    district_id, district_created, user_created = await ensure_test_user_and_district()
    try:
        await test_endpoints(district_id)
    finally:
        await cleanup_database(district_id, district_created, user_created)
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
