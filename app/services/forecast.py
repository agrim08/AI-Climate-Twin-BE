from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.forecast import Forecast
from app.schemas.forecast import ForecastCreate, ForecastUpdate

# Predictor instances cache
_temp_predictor = None
_rain_predictor = None

def get_predictors():
    global _temp_predictor, _rain_predictor
    if _temp_predictor is None or _rain_predictor is None:
        from app.ml_services.predict_temperature import TemperaturePredictor
        from app.ml_services.predict_rainfall import RainfallPredictor
        _temp_predictor = TemperaturePredictor()
        _rain_predictor = RainfallPredictor()
    return _temp_predictor, _rain_predictor

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
