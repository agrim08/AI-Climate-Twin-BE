from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class ExtremeWeatherInferenceInput(BaseModel):
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

    # Scenario delta modifiers
    temperature_delta: float = Field(0.0, description="Temperature anomaly delta (°C) for simulation")
    rainfall_delta: float = Field(0.0, description="Rainfall percentage change delta (%) for simulation")
    soil_moisture_delta: float = Field(0.0, description="Soil moisture percentage change delta (%) for simulation")
    evaporation_delta: float = Field(0.0, description="Evaporation percentage change delta (%) for simulation")
    runoff_delta: float = Field(0.0, description="Runoff percentage change delta (%) for simulation")

    # Additional metadata
    climate_zone: str = Field("Indo-Gangetic Plains", description="Regional climate zone name")


class WeatherPredictorOutput(BaseModel):
    category: str = Field(..., description="Predicted risk category: Low, Medium, High, Extreme")
    severity: float = Field(..., description="Continuous severity score scaled 0-100")
    confidence: float = Field(..., description="Model classification probability of predicted category")


class ExtremeWeatherPredictionResponse(BaseModel):
    heatwave: WeatherPredictorOutput = Field(..., description="Heatwave classification & severity predictions")
    extreme_rainfall: WeatherPredictorOutput = Field(..., description="Extreme rainfall classification & severity predictions")
    source: Optional[str] = Field(None, description="Source of weather input: LIVE, DATABASE, or HISTORICAL")
    confidence_source: Optional[float] = Field(None, description="Confidence score of the data source")
    last_updated: Optional[str] = Field(None, description="Timestamp or date when the source was last updated")


class OverallRiskResponse(BaseModel):
    overall_extreme_weather_risk: str = Field(..., description="Aggregated risk category: Low, Medium, High, Extreme")
    overall_risk_score: float = Field(..., description="Aggregated risk score (0 to 100)")


class ScenarioSimulationResponse(BaseModel):
    baseline_risk: str = Field(..., description="Overall risk category under baseline conditions")
    baseline_score: float = Field(..., description="Overall risk score under baseline conditions")
    scenario_risk: str = Field(..., description="Overall risk category under simulated scenario conditions")
    scenario_score: float = Field(..., description="Overall risk score under simulated scenario conditions")
    risk_change: str = Field(..., description="Relative risk levels difference (e.g. +2 levels, No change)")
    baseline_heatwave_severity: float = Field(..., description="Baseline heatwave severity score")
    scenario_heatwave_severity: float = Field(..., description="Simulated scenario heatwave severity score")
    baseline_rainfall_severity: float = Field(..., description="Baseline rainfall severity score")
    scenario_rainfall_severity: float = Field(..., description="Simulated scenario rainfall severity score")


class HeatwaveImpactResponse(BaseModel):
    health_risk: str = Field(..., description="Public health threat level (Low, Medium, High, Extreme)")
    outdoor_exposure_risk: str = Field(..., description="Outdoor safety threshold category (Low, Medium, High, Extreme)")
    heat_alert_level: str = Field(..., description="Color-coded public alarm level (Green, Yellow, Orange, Red)")
    recommendations: List[str] = Field(..., description="Health advisory recommendations")


class ExtremeRainfallImpactResponse(BaseModel):
    flash_flood_risk: str = Field(..., description="Flash flooding probability risk (Low, Medium, High, Extreme)")
    surface_runoff_risk: str = Field(..., description="Water runoff hazard risk (Low, Medium, High, Extreme)")
    drainage_overload_risk: str = Field(..., description="Urban drainage threat level (Low, Medium, High, Extreme)")
    recommendations: List[str] = Field(..., description="Disaster safety recommendations")


class ImpactAssessmentResponse(BaseModel):
    heatwave_impact: HeatwaveImpactResponse = Field(..., description="Heatwave socio-health impact assessment")
    rainfall_impact: ExtremeRainfallImpactResponse = Field(..., description="Extreme rainfall hydrological impact assessment")


class DriverAnalysisResponse(BaseModel):
    top_drivers: List[str] = Field(..., description="Identified drivers ordered by local contribution weight")


class EarlyWarningResponse(BaseModel):
    warning: bool = Field(..., description="True if an extreme hazard alert is active")
    warning_level: str = Field(..., description="Priority level (Low, Medium, High, Critical)")
    event_type: str = Field(..., description="Trigger hazard type (None, Heatwave, Extreme Rainfall, Compound)")
    message: str = Field(..., description="Actionable early warning message notification")


class ExtremeWeatherTwinStateResponse(BaseModel):
    heatwave_prediction: WeatherPredictorOutput = Field(..., description="Heatwave predictor outcome")
    rainfall_extreme_prediction: WeatherPredictorOutput = Field(..., description="Extreme rainfall predictor outcome")
    overall_extreme_weather: OverallRiskResponse = Field(..., description="Combined multi-hazard risk layer")
    scenario_analysis: ScenarioSimulationResponse = Field(..., description="Scenario testing delta simulator output")
    driver_analysis: DriverAnalysisResponse = Field(..., description="Strongest driver factors identification")
    impact_assessment: ImpactAssessmentResponse = Field(..., description="Socio-economic public-health impact advisory")
    early_warning: EarlyWarningResponse = Field(..., description="Multi-level emergency alerts trigger")
    source: Optional[str] = Field(None, description="Source of weather input: LIVE, DATABASE, or HISTORICAL")
    confidence_source: Optional[float] = Field(None, description="Confidence score of the data source")
    last_updated: Optional[str] = Field(None, description="Timestamp or date when the source was last updated")
