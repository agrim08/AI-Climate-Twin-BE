from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from pydantic import BaseModel

from app.core.database import get_db
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Climate Analytics"])

class DistrictSummaryResponse(BaseModel):
    district_id: int
    average_rainfall: float
    average_temperature: float
    average_humidity: float
    observation_count: int

class HistoricalTrendResponse(BaseModel):
    period: date
    average_rainfall: float
    average_temperature: float
    average_humidity: float
    observation_count: int

class DistrictComparisonResponse(BaseModel):
    district_id: int
    district_name: str
    state: str
    average_rainfall: float
    average_temperature: float
    average_humidity: float
    observation_count: int

class DistrictSummaryDetailResponse(BaseModel):
    district_id: int
    average_rainfall: float
    average_temperature: float
    average_humidity: float
    observation_count: int
    average_predicted_rainfall: float
    average_predicted_temperature: float
    forecast_count: int

class ComparisonAverages(BaseModel):
    temperature: float
    rainfall: float
    humidity: float

class ComparisonDifferences(BaseModel):
    temperature: float
    rainfall: float
    humidity: float

class DistrictComparisonDetailResponse(BaseModel):
    district_id: int
    district_name: str
    state: str
    observation_count: int
    district_averages: ComparisonAverages
    overall_averages: ComparisonAverages
    differences: ComparisonDifferences

@router.get("/district/{district_id}", response_model=DistrictSummaryResponse)
async def read_district_summary(district_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get aggregate summary stats for a single district.
    """
    # Verify district exists
    from app.services.district import DistrictService
    district = await DistrictService.get_district_by_id(db, district_id)
    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"District with ID {district_id} not found"
        )

    summary = await AnalyticsService.get_district_summary(db, district_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No climate data found for district ID {district_id}"
        )
    return summary

@router.get("/district/{district_id}/summary", response_model=Dict[str, Any])
async def read_district_summary_old(district_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get aggregate temperature, rainfall, and humidity summaries for a district.
    """
    summary = await AnalyticsService.get_district_summary(db, district_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No climate data found for district ID {district_id}"
        )
    return summary

@router.get("/state/{state}/summary", response_model=Dict[str, Any])
async def read_state_summary(state: str, db: AsyncSession = Depends(get_db)):
    """
    Get aggregate summaries across all districts in a state.
    """
    summary = await AnalyticsService.get_state_summary(db, state)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No climate data found for state '{state}'"
        )
    return summary

@router.get("/district/{district_id}/trends/rainfall", response_model=List[Dict[str, Any]])
async def read_rainfall_trends(district_id: int, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """
    Get historical rainfall data points sorted chronologically.
    """
    return await AnalyticsService.get_rainfall_trends(db, district_id, limit=limit)

@router.get("/district/{district_id}/trends/temperature", response_model=List[Dict[str, Any]])
async def read_temperature_trends(district_id: int, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """
    Get historical temperature data points sorted chronologically.
    """
    return await AnalyticsService.get_temperature_trends(db, district_id, limit=limit)

@router.get("/trends/{district_id}", response_model=List[HistoricalTrendResponse])
async def read_historical_trends(
    district_id: int,
    aggregation_level: str = Query("monthly", description="Aggregation level: weekly, monthly, or yearly"),
    start_date: date | None = Query(None, description="Start date for filtering"),
    end_date: date | None = Query(None, description="End date for filtering"),
    skip: int = Query(0, ge=0, description="Number of aggregated periods to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max number of periods to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated climate observation trends for rainfall, temperature, and humidity for a district.
    Supports weekly, monthly, and yearly aggregation, date range filtering, and pagination.
    """
    # Verify district exists
    from app.services.district import DistrictService
    district = await DistrictService.get_district_by_id(db, district_id)
    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"District with ID {district_id} not found"
        )

    try:
        return await AnalyticsService.get_historical_trends(
            db=db,
            district_id=district_id,
            aggregation_level=aggregation_level,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/comparison", response_model=List[DistrictComparisonResponse])
async def read_district_comparison(
    skip: int = Query(0, ge=0, description="Number of districts to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max number of districts to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Compare average climate metrics across districts.
    """
    return await AnalyticsService.get_district_comparison(db, skip=skip, limit=limit)

@router.get("/summary/{district_id}", response_model=DistrictSummaryDetailResponse)
async def read_district_summary_detail(district_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get detailed climate averages (observations and forecasts) for a district.
    """
    # Verify district exists
    from app.services.district import DistrictService
    district = await DistrictService.get_district_by_id(db, district_id)
    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"District with ID {district_id} not found"
        )

    summary = await AnalyticsService.get_district_summary(db, district_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No climate or forecast data found for district ID {district_id}"
        )
    return summary

@router.get("/comparison/{district_id}", response_model=DistrictComparisonDetailResponse)
async def read_district_comparison_detail(district_id: int, db: AsyncSession = Depends(get_db)):
    """
    Compare a single district's climate averages with overall averages across all districts.
    """
    try:
        return await AnalyticsService.get_district_comparison_detail(db, district_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


