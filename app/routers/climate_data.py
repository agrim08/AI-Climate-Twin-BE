from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.schemas.climate_data import ClimateRecord, ClimateRecordCreate, ClimateRecordUpdate
from app.services.climate_data import ClimateDataService

router = APIRouter(prefix="/climate", tags=["Climate Data"])

@router.get("/", response_model=List[ClimateRecord])
async def read_climate_records(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """
    Retrieve climate records for various locations in India.
    """
    return await ClimateDataService.get_records(db, skip=skip, limit=limit)

@router.get("/{record_id}", response_model=ClimateRecord)
async def read_climate_record(record_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get a single climate record by its ID.
    """
    record = await ClimateDataService.get_record_by_id(db, record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Climate record with ID {record_id} not found"
        )
    return record

@router.post("/", response_model=ClimateRecord, status_code=status.HTTP_201_CREATED)
async def create_climate_record(record_in: ClimateRecordCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new climate record.
    """
    return await ClimateDataService.create_record(db, record_in)

@router.put("/{record_id}", response_model=ClimateRecord)
async def update_climate_record(
    record_id: int, record_in: ClimateRecordUpdate, db: AsyncSession = Depends(get_db)
):
    """
    Update an existing climate record.
    """
    record = await ClimateDataService.update_record(db, record_id, record_in)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Climate record with ID {record_id} not found"
        )
    return record

@router.delete("/{record_id}", response_model=ClimateRecord)
async def delete_climate_record(record_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete a climate record.
    """
    record = await ClimateDataService.delete_record(db, record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Climate record with ID {record_id} not found"
        )
    return record
