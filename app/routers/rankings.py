"""
National Climate Intelligence Rankings Router
=============================================
Exposes district-scale climate vulnerability rankings powered by
the full ML chained pipeline (Temperature → Rainfall → Drought → Extreme Weather).
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.rankings import RankingsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rankings", tags=["Climate Intelligence Rankings"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ScenarioRankingInput(BaseModel):
    year: int = Field(2025, ge=2020, le=2100, description="Target year for projections")
    month: int = Field(6, ge=1, le=12, description="Target month (1–12)")
    temp_delta: float = Field(0.0, description="Absolute temperature change (°C)")
    rain_delta: float = Field(0.0, description="Percentage rainfall change (%)")
    sm_delta: float = Field(0.0, description="Percentage soil moisture change (%)")
    top_n: int = Field(5, ge=1, le=50, description="Number of top/bottom districts to return")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/current", status_code=status.HTTP_200_OK)
async def get_current_rankings(
    year: int = Query(2025, ge=2020, le=2100, description="Reference year"),
    month: int = Query(6, ge=1, le=12, description="Reference month"),
    top_n: int = Query(5, ge=1, le=50, description="Number of districts to return"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns Top-N most vulnerable and least vulnerable districts
    using the Hotspot Composite Score across ALL districts in the database.

    Hotspot Score = (0.25 × Drought Severity × 100)
                  + (0.25 × Heatwave Severity)
                  + (0.20 × Water Stress Index × 100)
                  + (0.15 × Crop Stress Index × 100)
                  + (0.15 × Extreme Rainfall Severity)
    """
    try:
        return await RankingsService.get_current_rankings(
            db=db, year=year, month=month, top_n=top_n
        )
    except Exception as e:
        logger.error(f"Rankings/current error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute current rankings: {str(e)}"
        )


@router.get("/year/{year}", status_code=status.HTTP_200_OK)
async def get_year_rankings(
    year: int,
    month: int = Query(6, ge=1, le=12, description="Reference month"),
    top_n: int = Query(5, ge=1, le=50, description="Number of districts to return"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns projected Top-N/Bottom-N rankings for a specified future year.
    Leverages the LookupEngine fallback (nearest historical month) for
    years beyond the dataset horizon.
    """
    try:
        return await RankingsService.get_year_rankings(
            db=db, year=year, month=month, top_n=top_n
        )
    except Exception as e:
        logger.error(f"Rankings/year/{year} error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute year {year} rankings: {str(e)}"
        )


@router.post("/scenario", status_code=status.HTTP_200_OK)
async def get_scenario_rankings(
    input_data: ScenarioRankingInput,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns district rankings under custom scenario delta inputs
    (e.g., +2°C temperature, −10% rainfall).
    """
    try:
        return await RankingsService.get_scenario_rankings(
            db=db,
            year=input_data.year,
            month=input_data.month,
            temp_delta=input_data.temp_delta,
            rain_delta=input_data.rain_delta,
            sm_delta=input_data.sm_delta,
            top_n=input_data.top_n,
        )
    except Exception as e:
        logger.error(f"Rankings/scenario error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute scenario rankings: {str(e)}"
        )


@router.get("/hotspots", status_code=status.HTTP_200_OK)
async def get_hotspots(
    year: int = Query(2025, ge=2020, le=2100, description="Reference year"),
    month: int = Query(6, ge=1, le=12, description="Reference month"),
    top_n: int = Query(10, ge=1, le=50, description="Number of hotspots to return per category"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns:
    - **Vulnerable Hotspots**: Districts in the Critical/High risk band, sorted by hotspot score.
    - **Emerging Hotspots**: Districts in the Moderate risk band, at risk of escalation.
    """
    try:
        return await RankingsService.get_hotspots(
            db=db, year=year, month=month, top_n=top_n
        )
    except Exception as e:
        logger.error(f"Rankings/hotspots error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute hotspots: {str(e)}"
        )


@router.get("/movement", status_code=status.HTTP_200_OK)
async def get_rank_movement(
    base_year: int = Query(2025, ge=2020, le=2100, description="Base year for comparison"),
    target_year: int = Query(2035, ge=2020, le=2100, description="Target year for comparison"),
    month: int = Query(6, ge=1, le=12, description="Reference month"),
    top_n: int = Query(10, ge=1, le=50, description="Number of districts per movement category"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Compares district rank positions between `base_year` and `target_year`.
    Returns districts with the largest rank deterioration and largest improvements.

    A positive `rank_change` means the district worsened (moved up in the risk ranking).
    """
    if base_year >= target_year:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="base_year must be strictly less than target_year."
        )
    try:
        return await RankingsService.get_rank_movement(
            db=db,
            base_year=base_year,
            target_year=target_year,
            month=month,
            top_n=top_n,
        )
    except Exception as e:
        logger.error(f"Rankings/movement error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute rank movement: {str(e)}"
        )


@router.get("/trends", status_code=status.HTTP_200_OK)
async def get_trends(
    base_year: int = Query(2025, ge=2020, le=2100, description="Base year for trend calculation"),
    month: int = Query(6, ge=1, le=12, description="Reference month"),
    projection_years: Optional[str] = Query(
        None,
        description="Comma-separated target projection years (e.g. '2030,2035,2040,2050'). "
                    "Defaults to 2030,2035,2040,2050 if not provided."
    ),
    top_n: int = Query(10, ge=1, le=50, description="Number of districts per trend category"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns Top-N district rankings for each climate trend dimension:
    - **Fastest Warming** (°C/year)
    - **Fastest Drought Growth** (severity delta)
    - **Fastest Water Stress Growth** (index delta)
    - **Fastest Heatwave Growth** (severity delta)
    """
    parsed_years = None
    if projection_years:
        try:
            parsed_years = [int(y.strip()) for y in projection_years.split(",") if y.strip()]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="projection_years must be a comma-separated list of integers (e.g. '2030,2035,2050')."
            )

    try:
        return await RankingsService.get_trends(
            db=db,
            base_year=base_year,
            month=month,
            projection_years=parsed_years,
            top_n=top_n,
        )
    except Exception as e:
        logger.error(f"Rankings/trends error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute trends: {str(e)}"
        )


@router.get("/emerging-risks", status_code=status.HTTP_200_OK)
async def get_emerging_risks(
    base_year: int = Query(2025, ge=2020, le=2100, description="Current reference year"),
    target_year: int = Query(2035, ge=2020, le=2100, description="Future target year"),
    month: int = Query(6, ge=1, le=12, description="Reference month"),
    top_n: int = Query(10, ge=1, le=50, description="Number of emerging risk districts to return"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns districts where the composite hotspot score is growing fastest
    — districts currently in Moderate risk but trending toward High/Critical.
    """
    if base_year >= target_year:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="base_year must be strictly less than target_year."
        )
    try:
        return await RankingsService.get_emerging_risks(
            db=db,
            base_year=base_year,
            target_year=target_year,
            month=month,
            top_n=top_n,
        )
    except Exception as e:
        logger.error(f"Rankings/emerging-risks error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute emerging risks: {str(e)}"
        )
