import uuid
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.simulation import SimulationResult
from app.schemas.simulation import SimulationResultCreate, SimulationResultUpdate

# Predictor instances cache
_temp_predictor = None
_rain_predictor = None
_drought_predictor = None
_extreme_predictor = None

def get_predictors():
    global _temp_predictor, _rain_predictor, _drought_predictor, _extreme_predictor
    if _temp_predictor is None or _rain_predictor is None or _drought_predictor is None or _extreme_predictor is None:
        from app.ml_services.predict_temperature import TemperaturePredictor
        from app.ml_services.predict_rainfall import RainfallPredictor
        from app.ml_services.predict_drought import DroughtPredictor
        from app.ml_services.predict_extreme_weather import ExtremeWeatherPredictor
        _temp_predictor = TemperaturePredictor()
        _rain_predictor = RainfallPredictor()
        _drought_predictor = DroughtPredictor()
        _extreme_predictor = ExtremeWeatherPredictor()
    return _temp_predictor, _rain_predictor, _drought_predictor, _extreme_predictor

class SimulationResultService:
    @staticmethod
    async def get_simulation_results(db: AsyncSession, skip: int = 0, limit: int = 100):
        query = select(SimulationResult).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_simulation_result_by_id(db: AsyncSession, sim_id: int):
        query = select(SimulationResult).where(SimulationResult.id == sim_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_simulation_results_by_user(db: AsyncSession, user_id: uuid.UUID, skip: int = 0, limit: int = 100):
        query = select(SimulationResult).where(SimulationResult.user_id == user_id).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def create_simulation_result(db: AsyncSession, sim_in: SimulationResultCreate):
        db_sim = SimulationResult(
            user_id=sim_in.user_id,
            district_id=sim_in.district_id,
            rainfall_change=sim_in.rainfall_change,
            temperature_change=sim_in.temperature_change,
            humidity_change=sim_in.humidity_change,
            result_json=sim_in.result_json
        )
        db.add(db_sim)
        await db.commit()
        await db.refresh(db_sim)
        return db_sim

    @staticmethod
    async def update_simulation_result(db: AsyncSession, sim_id: int, sim_in: SimulationResultUpdate):
        db_sim = await SimulationResultService.get_simulation_result_by_id(db, sim_id)
        if not db_sim:
            return None
        update_data = sim_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_sim, key, value)
        await db.commit()
        await db.refresh(db_sim)
        return db_sim

    @staticmethod
    async def delete_simulation_result(db: AsyncSession, sim_id: int):
        db_sim = await SimulationResultService.get_simulation_result_by_id(db, sim_id)
        if not db_sim:
            return None
        await db.delete(db_sim)
        await db.commit()
        return db_sim

    @staticmethod
    async def run_simulation(
        db: AsyncSession,
        user_id: uuid.UUID,
        district_id: int,
        rainfall_change: float,
        temperature_change: float,
        humidity_change: float
    ):
        """
        Runs a climate simulation for a district by applying delta changes (anomalies) to the baseline climate summary.
        """
        # 1. Verify district exists
        from app.services.district import DistrictService
        district = await DistrictService.get_district_by_id(db, district_id)
        if not district:
            raise ValueError(f"District with ID {district_id} not found.")

        temp_predictor, rain_predictor, drought_predictor, extreme_predictor = get_predictors()
        from app.ml_services.lookup import ClimateLookup
        from app.models.climate_observation import ClimateObservation

        # 2. Query the latest observation to establish baseline year/month context
        query = select(ClimateObservation).where(
            ClimateObservation.district_id == district_id
        ).order_by(ClimateObservation.observation_date.desc()).limit(1)
        res = await db.execute(query)
        latest_obs = res.scalar_one_or_none()

        if latest_obs:
            year = latest_obs.observation_date.year
            month = latest_obs.observation_date.month
            obs_count = 1
        else:
            year = 2024
            month = 6
            obs_count = 0

        # 3. Retrieve baseline lookup state (deltas = 0)
        baseline_payload = await ClimateLookup.get_lookup_state(db, {
            "district_id": district_id,
            "year": year,
            "month": month,
            "temperature_delta": 0.0,
            "rainfall_delta": 0.0,
            "soil_moisture_delta": 0.0
        })

        # Run ML models on baseline state following the consistent chain:
        # Temperature -> Rainfall -> Drought -> Extreme Weather
        
        # Step A: Temperature baseline
        t_base_res = temp_predictor.predict(baseline_payload)
        base_temp = t_base_res["predicted_temperature_c"]
        baseline_payload["temperature_c"] = base_temp
        
        # Step B: Rainfall baseline
        r_base_res = rain_predictor.predict(baseline_payload)
        base_rain = r_base_res["predicted_rainfall_mm"]
        baseline_payload["rainfall_mm"] = base_rain
        
        # Step C: Drought baseline
        d_base_res = drought_predictor.predict(baseline_payload)
        
        # Step D: Extreme Weather baseline
        ew_base_res = extreme_predictor.predict(baseline_payload, apply_deltas=False)
        base_overall = extreme_predictor.calculate_overall_risk(
            ew_base_res["heatwave"], ew_base_res["extreme_rainfall"],
            ew_base_res["heatwave"]["_probabilities"], ew_base_res["extreme_rainfall"]["_probabilities"]
        )

        # For humidity, use database baseline average or fallback (since it's not predicted by ML models)
        from app.services.analytics import AnalyticsService
        db_summary = await AnalyticsService.get_district_summary(db, district_id)
        base_hum = db_summary["average_humidity"] if db_summary else 60.0

        # 4. Retrieve simulated state (deltas applied)
        # We pass deltas directly as percentage values to downstream ML predictors
        simulated_payload = await ClimateLookup.get_lookup_state(db, {
            "district_id": district_id,
            "year": year,
            "month": month,
            "temperature_delta": temperature_change,
            "rainfall_delta": rainfall_change,
            "soil_moisture_delta": humidity_change
        })

        # Run ML models on simulated state following the same consistent chain:
        # Temperature (+delta) -> Rainfall (+delta) -> Drought -> Extreme Weather
        
        # Step A: Simulated temperature
        t_sim_res = temp_predictor.predict(simulated_payload)
        simulated_temp = t_sim_res["predicted_temperature_c"] + temperature_change
        simulated_payload["temperature_c"] = simulated_temp
        
        # Step B: Simulated rainfall
        r_sim_res = rain_predictor.predict(simulated_payload)
        simulated_rain = max(0.0, r_sim_res["predicted_rainfall_mm"] * (1.0 + rainfall_change / 100.0))
        simulated_payload["rainfall_mm"] = simulated_rain
        
        # Scale soil moisture in payload for drought and extreme weather
        simulated_payload["soil_moisture"] = max(0.0, min(1.0, float(simulated_payload.get("soil_moisture", 0.2)) * (1.0 + humidity_change / 100.0)))
        
        # Step C: Simulated drought
        d_sim_res = drought_predictor.predict(simulated_payload)
        
        # Step D: Simulated extreme weather
        ew_sim_res = extreme_predictor.predict(simulated_payload, apply_deltas=False)
        sim_overall = extreme_predictor.calculate_overall_risk(
            ew_sim_res["heatwave"], ew_sim_res["extreme_rainfall"],
            ew_sim_res["heatwave"]["_probabilities"], ew_sim_res["extreme_rainfall"]["_probabilities"]
        )

        simulated_hum = round(max(0.0, min(100.0, base_hum * (1 + humidity_change / 100.0))), 2)

        # 5. Risk level change and confidence change comparison
        lvl_map = {"Low": 0, "Medium": 1, "High": 2, "Extreme": 3}
        
        # Overall risk level shift
        base_lvl = lvl_map.get(base_overall["overall_extreme_weather_risk"], 0)
        sim_lvl = lvl_map.get(sim_overall["overall_extreme_weather_risk"], 0)
        diff = sim_lvl - base_lvl
        if diff > 0:
            risk_change_str = f"+{diff} level{'s' if diff > 1 else ''}"
        elif diff < 0:
            risk_change_str = f"{diff} level{'s' if abs(diff) > 1 else ''}"
        else:
            risk_change_str = "No change"
            
        # Confidence comparison
        base_conf = (
            float(d_base_res["confidence_score"]) +
            float(ew_base_res["heatwave"]["confidence"]) +
            float(ew_base_res["extreme_rainfall"]["confidence"])
        ) / 3.0
        
        sim_conf = (
            float(d_sim_res["confidence_score"]) +
            float(ew_sim_res["heatwave"]["confidence"]) +
            float(ew_sim_res["extreme_rainfall"]["confidence"])
        ) / 3.0
        
        confidence_change_str = f"{round(sim_conf - base_conf, 3):+}"

        # Comfort index calculation (backward compatibility helper)
        comfort_index = "Uncomfortable" if simulated_temp > 32.0 and simulated_hum > 70.0 else "Pleasant" if 20.0 <= simulated_temp <= 26.0 else "Moderate"

        result_json = {
            "baseline_state": {
                "temperature": base_temp,
                "rainfall": base_rain,
                "humidity": base_hum,
                "drought_category": d_base_res["drought_category"],
                "drought_score": d_base_res["severity_score"],
                "heatwave_category": ew_base_res["heatwave"]["category"],
                "heatwave_severity": ew_base_res["heatwave"]["severity"],
                "extreme_rainfall_category": ew_base_res["extreme_rainfall"]["category"],
                "extreme_rainfall_severity": ew_base_res["extreme_rainfall"]["severity"],
                "overall_risk_score": base_overall["overall_risk_score"],
                "overall_risk_category": base_overall["overall_extreme_weather_risk"]
            },
            "scenario_state": {
                "temperature": simulated_temp,
                "rainfall": simulated_rain,
                "humidity": simulated_hum,
                "drought_category": d_sim_res["drought_category"],
                "drought_score": d_sim_res["severity_score"],
                "heatwave_category": ew_sim_res["heatwave"]["category"],
                "heatwave_severity": ew_sim_res["heatwave"]["severity"],
                "extreme_rainfall_category": ew_sim_res["extreme_rainfall"]["category"],
                "extreme_rainfall_severity": ew_sim_res["extreme_rainfall"]["severity"],
                "overall_risk_score": sim_overall["overall_risk_score"],
                "overall_risk_category": sim_overall["overall_extreme_weather_risk"]
            },
            "risk_change": risk_change_str,
            "confidence_change": confidence_change_str,
            
            # Nested fields for backward compatibility
            "baseline": {
                "temperature": base_temp,
                "rainfall": base_rain,
                "humidity": base_hum,
                "observation_count": obs_count
            },
            "projections": {
                "temperature": simulated_temp,
                "rainfall": simulated_rain,
                "humidity": simulated_hum
            },
            "impacts": {
                "drought_risk": d_sim_res["drought_category"],
                "flood_risk": ew_sim_res["extreme_rainfall"]["category"],
                "comfort_index": comfort_index
            }
        }

        # 6. Save and return simulation record
        db_sim = SimulationResult(
            user_id=user_id,
            district_id=district_id,
            rainfall_change=rainfall_change,
            temperature_change=temperature_change,
            humidity_change=humidity_change,
            result_json=result_json
        )
        db.add(db_sim)
        await db.commit()
        await db.refresh(db_sim)
        return db_sim

    @staticmethod
    async def run_scenario_simulation(
        db: AsyncSession,
        user_id: uuid.UUID,
        district_id: int,
        scenario: str
    ):
        """
        Runs a climate simulation for a district using pre-defined scenarios.
        """
        scenario_lower = scenario.lower()
        if scenario_lower == "temperature_plus_1":
            temp_change = 1.0
            rain_change = 0.0
            hum_change = 0.0
        elif scenario_lower == "temperature_plus_2":
            temp_change = 2.0
            rain_change = 0.0
            hum_change = 0.0
        elif scenario_lower == "rainfall_minus_10":
            temp_change = 0.0
            rain_change = -10.0
            hum_change = 0.0
        elif scenario_lower == "rainfall_plus_10":
            temp_change = 0.0
            rain_change = 10.0
            hum_change = 0.0
        else:
            raise ValueError(
                f"Invalid scenario: {scenario}. Choose from: "
                "temperature_plus_1, temperature_plus_2, rainfall_minus_10, rainfall_plus_10"
            )

        return await SimulationResultService.run_simulation(
            db=db,
            user_id=user_id,
            district_id=district_id,
            rainfall_change=rain_change,
            temperature_change=temp_change,
            humidity_change=hum_change
        )
