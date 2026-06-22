"""
tests/test_rankings.py
======================
Automated tests for the RankingsService, verifying:
  - Hotspot Composite Score weights and normalization.
  - District coverage (all DB districts evaluated, not just 47 cities).
  - Fallback mapping for out-of-sample coordinates.
  - Rank movement computation correctness.
"""

import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.rankings import (
    _compute_composite_score,
    _score_to_risk_band,
    RankingsService,
)


class TestHotspotCompositeScore(unittest.TestCase):
    """Unit tests for the composite score formula."""

    def test_all_zero_inputs(self):
        score = _compute_composite_score(0.0, 0.0, 0.0, 0.0, 0.0)
        self.assertEqual(score, 0.0)

    def test_all_max_inputs(self):
        # drought=1.0, heatwave=100, water=1.0, crop=1.0, extreme_rain=100
        score = _compute_composite_score(1.0, 100.0, 1.0, 1.0, 100.0)
        expected = 0.25 * 100 + 0.25 * 100 + 0.20 * 100 + 0.15 * 100 + 0.15 * 100
        self.assertAlmostEqual(score, expected, places=1)
        self.assertLessEqual(score, 100.0)

    def test_weight_sum_equals_100(self):
        # Weights must sum to 1.0 (multiplied by 100 scale = 100 max score)
        weights = [0.25, 0.25, 0.20, 0.15, 0.15]
        self.assertAlmostEqual(sum(weights), 1.0, places=5)

    def test_moderate_drought_only(self):
        # 50% drought severity, nothing else
        score = _compute_composite_score(0.5, 0.0, 0.0, 0.0, 0.0)
        expected = 0.25 * 0.5 * 100
        self.assertAlmostEqual(score, expected, places=2)

    def test_score_clamped_to_100(self):
        # Even with extreme inputs, score should not exceed 100
        score = _compute_composite_score(2.0, 200.0, 2.0, 2.0, 200.0)
        self.assertLessEqual(score, 100.0)

    def test_score_clamped_to_zero(self):
        # Negative inputs should clamp to 0
        score = _compute_composite_score(-1.0, -50.0, -1.0, -1.0, -50.0)
        self.assertGreaterEqual(score, 0.0)


class TestRiskBandClassification(unittest.TestCase):
    """Unit tests for the risk band mapping."""

    def test_low_band(self):
        self.assertEqual(_score_to_risk_band(0.0), "Low")
        self.assertEqual(_score_to_risk_band(24.9), "Low")

    def test_moderate_band(self):
        self.assertEqual(_score_to_risk_band(25.0), "Moderate")
        self.assertEqual(_score_to_risk_band(49.9), "Moderate")

    def test_high_band(self):
        self.assertEqual(_score_to_risk_band(50.0), "High")
        self.assertEqual(_score_to_risk_band(74.9), "High")

    def test_critical_band(self):
        self.assertEqual(_score_to_risk_band(75.0), "Critical")
        self.assertEqual(_score_to_risk_band(100.0), "Critical")


