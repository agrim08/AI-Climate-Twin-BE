from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.ml_services.predict_rainfall import RainfallPredictor
from app.ml_services.lookup import ClimateLookup
from app.schemas.rainfall import (
    RainfallInferenceInput,
    RainfallPredictionResponse
)

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/rainfall", tags=["Rainfall Intelligence"])

# Instantiate the predictor once at startup
try:
    predictor = RainfallPredictor()
except Exception as e:
    logger.critical(f"Failed to initialize RainfallPredictor at router level: {str(e)}")
    predictor = None


@router.post("/predict", response_model=RainfallPredictionResponse, status_code=status.HTTP_200_OK)
async def predict_rainfall(input_data: RainfallInferenceInput, db: AsyncSession = Depends(get_db)):
    """
    Predict monthly rainfall accumulation and confidence indicators for a single location state.
    """
    if not predictor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rainfall model is not loaded/available."
        )
    try:
        full_payload = await ClimateLookup.get_lookup_state(db, input_data.model_dump(exclude_unset=True))
        return predictor.predict(full_payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rainfall prediction failed: {str(e)}"
        )


@router.post("/predict/batch", response_model=List[RainfallPredictionResponse], status_code=status.HTTP_200_OK)
async def predict_rainfall_batch(input_data: List[RainfallInferenceInput], db: AsyncSession = Depends(get_db)):
    """
    Optimized batch predictions for multiple locations or timeframes at once.
    """
    if not predictor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rainfall model is not loaded/available."
        )
    try:
        resolved_requests = []
        for item in input_data:
            resolved_req = await ClimateLookup.get_lookup_state(db, item.model_dump(exclude_unset=True))
            resolved_requests.append(resolved_req)
        return predictor.batch_predict(resolved_requests)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch rainfall prediction failed: {str(e)}"
        )
