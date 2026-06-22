from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class DroughtInferenceInput(BaseModel):
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

    # Historical / Lag Context (With sensible defaults for standalone usage)
    temperature_prev_1: float = Field(29.0, description="Temperature of preceding month")
    temperature_prev_3: float = Field(28.0, description="Temperature of month t-3")
    rainfall_prev_1: float = Field(5.0, description="Rainfall of preceding month")
    rainfall_prev_3: float = Field(2.0, description="Rainfall of month t-3")
    soil_moisture_prev_1: float = Field(0.18, description="Soil moisture of preceding month")
    
    rolling_temp_3m: float = Field(28.5, description="3-month rolling average temperature")
    rolling_temp_6m: float = Field(25.0, description="6-month rolling average temperature")
    rolling_rainfall_3m: float = Field(15.0, description="3-month rolling average rainfall")
    rolling_rainfall_6m: float = Field(30.0, description="6-month rolling average rainfall")
    rolling_sm_3m: float = Field(0.22, description="3-month rolling average soil moisture")
    rolling_sm_6m: float = Field(0.25, description="6-month rolling average soil moisture")

    # Streaks & Persistence
    dry_month_streak: float = Field(0.0, description="Number of consecutive dry months")
    deficit_streak: float = Field(0.0, description="Number of consecutive rainfall deficit months")
    low_sm_streak: float = Field(0.0, description="Number of consecutive low soil moisture months")

    # Cumulative Deficits
    cumulative_deficit_3m: float = Field(-10.0, description="Cumulative rainfall deficit over 3 months")
    cumulative_deficit_6m: float = Field(-25.0, description="Cumulative rainfall deficit over 6 months")
    cumulative_sm_deficit_3m: float = Field(0.05, description="Cumulative soil moisture deficit over 3 months")
    cumulative_sm_deficit_6m: float = Field(0.10, description="Cumulative soil moisture deficit over 6 months")

    # Climatology Baselines
    rainfall_climatology: float = Field(12.0, description="Historical climatology mean rainfall for the month")
    rainfall_climatology_std: float = Field(5.0, description="Historical rainfall standard deviation")
    sm_climatology: float = Field(0.25, description="Historical climatology mean soil moisture")
    sm_climatology_std: float = Field(0.05, description="Historical soil moisture standard deviation")
    temperature_climatology: float = Field(28.0, description="Historical climatology mean temperature")
    temperature_climatology_std: float = Field(2.0, description="Historical temperature standard deviation")
    lag1_climatology: float = Field(10.0, description="Historical climatology mean rainfall for preceding month")

    # Zone Baselines
    zone_rain_climatology: float = Field(10.0, description="Regional zone baseline rainfall")
    zone_rain_climatology_std: float = Field(4.0, description="Regional zone rainfall standard deviation")
    zone_sm_climatology: float = Field(0.20, description="Regional zone baseline soil moisture")
    zone_sm_climatology_std: float = Field(0.04, description="Regional zone soil moisture standard deviation")
    zone_aridity_index: float = Field(1.5, description="Regional zone aridity index")

    # Scenario delta modifiers
    temperature_delta: float = Field(0.0, description="Temperature anomaly delta (°C) for simulation")
    rainfall_delta: float = Field(0.0, description="Rainfall percentage change delta (%) for simulation")
    soil_moisture_delta: float = Field(0.0, description="Soil moisture percentage change delta (%) for simulation")
    evaporation_delta: float = Field(0.0, description="Evaporation percentage change delta (%) for simulation")
    runoff_delta: float = Field(0.0, description="Runoff percentage change delta (%) for simulation")

    # Additional metadata
    climate_zone: str = Field("Indo-Gangetic Plains", description="Regional climate zone name")
    drought_acceleration: float = Field(0.0, description="Short-term acceleration index")
    deficit_volatility_3m: float = Field(5.0, description="Rainfall deficit volatility over 3 months")


class DroughtPredictionResponse(BaseModel):
    drought_category: str = Field(..., description="Predicted drought class: Low, Medium, High, Extreme")
    severity_score: float = Field(..., description="Continuous drought risk/severity score (0.0 to 1.0)")
    drought_risk_score: float = Field(..., description="Alias/backwards-compatible risk score (0.0 to 1.0)")
    confidence_score: float = Field(..., description="Probability of the predicted class (0.0 to 1.0)")
    confidence_level: str = Field(..., description="Confidence level: High, Medium, Low")
    probabilities: Dict[str, float] = Field(..., description="Probability distribution across all categories")
    source: Optional[str] = Field(None, description="Source of weather input: LIVE, DATABASE, or HISTORICAL")
    confidence_source: Optional[float] = Field(None, description="Confidence score of the data source")
    last_updated: Optional[str] = Field(None, description="Timestamp or date when the source was last updated")


class ScenarioSimulationResponse(BaseModel):
    baseline_category: str = Field(..., description="Drought category under baseline conditions")
    baseline_score: float = Field(..., description="Drought severity/risk score under baseline conditions")
    scenario_category: str = Field(..., description="Drought category under simulated scenario conditions")
    scenario_score: float = Field(..., description="Drought severity/risk score under simulated scenario conditions")
    risk_change: str = Field(..., description="Relative level difference (e.g. +2 levels, -1 level, No change)")


class DriverAnalysisResponse(BaseModel):
    top_drivers: List[str] = Field(..., description="List of strongest active drought drivers, in descending order of influence")


class WaterStressResponse(BaseModel):
    water_stress_index: float = Field(..., description="Hydrological water stress index (0-100)")
    reservoir_risk: str = Field(..., description="Assessed risk level for reservoirs (Low, Medium, High, Critical)")
    groundwater_risk: str = Field(..., description="Assessed risk level for groundwater aquifers (Low, Medium, High, Critical)")
    water_availability_status: str = Field(..., description="Qualitative status (Abundant, Sufficient, Stressed, Deficit)")


class AgriculturalStressResponse(BaseModel):
    crop_stress_index: float = Field(..., description="Agricultural crop health stress index (0-100)")
    irrigation_need: str = Field(..., description="Assessed irrigation urgency level (Low, Medium, High, Critical)")
    agricultural_risk: str = Field(..., description="Assessed risk level for agricultural yield (Low, Medium, High, Critical)")


class EarlyWarningResponse(BaseModel):
    warning: bool = Field(..., description="Indicator if a drought alert warning is active")
    warning_level: str = Field(..., description="Warning priority level (Low, Medium, High, Critical)")
    message: str = Field(..., description="Actionable alert warning notification message")


class DroughtTwinStateResponse(BaseModel):
    drought_prediction: DroughtPredictionResponse = Field(..., description="Core drought category and score prediction outputs")
    scenario_analysis: ScenarioSimulationResponse = Field(..., description="Drought simulation analysis comparison (baseline vs scenario)")
    drivers: DriverAnalysisResponse = Field(..., description="Identify key driver indicators for the current prediction")
    water_intelligence: WaterStressResponse = Field(..., description="Water resource stress and risk assessments")
    agriculture_intelligence: AgriculturalStressResponse = Field(..., description="Agricultural stress, risk, and crop indicators")
    early_warning: EarlyWarningResponse = Field(..., description="Drought early warning triggering and messages")
    source: Optional[str] = Field(None, description="Source of weather input: LIVE, DATABASE, or HISTORICAL")
    confidence_source: Optional[float] = Field(None, description="Confidence score of the data source")
    last_updated: Optional[str] = Field(None, description="Timestamp or date when the source was last updated")
