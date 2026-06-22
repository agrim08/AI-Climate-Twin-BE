import sys
import os
import unittest
import pandas as pd

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.ml_services.lookup import ClimateLookup

class TestLookupEngine(unittest.IsolatedAsyncioTestCase):
    
    @classmethod
    def setUpClass(cls):
        # Initialize lookup engine (loads CSV once)
        ClimateLookup.initialize()

    async def test_lookup_exact_match(self):
        # Delhi June 2024 (should exist in dataset)
        payload = await ClimateLookup.get_lookup_state(None, {
            "latitude": 28.61,
            "longitude": 77.20,
            "year": 2024,
            "month": 6
        })
        self.assertEqual(payload["city"], "Delhi")
        self.assertEqual(payload["year"], 2024)
        self.assertEqual(payload["month"], 6)
        # Check that lag/rolling features are populated
        self.assertIn("rolling_temp_3m", payload)
        self.assertGreater(payload["rolling_temp_3m"], 0.0)

    async def test_lookup_future_2026(self):
        # 2026 projections
        payload = await ClimateLookup.get_lookup_state(None, {
            "latitude": 28.61,
            "longitude": 77.20,
            "year": 2026,
            "month": 6
        })
        self.assertEqual(payload["city"], "Delhi")
        self.assertEqual(payload["year"], 2026)
        self.assertEqual(payload["month"], 6)
        # Verify lag features are non-zero (pulled from 2025 fallback)
        self.assertGreater(payload["rolling_temp_3m"], 0.0)

    async def test_lookup_future_2030(self):
        # 2030 projections
        payload = await ClimateLookup.get_lookup_state(None, {
            "latitude": 28.61,
            "longitude": 77.20,
            "year": 2030,
            "month": 6
        })
        self.assertEqual(payload["city"], "Delhi")
        self.assertEqual(payload["year"], 2030)
        self.assertEqual(payload["month"], 6)
        self.assertGreater(payload["rolling_temp_3m"], 0.0)

    async def test_lookup_december_projection(self):
        # December projections (historically missing for max year 2025, should fallback to 2024)
        payload = await ClimateLookup.get_lookup_state(None, {
            "city": "Itanagar",
            "latitude": 27.08,
            "longitude": 93.60,
            "year": 2025,
            "month": 12
        })
        # Check that it resolved to Itanagar
        self.assertEqual(payload["city"], "Itanagar")
        self.assertEqual(payload["month"], 12)
        # Lags/rolling must not default to 0.0 because of missing month 12
        self.assertGreater(payload.get("temperature_prev_1", 0.0), 0.0)
        self.assertGreater(payload.get("rolling_temp_3m", 0.0), 0.0)

    async def test_lookup_missing_historical_months(self):
        # Try a completely missing month or out of bounds query (e.g. month 13, which is invalid but should resolve closest)
        payload = await ClimateLookup.get_lookup_state(None, {
            "city": "Itanagar",
            "latitude": 27.08,
            "longitude": 93.60,
            "year": 2025,
            "month": 13
        })
        self.assertEqual(payload["city"], "Itanagar")
        self.assertGreater(payload.get("temperature_prev_1", 0.0), 0.0)

if __name__ == "__main__":
    unittest.main()
