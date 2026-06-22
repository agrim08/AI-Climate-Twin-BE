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
        lat = input_data.latitude
        lon = input_data.longitude
        if input_data.district_id is not None:
            try:
                lat, lon, _ = await ClimateLookup.resolve_district(db, input_data.district_id)
            except Exception:
                pass
                
        from app.utils.cache import PredictionCache
        from app.core.config import settings
        
        cache_key = PredictionCache.make_key(
            lat, lon, input_data.year, input_data.month,
            temp_delta=input_data.temperature_delta,
            rain_delta=input_data.rainfall_delta,
            sm_delta=input_data.soil_moisture_delta
        )
        cached_res = PredictionCache.get_prediction(cache_key, "rainfall")
        if cached_res is not None:
            return cached_res
            
        from app.ml_services.resolver import ClimateStateResolver
        full_payload = await ClimateStateResolver.resolve_state(db, input_data.model_dump(exclude_unset=True))
        pred_res = predictor.predict(full_payload)
        
        PredictionCache.set_prediction(cache_key, "rainfall", pred_res, ttl=settings.CACHE_TTL)
        return pred_res
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
        from app.utils.cache import PredictionCache
        from app.core.config import settings
        from app.ml_services.resolver import ClimateStateResolver
        
        results = []
        for item in input_data:
            lat = item.latitude
            lon = item.longitude
            if item.district_id is not None:
                try:
                    lat, lon, _ = await ClimateLookup.resolve_district(db, item.district_id)
                except Exception:
                    pass
                    
            cache_key = PredictionCache.make_key(
                lat, lon, item.year, item.month,
                temp_delta=item.temperature_delta,
                rain_delta=item.rainfall_delta,
                sm_delta=item.soil_moisture_delta
            )
            cached_res = PredictionCache.get_prediction(cache_key, "rainfall")
            if cached_res is not None:
                results.append(cached_res)
                continue
                
            full_payload = await ClimateStateResolver.resolve_state(db, item.model_dump(exclude_unset=True))
            pred_res = predictor.predict(full_payload)
            PredictionCache.set_prediction(cache_key, "rainfall", pred_res, ttl=settings.CACHE_TTL)
            results.append(pred_res)
            
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch rainfall prediction failed: {str(e)}"
        )
