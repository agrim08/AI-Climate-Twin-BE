from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.ml_services.predict_temperature import TemperaturePredictor
from app.ml_services.lookup import ClimateLookup
from app.schemas.temperature import (
    TemperatureInferenceInput,
    TemperaturePredictionResponse
)

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/temperature", tags=["Temperature Intelligence"])

# Instantiate the predictor once at startup
try:
    predictor = TemperaturePredictor()
except Exception as e:
    logger.critical(f"Failed to initialize TemperaturePredictor at router level: {str(e)}")
    predictor = None


@router.post("/predict", response_model=TemperaturePredictionResponse, status_code=status.HTTP_200_OK)
async def predict_temperature(input_data: TemperatureInferenceInput, db: AsyncSession = Depends(get_db)):
    """
    Predict monthly mean temperature and confidence indicators for a single location state.
    """
    if not predictor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Temperature model is not loaded/available."
        )
    try:
        full_payload = await ClimateLookup.get_lookup_state(db, input_data.model_dump(exclude_unset=True))
        return predictor.predict(full_payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Temperature prediction failed: {str(e)}"
        )


@router.post("/predict/batch", response_model=List[TemperaturePredictionResponse], status_code=status.HTTP_200_OK)
async def predict_temperature_batch(input_data: List[TemperatureInferenceInput], db: AsyncSession = Depends(get_db)):
    """
    Optimized batch predictions for multiple locations or timeframes at once.
    """
    if not predictor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Temperature model is not loaded/available."
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
            detail=f"Batch temperature prediction failed: {str(e)}"
        )
