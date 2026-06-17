from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.dashboard import DashboardOverview
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Public Dashboard"])

@router.get("/overview", response_model=DashboardOverview)
async def read_dashboard_overview(db: AsyncSession = Depends(get_db)):
    """
    Get overview metrics and latest records for the public dashboard.
    """
    return await DashboardService.get_overview(db)
