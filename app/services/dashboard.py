from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
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
