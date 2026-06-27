from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, extract
from app.models.district import District
from app.models.climate_observation import ClimateObservation
from app.models.forecast import Forecast
from app.models.simulation import SimulationResult

class DashboardService:
    @staticmethod
    async def get_overview(db: AsyncSession, limit: int = 5):
        """
        Retrieves total entity counts and lists the latest observations, forecasts, and simulations.
        """
        # 1. Fetch counts
        districts_count = await db.scalar(select(func.count(District.id)))
        obs_count = await db.scalar(select(func.count(ClimateObservation.id)))
        forecasts_count = await db.scalar(select(func.count(Forecast.id)))
        sim_count = await db.scalar(select(func.count(SimulationResult.id)))
        
        # 2. Fetch latest items
        latest_obs_query = select(ClimateObservation).order_by(ClimateObservation.observation_date.desc(), ClimateObservation.id.desc()).limit(limit)
        latest_obs = (await db.execute(latest_obs_query)).scalars().all()
        
        latest_forecasts_query = select(Forecast).order_by(Forecast.forecast_date.desc(), Forecast.id.desc()).limit(limit)
        latest_forecasts = (await db.execute(latest_forecasts_query)).scalars().all()
        
        latest_sims_query = select(SimulationResult).order_by(SimulationResult.created_at.desc(), SimulationResult.id.desc()).limit(limit)
        latest_sims = (await db.execute(latest_sims_query)).scalars().all()
        
        return {
            "total_districts": districts_count or 0,
            "total_observations": obs_count or 0,
            "total_forecasts": forecasts_count or 0,
            "total_simulations": sim_count or 0,
            "latest_observations": latest_obs,
            "latest_forecasts": latest_forecasts,
            "latest_simulations": latest_sims
        }

    @staticmethod
    async def get_public_overview(db: AsyncSession):
        """
        Retrieves total entity counts, top 5 hottest districts, and top 5 highest rainfall districts.
        """
        # 1. Fetch counts
        districts_count = await db.scalar(select(func.count(District.id))) or 0
        obs_count = await db.scalar(select(func.count(ClimateObservation.id))) or 0
        forecasts_count = await db.scalar(select(func.count(Forecast.id))) or 0
        sim_count = await db.scalar(select(func.count(SimulationResult.id))) or 0
        
        # 2. Fetch top 5 hottest districts based on average temperature
        hottest_query = select(
            func.min(District.id).label("district_id"),
            District.district_name,
            District.state,
            func.avg(ClimateObservation.temperature).label("average_temperature")
        ).join(
            ClimateObservation, ClimateObservation.district_id == District.id
        ).group_by(
            District.district_name, District.state
        ).order_by(
            func.avg(ClimateObservation.temperature).desc()
        ).limit(5)
        
        hottest_result = await db.execute(hottest_query)
        top_hottest = [
            {
                "district_id": r.district_id,
                "district_name": r.district_name,
                "state": r.state,
                "average_temperature": round(float(r.average_temperature), 2)
            }
            for r in hottest_result.fetchall()
        ]
        
        # 2.5  Top 5 coldest districts — uses daytime high (T_max) to match the
        # heatwave leaderboard context. Filters to the current month so that
        # Himalayan winter readings don't pollute a summer dashboard.
        current_month = datetime.utcnow().month
        coldest_query = select(
            func.min(District.id).label("district_id"),
            District.district_name,
            District.state,
            func.max(ClimateObservation.temperature).label("average_temperature")
        ).join(
            ClimateObservation, ClimateObservation.district_id == District.id
        ).where(
            extract("month", ClimateObservation.observation_date) == current_month
        ).group_by(
            District.district_name, District.state
        ).order_by(
            func.max(ClimateObservation.temperature).asc()
        ).limit(5)
        
        coldest_result = await db.execute(coldest_query)
        top_coldest = [
            {
                "district_id": r.district_id,
                "district_name": r.district_name,
                "state": r.state,
                "average_temperature": round(float(r.average_temperature), 2)
            }
            for r in coldest_result.fetchall()
        ]
        
        # 3. Fetch top 5 highest rainfall districts based on average rainfall
        rainfall_query = select(
            func.min(District.id).label("district_id"),
            District.district_name,
            District.state,
            func.avg(ClimateObservation.rainfall).label("average_rainfall")
        ).join(
            ClimateObservation, ClimateObservation.district_id == District.id
        ).group_by(
            District.district_name, District.state
        ).order_by(
            func.avg(ClimateObservation.rainfall).desc()
        ).limit(5)
        
        rainfall_result = await db.execute(rainfall_query)
        top_rainfall = [
            {
                "district_id": r.district_id,
                "district_name": r.district_name,
                "state": r.state,
                "average_rainfall": round(float(r.average_rainfall), 2)
            }
            for r in rainfall_result.fetchall()
        ]
        
        return {
            "total_districts": districts_count,
            "total_observations": obs_count,
            "latest_forecasts_count": forecasts_count,
            "latest_simulations_count": sim_count,
            "top_5_hottest_districts": top_hottest,
            "top_5_coldest_districts": top_coldest,
            "top_5_highest_rainfall_districts": top_rainfall
        }

