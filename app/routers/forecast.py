from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from datetime import date
from pydantic import BaseModel
from app.core.database import get_db
from app.core.auth import require_role
from app.models.user import User, UserRole
from app.schemas.forecast import Forecast, ForecastCreate, ForecastUpdate
from app.services.forecast import ForecastService

router = APIRouter(prefix="/forecasts", tags=["Forecasts"])

class ForecastGenerateInput(BaseModel):
    district_id: int
    target_date: date

@router.post("/generate", response_model=Forecast, status_code=status.HTTP_201_CREATED)
async def generate_district_forecast(
    forecast_in: ForecastGenerateInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.RESEARCHER]))
):
    """
    Generate and save a forecast for a district on a target date based on past observations.
    Requires Bearer token authentication and admin/researcher roles.
    """
    return await ForecastService.generate_forecast_for_district(
        db=db,
        district_id=forecast_in.district_id,
        target_date=forecast_in.target_date
    )

@router.get("/", response_model=List[Forecast])
async def read_forecasts(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await ForecastService.get_forecasts(db, skip=skip, limit=limit)

@router.get("/{forecast_id}", response_model=Forecast)
async def read_forecast(forecast_id: int, db: AsyncSession = Depends(get_db)):
    forecast = await ForecastService.get_forecast_by_id(db, forecast_id)
    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast with ID {forecast_id} not found"
        )
    return forecast

@router.get("/district/{district_id}", response_model=List[Forecast])
async def read_district_forecasts(
    district_id: int, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    return await ForecastService.get_forecasts_by_district(db, district_id, skip=skip, limit=limit)

@router.post("/", response_model=Forecast, status_code=status.HTTP_201_CREATED)
async def create_forecast(forecast_in: ForecastCreate, db: AsyncSession = Depends(get_db)):
    return await ForecastService.create_forecast(db, forecast_in)

@router.put("/{forecast_id}", response_model=Forecast)
async def update_forecast(
    forecast_id: int, forecast_in: ForecastUpdate, db: AsyncSession = Depends(get_db)
):
    forecast = await ForecastService.update_forecast(db, forecast_id, forecast_in)
    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast with ID {forecast_id} not found"
        )
    return forecast

@router.delete("/{forecast_id}", response_model=Forecast)
async def delete_forecast(forecast_id: int, db: AsyncSession = Depends(get_db)):
    forecast = await ForecastService.delete_forecast(db, forecast_id)
    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast with ID {forecast_id} not found"
        )
    return forecast
