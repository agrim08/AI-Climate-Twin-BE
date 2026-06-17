from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.models.climate_observation import ClimateObservation
from app.models.district import District

class AnalyticsService:
    @staticmethod
    async def get_district_summary(db: AsyncSession, district_id: int):
        """
        Calculate aggregate summary stats for a single district.
        """
        query = select(
            func.avg(ClimateObservation.rainfall).label("avg_rainfall"),
            func.avg(ClimateObservation.temperature).label("avg_temperature"),
            func.avg(ClimateObservation.humidity).label("avg_humidity"),
            func.count(ClimateObservation.id).label("observation_count")
        ).where(ClimateObservation.district_id == district_id)
        
        result = await db.execute(query)
        row = result.fetchone()
        if not row or row.observation_count == 0:
            return None
            
        return {
            "district_id": district_id,
            "average_rainfall": round(float(row.avg_rainfall), 2),
            "average_temperature": round(float(row.avg_temperature), 2),
            "average_humidity": round(float(row.avg_humidity), 2),
            "observation_count": row.observation_count
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


