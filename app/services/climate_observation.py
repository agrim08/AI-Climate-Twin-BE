from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.climate_observation import ClimateObservation
from app.schemas.climate_observation import ClimateObservationCreate, ClimateObservationUpdate

class ClimateObservationService:
    @staticmethod
    async def get_observations(db: AsyncSession, skip: int = 0, limit: int = 100):
        query = select(ClimateObservation).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_observation_by_id(db: AsyncSession, obs_id: int):
        query = select(ClimateObservation).where(ClimateObservation.id == obs_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_observations_by_district(db: AsyncSession, district_id: int, skip: int = 0, limit: int = 100):
        query = select(ClimateObservation).where(ClimateObservation.district_id == district_id).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def create_observation(db: AsyncSession, obs_in: ClimateObservationCreate):
        db_obs = ClimateObservation(
            district_id=obs_in.district_id,
            rainfall=obs_in.rainfall,
            temperature=obs_in.temperature,
            humidity=obs_in.humidity,
            observation_date=obs_in.observation_date
        )
        db.add(db_obs)
        await db.commit()
        await db.refresh(db_obs)
        return db_obs

    @staticmethod
    async def update_observation(db: AsyncSession, obs_id: int, obs_in: ClimateObservationUpdate):
        db_obs = await ClimateObservationService.get_observation_by_id(db, obs_id)
        if not db_obs:
            return None
        update_data = obs_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_obs, key, value)
        await db.commit()
        await db.refresh(db_obs)
        return db_obs

    @staticmethod
    async def delete_observation(db: AsyncSession, obs_id: int):
        db_obs = await ClimateObservationService.get_observation_by_id(db, obs_id)
        if not db_obs:
            return None
        await db.delete(db_obs)
        await db.commit()
        return db_obs
