from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.district import District
from app.schemas.district import DistrictCreate, DistrictUpdate

class DistrictService:
    @staticmethod
    async def get_districts(db: AsyncSession, skip: int = 0, limit: int = 100):
        query = select(District).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_district_by_id(db: AsyncSession, district_id: int):
        query = select(District).where(District.id == district_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_district(db: AsyncSession, district_in: DistrictCreate):
        db_district = District(
            state=district_in.state,
            district_name=district_in.district_name,
            latitude=district_in.latitude,
            longitude=district_in.longitude
        )
        db.add(db_district)
        await db.commit()
        await db.refresh(db_district)
        return db_district

    @staticmethod
    async def update_district(db: AsyncSession, district_id: int, district_in: DistrictUpdate):
        db_district = await DistrictService.get_district_by_id(db, district_id)
        if not db_district:
            return None
        update_data = district_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_district, key, value)
        await db.commit()
        await db.refresh(db_district)
        return db_district

    @staticmethod
    async def delete_district(db: AsyncSession, district_id: int):
        db_district = await DistrictService.get_district_by_id(db, district_id)
        if not db_district:
            return None
        await db.delete(db_district)
        await db.commit()
        return db_district
