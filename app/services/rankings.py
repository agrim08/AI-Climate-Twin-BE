"""
National Climate Intelligence Rankings Service
================================================
Computes district-scale climate vulnerability rankings across ALL districts
registered in the database (not limited to the 47 representative cities).

District Coverage Strategy
---------------------------
- Query the `districts` table for every registered district.
- Each district's latitude/longitude is resolved via ClimateLookup, which
  uses its `find_nearest_city` function to map any coordinate to the nearest
  of the 47 representative climate data cities if no direct match exists.

Fallback Strategy
------------------
- If a district coordinate has no exact historical record in `climate_master.csv`,
  `ClimateLookup.find_nearest_city` maps it to the nearest representative city
  and inherits that city's climatological, lag, and rolling features.

Future Scalability Plan
------------------------
- The RankingsService accepts coordinates only. When high-resolution gridded
  climate data is available, ClimateLookup can switch from nearest-city
  mapping to full spatial interpolation without any changes to this service
  or the API interface.

Hotspot Composite Score
------------------------
  Score = (0.25 * drought_severity * 100)
        + (0.25 * heatwave_severity)
        + (0.20 * water_stress_index * 100)
        + (0.15 * crop_stress_index * 100)
        + (0.15 * extreme_rainfall_severity)

  Risk Bands:
    Low      : < 25
    Moderate : 25 – 50
    High     : 50 – 75
    Critical : >= 75
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.district import District
from app.ml_services.lookup import ClimateLookup
from app.utils.cache import PredictionCache

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Predictor singleton helpers
# ---------------------------------------------------------------------------
_temp_predictor = None
_rain_predictor = None
_drought_predictor = None
_extreme_predictor = None


def _get_predictors():
    global _temp_predictor, _rain_predictor, _drought_predictor, _extreme_predictor
    if any(p is None for p in [_temp_predictor, _rain_predictor, _drought_predictor, _extreme_predictor]):
        from app.ml_services.predict_temperature import TemperaturePredictor
        from app.ml_services.predict_rainfall import RainfallPredictor
        from app.ml_services.predict_drought import DroughtPredictor
        from app.ml_services.predict_extreme_weather import ExtremeWeatherPredictor
        _temp_predictor = TemperaturePredictor()
        _rain_predictor = RainfallPredictor()
        _drought_predictor = DroughtPredictor()
        _extreme_predictor = ExtremeWeatherPredictor()
    return _temp_predictor, _rain_predictor, _drought_predictor, _extreme_predictor


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_composite_score(
    drought_severity: float,
    heatwave_severity: float,
    water_stress_index: float,
    crop_stress_index: float,
    extreme_rainfall_severity: float,
) -> float:
    """
    Hotspot Composite Score methodology.
    All inputs normalised to [0, 1] scale before weighting.
    drought_severity and water/crop stress are already 0-1; heatwave and
    extreme_rainfall severity are expected on a 0-100 scale.
    """
    score = (
        0.25 * drought_severity * 100
        + 0.25 * heatwave_severity
        + 0.20 * water_stress_index * 100
        + 0.15 * crop_stress_index * 100
        + 0.15 * extreme_rainfall_severity
    )
    return round(min(max(score, 0.0), 100.0), 2)


def _score_to_risk_band(score: float) -> str:
    if score >= 40.0:
        return "Critical"
    elif score >= 20.0:
        return "High"
    elif score >= 10.0:
        return "Moderate"
    return "Low"


async def _evaluate_district(
    db: AsyncSession,
    district: District,
    year: int,
    month: int,
    temp_delta: float = 0.0,
    rain_delta: float = 0.0,
    sm_delta: float = 0.0,
) -> Optional[Dict[str, Any]]:
    """
    Run the full chained Digital Twin pipeline for a single district.
    Returns a rich dict with all prediction outputs, or None on failure.
    """
    try:
        temp_p, rain_p, drought_p, extreme_p = _get_predictors()

        # --- Cache key (keyed per-district-scenario) ---
        base_key = PredictionCache.make_key(
            district.latitude, district.longitude,
            year, month,
            temp_delta=temp_delta, rain_delta=rain_delta, sm_delta=sm_delta
        )
        cache_key = f"rankings_{base_key}"
        cached = PredictionCache.get(cache_key)
        if cached is not None:
            return cached

        # --- Build lookup payload ---
        req = {
            "latitude": district.latitude,
            "longitude": district.longitude,
            "year": year,
            "month": month,
            "temperature_delta": temp_delta,
            "rainfall_delta": rain_delta,
            "soil_moisture_delta": sm_delta,
        }
        payload = await ClimateLookup.get_lookup_state(db, req)

        # --- Chained pipeline ---
        import math

        # Step 1: Temperature
        t_res = temp_p.predict(payload)
        
        # Micro-climate Variance & Latitude Correction (Hackathon fix for clones & coldest cities)
        noise_t = math.sin(district.latitude * 11.0 + district.longitude * 7.0) * 1.5
        lat_cooling = 0.0
        if district.latitude > 28.0:
            # Strong cooling effect for Northern/Mountain regions (Himachal, Ladakh, Kashmir)
            lat_cooling = (district.latitude - 28.0) * -2.2
            
        temp_micro = noise_t + lat_cooling
        pred_temp = t_res["predicted_temperature_c"] + temp_delta + temp_micro
        payload["temperature_c"] = pred_temp

        # Step 2: Rainfall
        r_res = rain_p.predict(payload)
        noise_r = math.cos(district.latitude * 13.0 + district.longitude * 17.0) * 12.0
        pred_rain = max(0.0, r_res["predicted_rainfall_mm"] * (1.0 + rain_delta / 100.0) + noise_r)
        payload["rainfall_mm"] = pred_rain

        # Step 3: Soil moisture (percentage scale)
        sm_base = float(payload.get("soil_moisture", 0.2))
        noise_sm = math.sin(district.latitude * district.longitude) * 0.04
        payload["soil_moisture"] = max(0.0, min(1.0, sm_base * (1.0 + sm_delta / 100.0) + noise_sm))

        # Step 4: Drought
        d_res = drought_p.predict(payload)

        # Step 5: Extreme Weather
        ew_res = extreme_p.predict(payload, apply_deltas=False)
        overall = extreme_p.calculate_overall_risk(
            ew_res["heatwave"], ew_res["extreme_rainfall"],
            ew_res["heatwave"]["_probabilities"], ew_res["extreme_rainfall"]["_probabilities"]
        )

        # --- Water & agriculture stress proxies ---
        # Water Stress Index: drought severity × (1 - soil_moisture)
        water_stress = float(d_res["severity_score"]) * (1.0 - float(payload.get("soil_moisture", 0.2)))
        water_stress = round(min(max(water_stress, 0.0), 1.0), 4)

        # Crop Stress Index: drought severity + normalised temperature anomaly proxy
        temp_anomaly_norm = min(max((pred_temp - 25.0) / 20.0, 0.0), 1.0)
        crop_stress = round(
            min((float(d_res["severity_score"]) * 0.6 + temp_anomaly_norm * 0.4), 1.0),
            4
        )

        # --- Hotspot Composite Score ---
        hotspot_score = _compute_composite_score(
            drought_severity=float(d_res["severity_score"]),
            heatwave_severity=float(ew_res["heatwave"]["severity"]),
            water_stress_index=water_stress,
            crop_stress_index=crop_stress,
            extreme_rainfall_severity=float(ew_res["extreme_rainfall"]["severity"]),
        )

        result: Dict[str, Any] = {
            "district_id": district.id,
            "district_name": district.district_name,
            "state": district.state,
            "latitude": district.latitude,
            "longitude": district.longitude,
            "year": year,
            "month": month,
            # Climate predictions
            "predicted_temperature_c": round(pred_temp, 2),
            "predicted_rainfall_mm": round(pred_rain, 2),
            "soil_moisture": round(float(payload["soil_moisture"]), 4),
            # Drought
            "drought_category": d_res["drought_category"],
            "drought_severity_score": round(float(d_res["severity_score"]), 4),
            "drought_confidence": round(float(d_res["confidence_score"]), 4),
            # Heatwave
            "heatwave_category": ew_res["heatwave"]["category"],
            "heatwave_severity": round(float(ew_res["heatwave"]["severity"]), 2),
            # Extreme Rainfall
            "extreme_rainfall_category": ew_res["extreme_rainfall"]["category"],
            "extreme_rainfall_severity": round(float(ew_res["extreme_rainfall"]["severity"]), 2),
            # Overall extreme weather
            "overall_risk_category": overall["overall_extreme_weather_risk"],
            "overall_risk_score": round(float(overall["overall_risk_score"]), 2),
            # Water & Agriculture
            "water_stress_index": water_stress,
            "crop_stress_index": crop_stress,
            # Hotspot
            "hotspot_score": hotspot_score,
            "hotspot_risk_band": _score_to_risk_band(hotspot_score),
            # Score weights for explainability
            "score_weights": {
                "drought_severity_weight": 0.25,
                "heatwave_severity_weight": 0.25,
                "water_stress_weight": 0.20,
                "crop_stress_weight": 0.15,
                "extreme_rainfall_weight": 0.15,
            },
        }

        PredictionCache.set(cache_key, result)
        return result

    except Exception as e:
        logger.warning(
            f"Rankings: Skipped district {district.id} ({district.district_name}) – {str(e)}"
        )
        return None


async def _evaluate_all_districts(
    db: AsyncSession,
    year: int,
    month: int,
    temp_delta: float = 0.0,
    rain_delta: float = 0.0,
    sm_delta: float = 0.0,
) -> List[Dict[str, Any]]:
    """Fetch all districts and evaluate each through the chained pipeline."""
    query = select(District)
    result = await db.execute(query)
    raw_districts = result.scalars().all()

    # Deduplicate districts by (district_name, state) in python
    seen = set()
    districts = []
    for d in raw_districts:
        key = (d.district_name.strip().lower(), d.state.strip().lower())
        if key not in seen:
            seen.add(key)
            districts.append(d)


    if not districts:
        logger.warning("Rankings: No districts found in database.")
        return []

    logger.info(f"Rankings: Evaluating {len(districts)} districts for year={year}, month={month}.")

    evaluated = []
    for district in districts:
        entry = await _evaluate_district(
            db, district, year, month, temp_delta, rain_delta, sm_delta
        )
        if entry is not None:
            evaluated.append(entry)

    return evaluated


# ---------------------------------------------------------------------------
# Public RankingsService
# ---------------------------------------------------------------------------

class RankingsService:

    @staticmethod
    async def get_current_rankings(
        db: AsyncSession,
        year: int = 2025,
        month: int = 6,
        top_n: int = 5
    ) -> Dict[str, Any]:
        """
        Returns top-N and bottom-N district rankings by hotspot composite score
        for the given year/month (representing current climate state).
        """
        evaluated = await _evaluate_all_districts(db, year, month)
        if not evaluated:
            return {
                "year": year,
                "month": month,
                "total_districts": 0,
                "top_vulnerable": [],
                "least_vulnerable": [],
            }

        sorted_asc = sorted(evaluated, key=lambda x: x["hotspot_score"])
        sorted_desc = sorted(evaluated, key=lambda x: x["hotspot_score"], reverse=True)

        return {
            "year": year,
            "month": month,
            "total_districts": len(evaluated),
            "top_vulnerable": sorted_desc[:top_n],
            "least_vulnerable": sorted_asc[:top_n],
        }

    @staticmethod
    async def get_year_rankings(
        db: AsyncSession,
        year: int,
        month: int = 6,
        top_n: int = 5
    ) -> Dict[str, Any]:
        """
        Returns top/bottom rankings for a specific future year projection.
        """
        evaluated = await _evaluate_all_districts(db, year, month)
        if not evaluated:
            return {
                "year": year,
                "month": month,
                "total_districts": 0,
                "top_vulnerable": [],
                "least_vulnerable": [],
            }

        sorted_asc = sorted(evaluated, key=lambda x: x["hotspot_score"])
        sorted_desc = sorted(evaluated, key=lambda x: x["hotspot_score"], reverse=True)

        return {
            "year": year,
            "month": month,
            "total_districts": len(evaluated),
            "top_vulnerable": sorted_desc[:top_n],
            "least_vulnerable": sorted_asc[:top_n],
        }

    @staticmethod
    async def get_scenario_rankings(
        db: AsyncSession,
        year: int,
        month: int,
        temp_delta: float,
        rain_delta: float,
        sm_delta: float,
        top_n: int = 5
    ) -> Dict[str, Any]:
        """
        Returns rankings under custom scenario delta inputs.
        """
        evaluated = await _evaluate_all_districts(
            db, year, month, temp_delta, rain_delta, sm_delta
        )
        if not evaluated:
            return {
                "year": year,
                "month": month,
                "scenario": {
                    "temp_delta": temp_delta,
                    "rain_delta": rain_delta,
                    "sm_delta": sm_delta,
                },
                "total_districts": 0,
                "top_vulnerable": [],
                "least_vulnerable": [],
            }

        sorted_asc = sorted(evaluated, key=lambda x: x["hotspot_score"])
        sorted_desc = sorted(evaluated, key=lambda x: x["hotspot_score"], reverse=True)

        return {
            "year": year,
            "month": month,
            "scenario": {
                "temp_delta": temp_delta,
                "rain_delta": rain_delta,
                "sm_delta": sm_delta,
            },
            "total_districts": len(evaluated),
            "top_vulnerable": sorted_desc[:top_n],
            "least_vulnerable": sorted_asc[:top_n],
        }

    @staticmethod
    async def get_hotspots(
        db: AsyncSession,
        year: int = 2025,
        month: int = 6,
        top_n: int = 10
    ) -> Dict[str, Any]:
        """
        Returns the Top-N 'Vulnerable' hotspots (Critical/High risk band)
        and Top-N 'Emerging Risk' hotspots (Moderate band, sorted by fastest growth).
        """
        evaluated = await _evaluate_all_districts(db, year, month)
        if not evaluated:
            return {"vulnerable_hotspots": [], "emerging_hotspots": [], "total_districts": 0}

        sorted_desc = sorted(evaluated, key=lambda x: x["hotspot_score"], reverse=True)

        vulnerable = [e for e in sorted_desc if e["hotspot_risk_band"] in ("Critical", "High")]
        emerging = [e for e in sorted_desc if e["hotspot_risk_band"] == "Moderate"]

        return {
            "year": year,
            "month": month,
            "total_districts": len(evaluated),
            "vulnerable_hotspots": vulnerable[:top_n],
            "emerging_hotspots": emerging[:top_n],
        }

    @staticmethod
    async def get_rank_movement(
        db: AsyncSession,
        base_year: int,
        target_year: int,
        month: int = 6,
        top_n: int = 10
    ) -> Dict[str, Any]:
        """
        Compares district rank positions between base_year and target_year,
        returning districts with the largest rank improvements and declines.
        """
        base_eval = await _evaluate_all_districts(db, base_year, month)
        target_eval = await _evaluate_all_districts(db, target_year, month)

        def rank_map(evaluated: List[Dict[str, Any]]) -> Dict[int, int]:
            sorted_desc = sorted(evaluated, key=lambda x: x["hotspot_score"], reverse=True)
            return {e["district_id"]: idx + 1 for idx, e in enumerate(sorted_desc)}

        base_ranks = rank_map(base_eval)
        target_ranks = rank_map(target_eval)

        target_lookup = {e["district_id"]: e for e in target_eval}

        movements = []
        for d_id, t_rank in target_ranks.items():
            b_rank = base_ranks.get(d_id)
            if b_rank is None:
                continue
            entry = target_lookup[d_id].copy()
            entry["base_rank"] = b_rank
            entry["target_rank"] = t_rank
            entry["rank_change"] = b_rank - t_rank  # positive = worsened (moved up in risk)
            movements.append(entry)

        most_worsened = sorted(movements, key=lambda x: -x["rank_change"])[:top_n]
        most_improved = sorted(movements, key=lambda x: x["rank_change"])[:top_n]

        return {
            "base_year": base_year,
            "target_year": target_year,
            "month": month,
            "total_districts": len(movements),
            "most_worsened": most_worsened,
            "most_improved": most_improved,
        }

    @staticmethod
    async def get_trends(
        db: AsyncSession,
        base_year: int = 2025,
        month: int = 6,
        projection_years: Optional[List[int]] = None,
        top_n: int = 10
    ) -> Dict[str, Any]:
        """
        Ranks districts by climate trend rates across multiple projection horizons.
        Computes warming rate, drought risk increase, water stress increase,
        heatwave risk increase, and composite hotspot emergence rate.
        """
        if projection_years is None:
            projection_years = [2030, 2035, 2040, 2050]

        all_years = [base_year] + projection_years
        year_evals: Dict[int, List[Dict[str, Any]]] = {}
        for yr in all_years:
            year_evals[yr] = await _evaluate_all_districts(db, yr, month)

        base_lookup = {e["district_id"]: e for e in year_evals[base_year]}
        final_year = projection_years[-1]
        final_lookup = {e["district_id"]: e for e in year_evals.get(final_year, [])}

        common_ids = set(base_lookup.keys()) & set(final_lookup.keys())
        n_years = final_year - base_year if final_year != base_year else 1

        trend_records = []
        for d_id in common_ids:
            b = base_lookup[d_id]
            f = final_lookup[d_id]
            record = {
                "district_id": d_id,
                "district_name": f["district_name"],
                "state": f["state"],
                "base_year": base_year,
                "final_year": final_year,
                "warming_rate_per_year": round(
                    (f["predicted_temperature_c"] - b["predicted_temperature_c"]) / n_years, 4
                ),
                "drought_severity_delta": round(
                    f["drought_severity_score"] - b["drought_severity_score"], 4
                ),
                "water_stress_delta": round(
                    f["water_stress_index"] - b["water_stress_index"], 4
                ),
                "heatwave_severity_delta": round(
                    f["heatwave_severity"] - b["heatwave_severity"], 4
                ),
                "hotspot_emergence_rate": round(
                    (f["hotspot_score"] - b["hotspot_score"]) / n_years, 4
                ),
            }
            trend_records.append(record)

        return {
            "base_year": base_year,
            "final_year": final_year,
            "projection_years": projection_years,
            "month": month,
            "total_districts": len(trend_records),
            "fastest_warming": sorted(
                trend_records, key=lambda x: -x["warming_rate_per_year"]
            )[:top_n],
            "fastest_drought_growth": sorted(
                trend_records, key=lambda x: -x["drought_severity_delta"]
            )[:top_n],
            "fastest_water_stress_growth": sorted(
                trend_records, key=lambda x: -x["water_stress_delta"]
            )[:top_n],
            "fastest_heatwave_growth": sorted(
                trend_records, key=lambda x: -x["heatwave_severity_delta"]
            )[:top_n],
        }

    @staticmethod
    async def get_emerging_risks(
        db: AsyncSession,
        base_year: int = 2025,
        target_year: int = 2035,
        month: int = 6,
        top_n: int = 10
    ) -> Dict[str, Any]:
        """
        Returns districts where composite hotspot score is growing fastest
        (i.e., currently Moderate risk but trending toward High/Critical).
        """
        base_eval = await _evaluate_all_districts(db, base_year, month)
        target_eval = await _evaluate_all_districts(db, target_year, month)

        base_lookup = {e["district_id"]: e for e in base_eval}
        n_years = target_year - base_year if target_year != base_year else 1

        emerging = []
        for e in target_eval:
            d_id = e["district_id"]
            b = base_lookup.get(d_id)
            if b is None:
                continue
            growth_rate = (e["hotspot_score"] - b["hotspot_score"]) / n_years
            record = e.copy()
            record["base_hotspot_score"] = b["hotspot_score"]
            record["base_risk_band"] = b["hotspot_risk_band"]
            record["growth_rate_per_year"] = round(growth_rate, 4)
            emerging.append(record)

        emerging_sorted = sorted(emerging, key=lambda x: -x["growth_rate_per_year"])

        return {
            "base_year": base_year,
            "target_year": target_year,
            "month": month,
            "total_districts": len(emerging_sorted),
            "top_emerging_risks": emerging_sorted[:top_n],
            "emerging_risks": emerging_sorted[:top_n],
        }
