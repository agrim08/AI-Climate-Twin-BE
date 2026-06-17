from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.climate_data import ClimateRecord
from app.schemas.climate_data import ClimateRecordCreate, ClimateRecordUpdate

class ClimateDataService:
    @staticmethod
    async def get_records(db: AsyncSession, skip: int = 0, limit: int = 100):
        """
        Fetch multiple climate records with pagination support.
        """
        query = select(ClimateRecord).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_record_by_id(db: AsyncSession, record_id: int):
        """
        Fetch a single climate record by its primary key ID.
        """
        query = select(ClimateRecord).where(ClimateRecord.id == record_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_record(db: AsyncSession, record_in: ClimateRecordCreate):
        """
        Create and persist a new climate record.
        """
        db_record = ClimateRecord(
            location=record_in.location,
            state=record_in.state,
            temperature=record_in.temperature,
            humidity=record_in.humidity,
            precipitation=record_in.precipitation,
        )
        if record_in.recorded_at:
            db_record.recorded_at = record_in.recorded_at
            
        db.add(db_record)
        await db.commit()
        await db.refresh(db_record)
        return db_record

    @staticmethod
    async def update_record(db: AsyncSession, record_id: int, record_in: ClimateRecordUpdate):
        """
        Update an existing climate record.
        """
        db_record = await ClimateDataService.get_record_by_id(db, record_id)
        if not db_record:
            return None
            
        update_data = record_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_record, key, value)
            
        await db.commit()
        await db.refresh(db_record)
        return db_record

    @staticmethod
    async def delete_record(db: AsyncSession, record_id: int):
        """
        Delete a climate record from the database.
        """
        db_record = await ClimateDataService.get_record_by_id(db, record_id)
        if not db_record:
            return None
            
        await db.delete(db_record)
        await db.commit()
        return db_record
