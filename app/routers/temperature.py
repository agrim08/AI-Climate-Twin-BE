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
        lat = input_data.latitude
        lon = input_data.longitude
        if input_data.district_id is not None:
            try:
                lat, lon, _ = await ClimateLookup.resolve_district(db, input_data.district_id)
            except Exception:
                pass
                
        from app.utils.cache import PredictionCache
        from app.core.config import settings
        
        cache_key = PredictionCache.make_key(lat, lon, input_data.year, input_data.month)
        cached_res = PredictionCache.get_prediction(cache_key, "temperature")
        if cached_res is not None:
            return cached_res
            
        from app.ml_services.resolver import ClimateStateResolver
        full_payload = await ClimateStateResolver.resolve_state(db, input_data.model_dump(exclude_unset=True))
        pred_res = predictor.predict(full_payload)
        
        PredictionCache.set_prediction(cache_key, "temperature", pred_res, ttl=settings.CACHE_TTL)
        return pred_res
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
                    
            cache_key = PredictionCache.make_key(lat, lon, item.year, item.month)
            cached_res = PredictionCache.get_prediction(cache_key, "temperature")
            if cached_res is not None:
                results.append(cached_res)
                continue
                
            full_payload = await ClimateStateResolver.resolve_state(db, item.model_dump(exclude_unset=True))
            pred_res = predictor.predict(full_payload)
            PredictionCache.set_prediction(cache_key, "temperature", pred_res, ttl=settings.CACHE_TTL)
            results.append(pred_res)
            
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch temperature prediction failed: {str(e)}"
        )
