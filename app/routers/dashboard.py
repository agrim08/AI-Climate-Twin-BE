from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List

from app.core.database import get_db
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Public Dashboard"])

class HottestDistrictDetail(BaseModel):
    district_id: int
    district_name: str
    state: str
    average_temperature: float

class RainfallDistrictDetail(BaseModel):
    district_id: int
    district_name: str
    state: str
    average_rainfall: float

class ColdestDistrictDetail(BaseModel):
    district_id: int
    district_name: str
    state: str
    average_temperature: float

class PublicDashboardOverview(BaseModel):
    total_districts: int
    total_observations: int
    latest_forecasts_count: int
    latest_simulations_count: int
    top_5_hottest_districts: List[HottestDistrictDetail]
    top_5_coldest_districts: List[ColdestDistrictDetail]
    top_5_highest_rainfall_districts: List[RainfallDistrictDetail]

@router.get("/overview", response_model=PublicDashboardOverview)
async def read_dashboard_overview(db: AsyncSession = Depends(get_db)):
    """
    Get overview metrics and top-performing/extreme climate districts for the public dashboard.
    """
    return await DashboardService.get_public_overview(db)