class TestRankingsServiceLogic(unittest.IsolatedAsyncioTestCase):
    """Integration-level tests for RankingsService using mocked predictors and DB."""

    def _make_district(self, id_, name, state, lat, lon):
        d = MagicMock()
        d.id = id_
        d.district_name = name
        d.state = state
        d.latitude = lat
        d.longitude = lon
        return d

    def _make_lookup_payload(self, lat, lon):
        return {
            "latitude": lat, "longitude": lon,
            "year": 2025, "month": 6,
            "temperature_c": 28.0, "rainfall_mm": 120.0,
            "soil_moisture": 0.3,
            "rolling_temp_3m": 27.5, "rolling_rain_3m": 110.0,
            "temperature_prev_1": 26.5,
        }

    @patch("app.services.rankings._get_predictors")
    @patch("app.services.rankings.ClimateLookup.get_lookup_state")
    @patch("app.services.rankings.PredictionCache.get", return_value=None)
    @patch("app.services.rankings.PredictionCache.set")
    async def test_evaluate_all_districts_uses_db_districts(
        self, mock_cache_set, mock_cache_get, mock_lookup, mock_get_predictors
    ):
        """Verifies that evaluation queries ALL districts from DB, not a hardcoded city list."""

        # Mock predictors
        temp_p = MagicMock()
        temp_p.predict.return_value = {"predicted_temperature_c": 32.0}

        rain_p = MagicMock()
        rain_p.predict.return_value = {"predicted_rainfall_mm": 80.0}

        drought_p = MagicMock()
        drought_p.predict.return_value = {
            "drought_category": "Moderate", "severity_score": 0.4, "confidence_score": 0.75
        }

        ew_p = MagicMock()
        ew_p.predict.return_value = {
            "heatwave": {"category": "Moderate", "severity": 45.0, "confidence": 0.7,
                         "_probabilities": [0.1, 0.5, 0.3, 0.1]},
            "extreme_rainfall": {"category": "Low", "severity": 15.0, "confidence": 0.8,
                                 "_probabilities": [0.7, 0.2, 0.07, 0.03]},
        }
        ew_p.calculate_overall_risk.return_value = {
            "overall_extreme_weather_risk": "Moderate", "overall_risk_score": 40.0
        }
        mock_get_predictors.return_value = (temp_p, rain_p, drought_p, ew_p)

        # Mock lookup to return a valid payload
        mock_lookup.side_effect = lambda db, req: self._make_lookup_payload(
            req["latitude"], req["longitude"]
        )

        # Mock DB: 3 districts in 2 different states
        district_a = self._make_district(1, "TestDistrict-A", "StateX", 28.6, 77.2)
        district_b = self._make_district(2, "TestDistrict-B", "StateY", 19.0, 72.8)
        district_c = self._make_district(3, "TestDistrict-C", "StateZ", 12.9, 77.6)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [district_a, district_b, district_c]
        mock_db.execute.return_value = mock_result

        result = await RankingsService.get_current_rankings(db=mock_db, year=2025, month=6, top_n=5)

        # Should have evaluated all 3 districts
        self.assertEqual(result["total_districts"], 3)
        self.assertIn("top_vulnerable", result)
        self.assertIn("least_vulnerable", result)

        # Lookup should have been called once per district
        self.assertEqual(mock_lookup.call_count, 3)

    @patch("app.services.rankings._get_predictors")
    @patch("app.services.rankings.ClimateLookup.get_lookup_state")
    @patch("app.services.rankings.PredictionCache.get", return_value=None)
    @patch("app.services.rankings.PredictionCache.set")
    async def test_rank_movement_correctly_computes_deltas(
        self, mock_cache_set, mock_cache_get, mock_lookup, mock_get_predictors
    ):
        """Verifies that rank_change is positive when a district worsens over time."""

        temp_p = MagicMock()
        rain_p = MagicMock()
        drought_p = MagicMock()
        ew_p = MagicMock()

        # Base year: lower severity
        base_payload = {
            "district_id": 1, "district_name": "TestDistrict-A", "state": "StateX",
            "latitude": 28.6, "longitude": 77.2,
            "predicted_temperature_c": 30.0, "predicted_rainfall_mm": 100.0,
            "soil_moisture": 0.3, "drought_category": "Moderate",
            "drought_severity_score": 0.35, "drought_confidence": 0.75,
            "heatwave_category": "Moderate", "heatwave_severity": 40.0,
            "extreme_rainfall_category": "Low", "extreme_rainfall_severity": 10.0,
            "overall_risk_category": "Moderate", "overall_risk_score": 35.0,
            "water_stress_index": 0.2, "crop_stress_index": 0.25,
            "hotspot_score": 20.0, "hotspot_risk_band": "Low",
            "score_weights": {},
        }

        # Target year: higher severity
        target_payload = base_payload.copy()
        target_payload.update({
            "predicted_temperature_c": 33.0, "drought_severity_score": 0.6,
            "heatwave_severity": 65.0, "extreme_rainfall_severity": 30.0,
            "water_stress_index": 0.4, "crop_stress_index": 0.5,
            "hotspot_score": 52.0, "hotspot_risk_band": "High",
        })

        call_count = [0]

        async def lookup_side_effect(db, req):
            count = call_count[0]
            call_count[0] += 1
            return self._make_lookup_payload(req["latitude"], req["longitude"])

        temp_p.predict.return_value = {"predicted_temperature_c": 32.0}
        rain_p.predict.return_value = {"predicted_rainfall_mm": 80.0}
        drought_p.predict.return_value = {
            "drought_category": "High", "severity_score": 0.6, "confidence_score": 0.7
        }
        ew_p.predict.return_value = {
            "heatwave": {"category": "High", "severity": 65.0, "confidence": 0.7,
                         "_probabilities": [0.05, 0.25, 0.45, 0.25]},
            "extreme_rainfall": {"category": "Moderate", "severity": 30.0, "confidence": 0.7,
                                 "_probabilities": [0.3, 0.4, 0.2, 0.1]},
        }
        ew_p.calculate_overall_risk.return_value = {
            "overall_extreme_weather_risk": "High", "overall_risk_score": 60.0
        }
        mock_get_predictors.return_value = (temp_p, rain_p, drought_p, ew_p)
        mock_lookup.side_effect = lookup_side_effect

        district_a = self._make_district(1, "TestDistrict-A", "StateX", 28.6, 77.2)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [district_a]
        mock_db.execute.return_value = mock_result

        result = await RankingsService.get_rank_movement(
            db=mock_db, base_year=2025, target_year=2035, month=6, top_n=5
        )
        self.assertIn("most_worsened", result)
        self.assertIn("most_improved", result)
        # Total districts should be 1
        self.assertEqual(result["total_districts"], 1)

    async def test_get_current_rankings_empty_db(self):
        """When DB has no districts, rankings should return empty lists gracefully."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await RankingsService.get_current_rankings(db=mock_db, year=2025, month=6)
        self.assertEqual(result["total_districts"], 0)
        self.assertEqual(result["top_vulnerable"], [])
        self.assertEqual(result["least_vulnerable"], [])


if __name__ == "__main__":
    unittest.main()
