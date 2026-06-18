from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.schemas.climate_observation import ClimateObservation, ClimateObservationCreate, ClimateObservationUpdate
from app.services.climate_observation import ClimateObservationService

router = APIRouter(prefix="/observations", tags=["Climate Observations"])

@router.get("/", response_model=List[ClimateObservation])
async def read_observations(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await ClimateObservationService.get_observations(db, skip=skip, limit=limit)

@router.get("/{obs_id}", response_model=ClimateObservation)
async def read_observation(obs_id: int, db: AsyncSession = Depends(get_db)):
    obs = await ClimateObservationService.get_observation_by_id(db, obs_id)
    if not obs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Climate observation with ID {obs_id} not found"
        )
    return obs

@router.get("/district/{district_id}", response_model=List[ClimateObservation])
async def read_district_observations(
    district_id: int, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    return await ClimateObservationService.get_observations_by_district(db, district_id, skip=skip, limit=limit)

@router.post("/", response_model=ClimateObservation, status_code=status.HTTP_201_CREATED)
async def create_observation(obs_in: ClimateObservationCreate, db: AsyncSession = Depends(get_db)):
    return await ClimateObservationService.create_observation(db, obs_in)

@router.put("/{obs_id}", response_model=ClimateObservation)
async def update_observation(
    obs_id: int, obs_in: ClimateObservationUpdate, db: AsyncSession = Depends(get_db)
):
    obs = await ClimateObservationService.update_observation(db, obs_id, obs_in)
    if not obs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Climate observation with ID {obs_id} not found"
        )
    return obs

@router.delete("/{obs_id}", response_model=ClimateObservation)
async def delete_observation(obs_id: int, db: AsyncSession = Depends(get_db)):
    obs = await ClimateObservationService.delete_observation(db, obs_id)
    if not obs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Climate observation with ID {obs_id} not found"
        )
    return obs
