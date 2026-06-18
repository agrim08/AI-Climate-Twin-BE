from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import require_role
from app.models.user import User, UserRole
from app.services.climate_ingestion import ClimateIngestionService

router = APIRouter(prefix="/climate", tags=["Climate Ingestion"])

@router.post("/fetch/{district_id}", status_code=status.HTTP_200_OK)
async def fetch_district_climate(
    district_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.RESEARCHER]))
):
    """
    Fetch weather data from Open-Meteo for a specific district and save past observations.
    Requires Bearer token authentication with admin or researcher role.
    """
    try:
        return await ClimateIngestionService.fetch_and_store_district_climate(db, district_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/fetch-all", status_code=status.HTTP_200_OK)
async def fetch_all_districts_climate(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.RESEARCHER]))
):
    """
    Fetch weather data from Open-Meteo for all districts and save past observations.
    Requires Bearer token authentication with admin or researcher role.
    """
    try:
        return await ClimateIngestionService.fetch_and_store_all_districts_climate(db)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
