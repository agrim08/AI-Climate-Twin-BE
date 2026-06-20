from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.forecast import Forecast
from app.schemas.forecast import ForecastCreate, ForecastUpdate

# Predictor instances cache
_temp_predictor = None
_rain_predictor = None
_drought_predictor = None
_ew_predictor = None

def get_predictors():
    global _temp_predictor, _rain_predictor, _drought_predictor, _ew_predictor
    if _temp_predictor is None or _rain_predictor is None:
        from app.ml_services.predict_temperature import TemperaturePredictor
        from app.ml_services.predict_rainfall import RainfallPredictor
        _temp_predictor = TemperaturePredictor()
        _rain_predictor = RainfallPredictor()
    if _drought_predictor is None:
        from app.ml_services.predict_drought import DroughtPredictor
        _drought_predictor = DroughtPredictor()
    if _ew_predictor is None:
        from app.ml_services.predict_extreme_weather import ExtremeWeatherPredictor
        _ew_predictor = ExtremeWeatherPredictor()
    return _temp_predictor, _rain_predictor, _drought_predictor, _ew_predictor

class ForecastService:
    @staticmethod
    async def get_forecasts(db: AsyncSession, skip: int = 0, limit: int = 100):
        query = select(Forecast).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_forecast_by_id(db: AsyncSession, forecast_id: int):
        query = select(Forecast).where(Forecast.id == forecast_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_forecasts_by_district(db: AsyncSession, district_id: int, skip: int = 0, limit: int = 100):
        query = select(Forecast).where(Forecast.district_id == district_id).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def create_forecast(db: AsyncSession, forecast_in: ForecastCreate):
        db_forecast = Forecast(
            district_id=forecast_in.district_id,
            predicted_rainfall=forecast_in.predicted_rainfall,
            predicted_temperature=forecast_in.predicted_temperature,
            forecast_date=forecast_in.forecast_date
        )
        db.add(db_forecast)
        await db.commit()
        await db.refresh(db_forecast)
        return db_forecast

    @staticmethod
    async def update_forecast(db: AsyncSession, forecast_id: int, forecast_in: ForecastUpdate):
        db_forecast = await ForecastService.get_forecast_by_id(db, forecast_id)
        if not db_forecast:
            return None
        update_data = forecast_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_forecast, key, value)
        await db.commit()
        await db.refresh(db_forecast)
        return db_forecast

    @staticmethod
    async def delete_forecast(db: AsyncSession, forecast_id: int):
        db_forecast = await ForecastService.get_forecast_by_id(db, forecast_id)
        if not db_forecast:
            return None
        await db.delete(db_forecast)
        await db.commit()
        return db_forecast

    @staticmethod
    async def generate_forecast_for_district(db: AsyncSession, district_id: int, target_date: date):
        """
        Generate and save/upsert a forecast for a district on a target date based on past observations.
        """
        from app.ml_services.lookup import ClimateLookup
        
        # 1. Verify district exists
        from app.services.district import DistrictService
        district = await DistrictService.get_district_by_id(db, district_id)
        if not district:
            raise ValueError(f"District with ID {district_id} not found.")

        temp_predictor, rain_predictor = get_predictors()

        # 2. Build look up state
        req_payload = {
            "district_id": district_id,
            "year": target_date.year,
            "month": target_date.month
        }
        full_payload = await ClimateLookup.get_lookup_state(db, req_payload)

        # 3. Predict values using ML models
        t_res = temp_predictor.predict(full_payload)
        r_res = rain_predictor.predict(full_payload)

        predicted_temp = t_res["predicted_temperature_c"]
        predicted_rain = r_res["predicted_rainfall_mm"]

        # 4. Check if a forecast already exists for this district + date (upsert logic)
        query = select(Forecast).where(
            Forecast.district_id == district_id,
            Forecast.forecast_date == target_date
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            existing.predicted_rainfall = predicted_rain
            existing.predicted_temperature = predicted_temp
            db_forecast = existing
        else:
            db_forecast = Forecast(
                district_id=district_id,
                predicted_rainfall=predicted_rain,
                predicted_temperature=predicted_temp,
                forecast_date=target_date
            )
            db.add(db_forecast)

        await db.commit()
        await db.refresh(db_forecast)
        return db_forecast

    @staticmethod
    async def generate_7day_forecast(db: AsyncSession, district_id: int):
        """
        Generate and save/upsert a 7-day forecast starting from today for a district based on past observations.
        """
        from app.ml_services.lookup import ClimateLookup
        
        # 1. Verify district exists
        from app.services.district import DistrictService
        district = await DistrictService.get_district_by_id(db, district_id)
        if not district:
            raise ValueError(f"District with ID {district_id} not found.")

        temp_predictor, rain_predictor = get_predictors()

        forecasts = []
        today = date.today()
        
        # Cache predictions for the same (year, month) to avoid duplicate model calls inside the 7-day loop
        prediction_cache = {}

        for i in range(7):
            target_date = today + timedelta(days=i)
            key = (target_date.year, target_date.month)

            if key not in prediction_cache:
                req_payload = {
                    "district_id": district_id,
                    "year": target_date.year,
                    "month": target_date.month
                }
                full_payload = await ClimateLookup.get_lookup_state(db, req_payload)
                t_res = temp_predictor.predict(full_payload)
                r_res = rain_predictor.predict(full_payload)

                prediction_cache[key] = {
                    "temp": t_res["predicted_temperature_c"],
                    "rain": r_res["predicted_rainfall_mm"]
                }

            predicted_temp = prediction_cache[key]["temp"]
            predicted_rain = prediction_cache[key]["rain"]

            query = select(Forecast).where(
                Forecast.district_id == district_id,
                Forecast.forecast_date == target_date
            )
            result = await db.execute(query)
            existing = result.scalar_one_or_none()

            if existing:
                existing.predicted_rainfall = predicted_rain
                existing.predicted_temperature = predicted_temp
                db_forecast = existing
            else:
                db_forecast = Forecast(
                    district_id=district_id,
                    predicted_rainfall=predicted_rain,
                    predicted_temperature=predicted_temp,
                    forecast_date=target_date
                )
                db.add(db_forecast)
            forecasts.append(db_forecast)

        await db.commit()
        for f in forecasts:
            await db.refresh(f)

        return forecasts

    @staticmethod
    async def get_active_forecasts_by_district(db: AsyncSession, district_id: int):
        """
        Retrieve active forecasts for a district (from today onwards).
        """
        # Verify district exists
        from app.services.district import DistrictService
        district = await DistrictService.get_district_by_id(db, district_id)
        if not district:
            raise ValueError(f"District with ID {district_id} not found.")

        query = select(Forecast).where(
            Forecast.district_id == district_id,
            Forecast.forecast_date >= date.today()
        ).order_by(Forecast.forecast_date.asc())
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_all_forecasts_by_district_paginated(db: AsyncSession, district_id: int, skip: int = 0, limit: int = 100):
        """
        Retrieve all forecasts for a district with pagination.
        """
        # Verify district exists
        from app.services.district import DistrictService
        district = await DistrictService.get_district_by_id(db, district_id)
        if not district:
            raise ValueError(f"District with ID {district_id} not found.")

        query = select(Forecast).where(
            Forecast.district_id == district_id
        ).order_by(Forecast.forecast_date.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_dynamic_projections(
        db: AsyncSession,
        district_id: int,
        timeframe: str,
        temperature_delta: float = 0.0,
        rainfall_delta: float = 0.0,
        soil_moisture_delta: float = 0.0
    ):
        """
        Generate on-the-fly ML climate projections for a district across any timeframe (7day, 1month, 1year, or future year like 2030/2050),
        applying scenario delta modifiers without persisting results.
        """
        # 1. Verify district exists
        from app.services.district import DistrictService
        district = await DistrictService.get_district_by_id(db, district_id)
        if not district:
            raise ValueError(f"District with ID {district_id} not found.")

        # 2. Determine base timeline date context
        from app.models.climate_observation import ClimateObservation
        obs_query = select(ClimateObservation).where(
            ClimateObservation.district_id == district_id
        ).order_by(ClimateObservation.observation_date.desc()).limit(1)
        res = await db.execute(obs_query)
        latest_obs = res.scalar_one_or_none()
        
        base_date = latest_obs.observation_date if latest_obs else date.today()

        # 3. Resolve timeframe into target dates
        target_dates = []
        timeframe_lower = timeframe.lower()

        if timeframe_lower == "7day":
            for i in range(7):
                target_dates.append(base_date + timedelta(days=i))
        elif timeframe_lower == "1month":
            # Target next calendar month
            month_idx = base_date.month + 1
            year_val = base_date.year + ((month_idx - 1) // 12)
            month_val = ((month_idx - 1) % 12) + 1
            target_dates.append(date(year_val, month_val, 1))
        elif timeframe_lower == "1year":
            # Target next 12 calendar months
            for i in range(1, 13):
                month_idx = base_date.month + i
                year_val = base_date.year + ((month_idx - 1) // 12)
                month_val = ((month_idx - 1) % 12) + 1
                target_dates.append(date(year_val, month_val, 1))
        else:
            # Check if it's a specific year number (e.g. 2030)
            try:
                target_year = int(timeframe_lower)
                if not (2020 <= target_year <= 2100):
                    raise ValueError()
                # Target all 12 months of that specific calendar year
                for m in range(1, 13):
                    target_dates.append(date(target_year, m, 1))
            except ValueError:
                raise ValueError(
                    f"Invalid timeframe: {timeframe}. Choose from '7day', '1month', '1year', or a target year (e.g. '2030', '2050')."
                )

        # 4. Generate projections
        from app.ml_services.lookup import ClimateLookup
        temp_predictor, rain_predictor, drought_predictor, ew_predictor = get_predictors()
        projections = []

        for target_date in target_dates:
            req_payload = {
                "district_id": district_id,
                "year": target_date.year,
                "month": target_date.month
            }
            # Resolve baseline parameters
            full_payload = await ClimateLookup.get_lookup_state(db, req_payload)
            
            # Apply delta modifiers
            full_payload["temperature_delta"] = temperature_delta
            # Rainfall and soil moisture changes are percentage-based in simulation and predictions
            if rainfall_delta != 0.0:
                base_rain_prev_1 = full_payload.get("rainfall_prev_1", 10.0)
                full_payload["rainfall_delta"] = base_rain_prev_1 * (rainfall_delta / 100.0)
            if soil_moisture_delta != 0.0:
                base_sm = full_payload.get("soil_moisture", 0.2)
                full_payload["soil_moisture_delta"] = base_sm * (soil_moisture_delta / 100.0)

            # Predict (Chained Cascade)
            t_res = temp_predictor.predict(full_payload)
            # Update baseline temperature for subsequent predictors
            full_payload["temperature_c"] = t_res["predicted_temperature_c"]

            r_res = rain_predictor.predict(full_payload)
            # Update baseline rainfall for subsequent predictors
            full_payload["rainfall_mm"] = r_res["predicted_rainfall_mm"]
            
            # Get drought classification
            d_res = drought_predictor.predict(full_payload)
            
            # Get extreme weather alerts
            ew_res = ew_predictor.predict(full_payload, apply_deltas=True)
            
            # Compute overall risk
            overall_risk_val = "Low"
            overall_risk_score = 0.0
            if ew_res:
                hw_out = ew_res["heatwave"]
                er_out = ew_res["extreme_rainfall"]
                hw_probs = hw_out.get("_probabilities")
                er_probs = er_out.get("_probabilities")
                if hw_probs is not None and er_probs is not None:
                    overall_risk = ew_predictor.calculate_overall_risk(hw_out, er_out, hw_probs, er_probs)
                    overall_risk_val = overall_risk.get("overall_extreme_weather_risk", "Low")
                    overall_risk_score = overall_risk.get("overall_risk_score", 0.0)
                
                # Strip out internal cascade metadata
                ew_res["heatwave"].pop("_probabilities", None)
                ew_res["heatwave"].pop("_features", None)
                ew_res["extreme_rainfall"].pop("_probabilities", None)
                ew_res["extreme_rainfall"].pop("_features", None)

            # Return simulated (delta-applied) values to the user
            simulated_temp = t_res["predicted_temperature_c"] + temperature_delta
            simulated_rain = max(0.0, r_res["predicted_rainfall_mm"] * (1.0 + rainfall_delta / 100.0))

            projections.append({
                "date": target_date.strftime("%Y-%m-%d"),
                "year": target_date.year,
                "month": target_date.month,
                "predicted_temperature_c": round(simulated_temp, 2),
                "temperature_confidence": t_res["confidence"],
                "predicted_rainfall_mm": round(simulated_rain, 2),
                "rainfall_confidence": r_res["confidence"],
                "rainfall_confidence_score": r_res["confidence_score"],
                "monsoon_status": r_res["monsoon_status"],
                "drought_category": d_res["drought_category"] if d_res else "Low",
                "drought_confidence": d_res["confidence_level"] if d_res else "High",
                "extreme_weather_risk": overall_risk_val,
                "extreme_weather_score": overall_risk_score
            })

        return projections
