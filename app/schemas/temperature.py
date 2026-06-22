from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class TemperatureInferenceInput(BaseModel):
    # Optional Database Resolution
    district_id: Optional[int] = Field(None, description="Optional District ID to load coordinate/climate state from database")
    use_live: Optional[bool] = Field(False, description="Whether to optionally resolve the latest live/database climate state")

    # Core Climate State Variables
    latitude: float = Field(20.0, description="Latitude of the target location")
    longitude: float = Field(80.0, description="Longitude of the target location")
    year: int = Field(2024, description="Target calendar year")
    month: int = Field(6, description="Target calendar month (1-12)")
    temperature_c: float = Field(30.0, description="Monthly mean temperature in Celsius")
    rainfall_mm: float = Field(10.0, description="Monthly rainfall accumulation in mm")
    soil_moisture: float = Field(0.2, description="Mean soil moisture content (0.0 to 1.0)")
    evabs: float = Field(-0.001, description="Mean evaporation flux (typically negative)")
    sro: float = Field(0.001, description="Surface runoff in mm/month")

    # Historical / Lag Context
    temperature_prev_1: float = Field(29.0, description="Temperature of preceding month")
    temperature_prev_3: float = Field(28.0, description="Temperature of month t-3")
    rainfall_prev_1: float = Field(5.0, description="Rainfall of preceding month")
    rainfall_prev_3: float = Field(2.0, description="Rainfall of month t-3")
    soil_moisture_prev_1: float = Field(0.18, description="Soil moisture of preceding month")
    
    rolling_temp_3m: float = Field(28.5, description="3-month rolling average temperature")
    rolling_temp_6m: float = Field(25.0, description="6-month rolling average temperature")
    rolling_rainfall_3m: float = Field(15.0, description="3-month rolling average rainfall")
    rolling_rainfall_6m: float = Field(30.0, description="6-month rolling average rainfall")

    # Climatologies (city × month level)
    temp_climo_mean: float = Field(28.0, description="Historical climatology mean temperature for the month")
    temp_climo_std: float = Field(2.0, description="Historical temperature standard deviation")
    rain_climo_mean: float = Field(12.0, description="Historical climatology mean rainfall for the month")
    rain_climo_std: float = Field(5.0, description="Historical rainfall standard deviation")
    sm_climo_mean: float = Field(0.25, description="Historical climatology mean soil moisture")
    sm_climo_std: float = Field(0.05, description="Historical soil moisture standard deviation")

    # Zone Climatologies (zone × month level)
    zone_temp_mean: float = Field(28.0, description="Zone monthly average temperature")
    zone_temp_std: float = Field(2.0, description="Zone temperature standard deviation")
    zone_rain_mean: float = Field(12.0, description="Zone monthly average rainfall")
    zone_rain_std: float = Field(5.0, description="Zone rainfall standard deviation")

    # India-wide seasonal baseline
    seasonal_temp_mean: float = Field(28.0, description="India-wide baseline temperature for the month")
    seasonal_rain_mean: float = Field(12.0, description="India-wide baseline rainfall for the month")

    # Streaks / Persistence
    consecutive_hot_months: float = Field(0.0, description="Consecutive hot months streak")
    consecutive_wet_months: float = Field(0.0, description="Consecutive wet months streak")

    # Additional metadata
    climate_zone: str = Field("Indo-Gangetic Plains", description="Regional climate zone name")


class TemperaturePredictionResponse(BaseModel):
    predicted_temperature_c: float = Field(..., description="Predicted monthly mean temperature in Celsius")
    confidence: str = Field(..., description="Prediction confidence level: low, medium, high")
    model_rmse_c: float = Field(..., description="Root Mean Squared Error of the model on validation data")
    source: Optional[str] = Field(None, description="Source of weather input: LIVE, DATABASE, or HISTORICAL")
    confidence_source: Optional[float] = Field(None, description="Confidence score of the data source")
    last_updated: Optional[str] = Field(None, description="Timestamp or date when the source was last updated")
