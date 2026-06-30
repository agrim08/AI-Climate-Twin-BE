from pydantic import BaseModel, Field
from typing import List
from app.schemas.climate_observation import ClimateObservation
from app.schemas.forecast import Forecast
from app.schemas.simulation import SimulationResult

class DashboardOverview(BaseModel):
    total_districts: int = Field(..., description="Total number of registered districts")
    total_observations: int = Field(..., description="Total climate observations recorded")
    total_forecasts: int = Field(..., description="Total forecasts generated")
    total_simulations: int = Field(..., description="Total simulation runs executed")
    latest_observations: List[ClimateObservation] = Field(..., description="Latest recorded climate observations")
    latest_forecasts: List[Forecast] = Field(..., description="Latest generated forecasts")
    latest_simulations: List[SimulationResult] = Field(..., description="Latest climate simulation runs")
