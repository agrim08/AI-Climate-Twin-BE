import sys
import os
import unittest
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.ml_services.resolver import ClimateStateResolver
from app.models.district import District
from app.models.climate_observation import ClimateObservation

class TestClimateResolver(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.db = AsyncSessionLocal()

    async def asyncTearDown(self):
        await self.db.close()

    async def test_resolver_historical_default(self):
        # use_live=False should resolve immediately to HISTORICAL
        payload = await ClimateStateResolver.resolve_state(self.db, {
            "latitude": 28.61,
            "longitude": 77.20,
            "year": 2024,
            "month": 6,
            "use_live": False
        })
        self.assertEqual(payload["source"], "HISTORICAL")
        self.assertEqual(payload["confidence_source"], 0.5)
        self.assertIn("2024-06-01", payload["last_updated"])

    async def test_resolver_live_or_database(self):
        # Get a valid district from database
        result = await self.db.execute(select(District).limit(1))
        district = result.scalar_one_or_none()
        
        if district:
            # Test database resolution or live resolution
            payload = await ClimateStateResolver.resolve_state(self.db, {
                "district_id": district.id,
                "year": 2024,
                "month": 6,
                "use_live": True
            })
            # It should be either LIVE or DATABASE or HISTORICAL depending on network and seeded database observations
            self.assertIn(payload["source"], ["LIVE", "DATABASE", "HISTORICAL"])
            self.assertIn("confidence_source", payload)
            self.assertIn("last_updated", payload)

if __name__ == "__main__":
    unittest.main()
