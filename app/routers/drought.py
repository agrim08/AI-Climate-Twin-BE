from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.ml_services.predict_drought import DroughtPredictor
from app.ml_services.lookup import ClimateLookup
from app.schemas.drought import (
    DroughtInferenceInput,
    DroughtPredictionResponse,
    ScenarioSimulationResponse,
    DroughtTwinStateResponse
)

# Initialize router
router = APIRouter(prefix="/drought", tags=["Drought Intelligence"])

# Instantiate the predictor once at startup
try:
    predictor = DroughtPredictor()
except Exception as e:
    # We log the error and allow router to load but prediction calls will fail
    import logging
    logger = logging.getLogger(__name__)
    logger.critical(f"Failed to initialize DroughtPredictor at router level: {str(e)}")
    predictor = None


@router.post("/predict", response_model=DroughtPredictionResponse, status_code=status.HTTP_200_OK)
async def predict_drought(input_data: DroughtInferenceInput, db: AsyncSession = Depends(get_db)):
    """
    Predict drought category, probabilities, and class probability-based confidence indicators
    for a single location state.
    """
    if not predictor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Drought model is not loaded/available."
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
            sm_delta=input_data.soil_moisture_delta,
            evap_delta=input_data.evaporation_delta,
            ro_delta=input_data.runoff_delta
        )
        cached_res = PredictionCache.get_prediction(cache_key, "drought")
        if cached_res is not None:
            return cached_res
            
        from app.ml_services.resolver import ClimateStateResolver
        full_payload = await ClimateStateResolver.resolve_state(db, input_data.model_dump(exclude_unset=True))
        pred_res = predictor.predict(full_payload)
        
        PredictionCache.set_prediction(cache_key, "drought", pred_res, ttl=settings.CACHE_TTL)
        return pred_res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Drought prediction failed: {str(e)}"
        )


@router.post("/predict/batch", response_model=List[DroughtPredictionResponse], status_code=status.HTTP_200_OK)
async def predict_drought_batch(input_data: List[DroughtInferenceInput], db: AsyncSession = Depends(get_db)):
    """
    Optimized batch drought predictions for multiple locations or timeframes at once.
    """
    if not predictor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Drought model is not loaded/available."
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
                sm_delta=item.soil_moisture_delta,
                evap_delta=item.evaporation_delta,
                ro_delta=item.runoff_delta
            )
            cached_res = PredictionCache.get_prediction(cache_key, "drought")
            if cached_res is not None:
                results.append(cached_res)
                continue
                
            full_payload = await ClimateStateResolver.resolve_state(db, item.model_dump(exclude_unset=True))
            pred_res = predictor.predict(full_payload)
            PredictionCache.set_prediction(cache_key, "drought", pred_res, ttl=settings.CACHE_TTL)
            results.append(pred_res)
            
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch drought prediction failed: {str(e)}"
        )


@router.post("/simulate", response_model=ScenarioSimulationResponse, status_code=status.HTTP_200_OK)
async def simulate_drought_scenario(input_data: DroughtInferenceInput, db: AsyncSession = Depends(get_db)):
    """
    Run a comparative drought scenario simulation comparing baseline (deltas=0) vs scenario modified conditions.
    Utilizes preferred chained Digital Twin prediction (Temperature Model -> Rainfall Model -> Drought Model)
    if available, with fallback to direct delta modification.
    """
    if not predictor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Drought model is not loaded/available."
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
            sm_delta=input_data.soil_moisture_delta,
            evap_delta=input_data.evaporation_delta,
            ro_delta=input_data.runoff_delta
        )
        cached_res = PredictionCache.get_prediction(cache_key, "drought_simulation")
        if cached_res is not None:
            return cached_res
            
        from app.ml_services.resolver import ClimateStateResolver
        full_payload = await ClimateStateResolver.resolve_state(db, input_data.model_dump(exclude_unset=True))
        pred_res = predictor.simulate_scenario(full_payload)
        
        PredictionCache.set_prediction(cache_key, "drought_simulation", pred_res, ttl=settings.CACHE_TTL)
        return pred_res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scenario simulation failed: {str(e)}"
        )


@router.post("/twin-state", response_model=DroughtTwinStateResponse, status_code=status.HTTP_200_OK)
async def get_drought_twin_state(input_data: DroughtInferenceInput, db: AsyncSession = Depends(get_db)):
    """
    Unified Digital Twin call. Returns the complete Drought Intelligence state (predictions,
    scenario comparison, drivers, water intelligence, agricultural risk, and early warning warnings)
    in a single combined payload.
    """
    if not predictor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Drought model is not loaded/available."
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
            sm_delta=input_data.soil_moisture_delta,
            evap_delta=input_data.evaporation_delta,
            ro_delta=input_data.runoff_delta
        )
        cached_res = PredictionCache.get_prediction(cache_key, "drought_twin_state")
        if cached_res is not None:
            return cached_res
            
        from app.ml_services.resolver import ClimateStateResolver
        full_payload = await ClimateStateResolver.resolve_state(db, input_data.model_dump(exclude_unset=True))
        pred_res = predictor.get_digital_twin_state(full_payload)
        
        PredictionCache.set_prediction(cache_key, "drought_twin_state", pred_res, ttl=settings.CACHE_TTL)
        return pred_res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Digital Twin state: {str(e)}"
        )
