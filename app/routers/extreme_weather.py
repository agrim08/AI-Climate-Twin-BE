from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.ml_services.predict_extreme_weather import ExtremeWeatherPredictor
from app.ml_services.lookup import ClimateLookup
from app.schemas.extreme_weather import (
    ExtremeWeatherInferenceInput,
    ExtremeWeatherPredictionResponse,
    ScenarioSimulationResponse,
    ExtremeWeatherTwinStateResponse
)

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/extreme-weather", tags=["Extreme Weather Intelligence"])

# Instantiate the predictor once at startup
try:
    predictor = ExtremeWeatherPredictor()
except Exception as e:
    logger.critical(f"Failed to initialize ExtremeWeatherPredictor at router level: {str(e)}")
    predictor = None


@router.post("/predict", response_model=ExtremeWeatherPredictionResponse, status_code=status.HTTP_200_OK)
async def predict_extreme_weather(input_data: ExtremeWeatherInferenceInput, db: AsyncSession = Depends(get_db)):
    """
    Predict heatwave and extreme rainfall categories and severities for a single location state.
    """
    if not predictor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Extreme weather models are not loaded/available."
        )
    try:
        full_payload = await ClimateLookup.get_lookup_state(db, input_data.model_dump(exclude_unset=True))
        # Strip out private keys that are used for internal metrics cascading
        res = predictor.predict(full_payload, apply_deltas=True)
        res["heatwave"].pop("_probabilities", None)
        res["heatwave"].pop("_features", None)
        res["extreme_rainfall"].pop("_probabilities", None)
        res["extreme_rainfall"].pop("_features", None)
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extreme weather prediction failed: {str(e)}"
        )


@router.post("/predict/batch", response_model=List[ExtremeWeatherPredictionResponse], status_code=status.HTTP_200_OK)
async def predict_extreme_weather_batch(input_data: List[ExtremeWeatherInferenceInput], db: AsyncSession = Depends(get_db)):
    """
    Optimized batch predictions for multiple locations or timeframes at once.
    """
    if not predictor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Extreme weather models are not loaded/available."
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
            detail=f"Batch extreme weather prediction failed: {str(e)}"
        )


@router.post("/simulate", response_model=ScenarioSimulationResponse, status_code=status.HTTP_200_OK)
async def simulate_extreme_weather_scenario(input_data: ExtremeWeatherInferenceInput, db: AsyncSession = Depends(get_db)):
    """
    Run comparative scenario simulation comparing baseline (deltas=0) vs simulated conditions.
    Utilizes preferred chained Digital Twin prediction (Temperature Model -> Rainfall Model -> Extreme Weather Models)
    if available, with fallback to direct delta modification.
    """
    if not predictor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Extreme weather models are not loaded/available."
        )
    try:
        full_payload = await ClimateLookup.get_lookup_state(db, input_data.model_dump(exclude_unset=True))
        return predictor.simulate_scenario(full_payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scenario simulation failed: {str(e)}"
        )


@router.post("/twin-state", response_model=ExtremeWeatherTwinStateResponse, status_code=status.HTTP_200_OK)
async def get_extreme_weather_twin_state(input_data: ExtremeWeatherInferenceInput, db: AsyncSession = Depends(get_db)):
    """
    Unified Digital Twin call. Returns the complete Extreme Weather state (predictions,
    scenario comparison, drivers, public-health/hydrological impacts, and early warning alert)
    in a single combined payload.
    """
    if not predictor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Extreme weather models are not loaded/available."
        )
    try:
        full_payload = await ClimateLookup.get_lookup_state(db, input_data.model_dump(exclude_unset=True))
        return predictor.get_digital_twin_state(full_payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Digital Twin state: {str(e)}"
        )
