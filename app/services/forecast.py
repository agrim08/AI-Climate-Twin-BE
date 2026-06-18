from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.forecast import Forecast
from app.schemas.forecast import ForecastCreate, ForecastUpdate

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
        # 1. Fetch recent observations
        from app.services.climate_observation import ClimateObservationService
        observations = await ClimateObservationService.get_observations_by_district(db, district_id, limit=30)
        
        if not observations:
            # Fallback values if no historical data is available
            predicted_rain = 50.0
            predicted_temp = 28.0
        else:
            # Simple moving average model
            predicted_rain = round(sum(o.rainfall for o in observations) / len(observations), 2)
            predicted_temp = round(sum(o.temperature for o in observations) / len(observations), 2)

        # 2. Check if a forecast already exists for this district + date (upsert logic)
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
        # 1. Verify district exists
        from app.services.district import DistrictService
        district = await DistrictService.get_district_by_id(db, district_id)
        if not district:
            raise ValueError(f"District with ID {district_id} not found.")

        # 2. Fetch recent observations
        from app.services.climate_observation import ClimateObservationService
        observations = await ClimateObservationService.get_observations_by_district(db, district_id, limit=30)
        
        if not observations:
            raise ValueError(f"No climate observations found for district ID {district_id} to generate forecast.")

        # Simple moving average model
        predicted_rain = round(sum(o.rainfall for o in observations) / len(observations), 2)
        predicted_temp = round(sum(o.temperature for o in observations) / len(observations), 2)

        forecasts = []
        today = date.today()
        
        for i in range(7):
            target_date = today + timedelta(days=i)
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

