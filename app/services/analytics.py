from datetime import date
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.models.climate_observation import ClimateObservation
from app.models.district import District

class AnalyticsService:
    @staticmethod
    async def get_district_summary(db: AsyncSession, district_id: int):
        """
        Calculate aggregate summary stats for a single district, including climate observations and forecasts.
        """
        query = select(
            func.avg(ClimateObservation.rainfall).label("avg_rainfall"),
            func.avg(ClimateObservation.temperature).label("avg_temperature"),
            func.avg(ClimateObservation.humidity).label("avg_humidity"),
            func.count(ClimateObservation.id).label("observation_count")
        ).where(ClimateObservation.district_id == district_id)
        
        result = await db.execute(query)
        row = result.fetchone()
        
        # Fetch forecast summaries
        from app.models.forecast import Forecast
        forecast_query = select(
            func.avg(Forecast.predicted_rainfall).label("avg_pred_rainfall"),
            func.avg(Forecast.predicted_temperature).label("avg_pred_temperature"),
            func.count(Forecast.id).label("forecast_count")
        ).where(Forecast.district_id == district_id)
        
        forecast_res = await db.execute(forecast_query)
        f_row = forecast_res.fetchone()
        
        obs_count = row.observation_count if row else 0
        f_count = f_row.forecast_count if f_row else 0
        
        if obs_count == 0 and f_count == 0:
            return None
            
        return {
            "district_id": district_id,
            "average_rainfall": round(float(row.avg_rainfall), 2) if row and row.avg_rainfall is not None else 0.0,
            "average_temperature": round(float(row.avg_temperature), 2) if row and row.avg_temperature is not None else 0.0,
            "average_humidity": round(float(row.avg_humidity), 2) if row and row.avg_humidity is not None else 0.0,
            "observation_count": obs_count,
            "average_predicted_rainfall": round(float(f_row.avg_pred_rainfall), 2) if f_row and f_row.avg_pred_rainfall is not None else 0.0,
            "average_predicted_temperature": round(float(f_row.avg_pred_temperature), 2) if f_row and f_row.avg_pred_temperature is not None else 0.0,
            "forecast_count": f_count
        }

    @staticmethod
    async def get_state_summary(db: AsyncSession, state: str):
        """
        Calculate aggregate summary stats for all districts in a state.
        """
        query = select(
            func.avg(ClimateObservation.rainfall).label("avg_rainfall"),
            func.avg(ClimateObservation.temperature).label("avg_temperature"),
            func.avg(ClimateObservation.humidity).label("avg_humidity"),
            func.count(ClimateObservation.id).label("observation_count")
        ).join(District).where(func.lower(District.state) == func.lower(state))
        
        result = await db.execute(query)
        row = result.fetchone()
        if not row or row.observation_count == 0:
            return None
            
        return {
            "state": state,
            "average_rainfall": round(float(row.avg_rainfall), 2),
            "average_temperature": round(float(row.avg_temperature), 2),
            "average_humidity": round(float(row.avg_humidity), 2),
            "observation_count": row.observation_count
        }

    @staticmethod
    async def get_rainfall_trends(db: AsyncSession, district_id: int, limit: int = 100):
        """
        Retrieve rainfall data points over time for a district.
        """
        query = select(
            ClimateObservation.observation_date,
            ClimateObservation.rainfall
        ).where(ClimateObservation.district_id == district_id).order_by(ClimateObservation.observation_date).limit(limit)
        
        result = await db.execute(query)
        rows = result.fetchall()
        return [{"date": r.observation_date, "rainfall": r.rainfall} for r in rows]

    @staticmethod
    async def get_temperature_trends(db: AsyncSession, district_id: int, limit: int = 100):
        """
        Retrieve temperature data points over time for a district.
        """
        query = select(
            ClimateObservation.observation_date,
            ClimateObservation.temperature
        ).where(ClimateObservation.district_id == district_id).order_by(ClimateObservation.observation_date).limit(limit)
        
        result = await db.execute(query)
        rows = result.fetchall()
        return [{"date": r.observation_date, "temperature": r.temperature} for r in rows]

    @staticmethod
    async def get_historical_trends(
        db: AsyncSession,
        district_id: int,
        aggregation_level: str,
        start_date: date | None = None,
        end_date: date | None = None,
        skip: int = 0,
        limit: int = 100
    ):
        """
        Retrieves aggregated historical trends (rainfall, temperature, humidity) 
        for a district with weekly, monthly, or yearly groupings and filtering.
        """
        level_map = {
            "weekly": "week",
            "monthly": "month",
            "yearly": "year"
        }
        
        db_level = level_map.get(aggregation_level.lower())
        if not db_level:
            raise ValueError(f"Invalid aggregation level: {aggregation_level}. Must be 'weekly', 'monthly', or 'yearly'.")
            
        # Select truncated date and aggregate averages
        trunc_date = func.date_trunc(db_level, ClimateObservation.observation_date).label("period")
        
        query = select(
            trunc_date,
            func.avg(ClimateObservation.rainfall).label("avg_rainfall"),
            func.avg(ClimateObservation.temperature).label("avg_temperature"),
            func.avg(ClimateObservation.humidity).label("avg_humidity"),
            func.count(ClimateObservation.id).label("observation_count")
        ).where(ClimateObservation.district_id == district_id)
        
        # Apply date filters
        if start_date:
            query = query.where(ClimateObservation.observation_date >= start_date)
        if end_date:
            query = query.where(ClimateObservation.observation_date <= end_date)
            
        # Group, sort, and paginate
        query = query.group_by(trunc_date).order_by(trunc_date)
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        rows = result.fetchall()
        
        return [
            {
                "period": r.period.date() if hasattr(r.period, "date") else r.period,
                "average_rainfall": round(float(r.avg_rainfall), 2) if r.avg_rainfall is not None else 0.0,
                "average_temperature": round(float(r.avg_temperature), 2) if r.avg_temperature is not None else 0.0,
                "average_humidity": round(float(r.avg_humidity), 2) if r.avg_humidity is not None else 0.0,
                "observation_count": r.observation_count
            }
            for r in rows
        ]

    @staticmethod
    async def get_district_comparison(db: AsyncSession, skip: int = 0, limit: int = 100):
        """
        Compare average climate metrics across districts using SQL group-by aggregation.
        """
        query = select(
            District.id.label("district_id"),
            District.district_name,
            District.state,
            func.avg(ClimateObservation.rainfall).label("avg_rainfall"),
            func.avg(ClimateObservation.temperature).label("avg_temperature"),
            func.avg(ClimateObservation.humidity).label("avg_humidity"),
            func.count(ClimateObservation.id).label("observation_count")
        ).join(
            ClimateObservation, ClimateObservation.district_id == District.id, isouter=True
        ).group_by(
            District.id, District.district_name, District.state
        ).order_by(District.district_name).offset(skip).limit(limit)

        result = await db.execute(query)
        rows = result.fetchall()

        return [
            {
                "district_id": r.district_id,
                "district_name": r.district_name,
                "state": r.state,
                "average_rainfall": round(float(r.avg_rainfall), 2) if r.avg_rainfall is not None else 0.0,
                "average_temperature": round(float(r.avg_temperature), 2) if r.avg_temperature is not None else 0.0,
                "average_humidity": round(float(r.avg_humidity), 2) if r.avg_humidity is not None else 0.0,
                "observation_count": r.observation_count
            }
            for r in rows
        ]

    @staticmethod
    async def get_district_comparison_detail(db: AsyncSession, district_id: int):
        """
        Compare a single district's climate averages with overall averages across all districts.
        """
        # Verify district exists
        from app.services.district import DistrictService
        district = await DistrictService.get_district_by_id(db, district_id)
        if not district:
            raise ValueError(f"District with ID {district_id} not found.")

        # Get district summary
        summary = await AnalyticsService.get_district_summary(db, district_id)
        
        dist_temp = summary["average_temperature"] if summary else 0.0
        dist_rain = summary["average_rainfall"] if summary else 0.0
        dist_hum = summary["average_humidity"] if summary else 0.0
        obs_count = summary["observation_count"] if summary else 0

        # Get overall averages across all districts
        overall_query = select(
            func.avg(ClimateObservation.rainfall).label("avg_rainfall"),
            func.avg(ClimateObservation.temperature).label("avg_temperature"),
            func.avg(ClimateObservation.humidity).label("avg_humidity")
        )
        overall_res = await db.execute(overall_query)
        overall_row = overall_res.fetchone()
        
        over_temp = round(float(overall_row.avg_temperature), 2) if overall_row and overall_row.avg_temperature is not None else 0.0
        over_rain = round(float(overall_row.avg_rainfall), 2) if overall_row and overall_row.avg_rainfall is not None else 0.0
        over_hum = round(float(overall_row.avg_humidity), 2) if overall_row and overall_row.avg_humidity is not None else 0.0

        # Calculate differences
        diff_temp = round(dist_temp - over_temp, 2)
        diff_rain = round(dist_rain - over_rain, 2)
        diff_hum = round(dist_hum - over_hum, 2)

        return {
            "district_id": district_id,
            "district_name": district.district_name,
            "state": district.state,
            "observation_count": obs_count,
            "district_averages": {
                "temperature": dist_temp,
                "rainfall": dist_rain,
                "humidity": dist_hum
            },
            "overall_averages": {
                "temperature": over_temp,
                "rainfall": over_rain,
                "humidity": over_hum
            },
            "differences": {
                "temperature": diff_temp,
                "rainfall": diff_rain,
                "humidity": diff_hum
            }
        }

    @staticmethod
    async def get_rankings(db: AsyncSession, metric: str, state: Optional[str] = None, limit: int = 5):
        """
        Get top districts ranked by temperature or rainfall, optionally filtered by state.
        """
        metric = metric.lower()
        if metric not in ["hottest", "wettest", "driest"]:
            raise ValueError("Invalid metric. Must be 'hottest', 'wettest', or 'driest'.")

        if metric == "hottest":
            val_col = func.avg(ClimateObservation.temperature).label("val")
            order_col = func.avg(ClimateObservation.temperature).desc()
        elif metric == "wettest":
            val_col = func.avg(ClimateObservation.rainfall).label("val")
            order_col = func.avg(ClimateObservation.rainfall).desc()
        else: # driest
            val_col = func.avg(ClimateObservation.rainfall).label("val")
            order_col = func.avg(ClimateObservation.rainfall).asc()

        query = select(
            District.id.label("district_id"),
            District.district_name,
            District.state,
            val_col
        ).join(
            ClimateObservation, ClimateObservation.district_id == District.id
        )

        if state:
            query = query.where(func.lower(District.state) == func.lower(state))

        query = query.group_by(
            District.id, District.district_name, District.state
        ).order_by(order_col).limit(limit)

        res = await db.execute(query)
        rows = res.fetchall()

        return [
            {
                "district_id": r.district_id,
                "district_name": r.district_name,
                "state": r.state,
                "value": round(float(r.val), 2) if r.val is not None else 0.0
            }
            for r in rows
        ]



