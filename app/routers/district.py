from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.schemas.district import District, DistrictCreate, DistrictUpdate
from app.services.district import DistrictService

router = APIRouter(prefix="/districts", tags=["Districts"])

@router.get("/", response_model=List[District])
async def read_districts(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await DistrictService.get_districts(db, skip=skip, limit=limit)

@router.get("/{district_id}", response_model=District)
async def read_district(district_id: int, db: AsyncSession = Depends(get_db)):
    district = await DistrictService.get_district_by_id(db, district_id)
    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"District with ID {district_id} not found"
        )
    return district

@router.post("/", response_model=District, status_code=status.HTTP_201_CREATED)
async def create_district(district_in: DistrictCreate, db: AsyncSession = Depends(get_db)):
    return await DistrictService.create_district(db, district_in)

@router.put("/{district_id}", response_model=District)
async def update_district(
    district_id: int, district_in: DistrictUpdate, db: AsyncSession = Depends(get_db)
):
    district = await DistrictService.update_district(db, district_id, district_in)
    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"District with ID {district_id} not found"
        )
    return district

@router.delete("/{district_id}", response_model=District)
async def delete_district(district_id: int, db: AsyncSession = Depends(get_db)):
    district = await DistrictService.delete_district(db, district_id)
    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"District with ID {district_id} not found"
        )
    return district
