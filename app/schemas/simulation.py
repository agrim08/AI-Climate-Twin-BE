import uuid
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class SimulationResultBase(BaseModel):
    user_id: uuid.UUID = Field(..., description="ID of the user who ran the simulation")
    district_id: int = Field(..., description="ID of the district simulated")
    rainfall_change: float = Field(..., description="Simulated rainfall change in mm/year")
    temperature_change: float = Field(..., description="Simulated temperature change in Celsius")
    humidity_change: float = Field(..., description="Simulated humidity change percentage")
    result_json: dict = Field(..., description="Detailed simulation configuration and metrics JSON")

class SimulationResultCreate(SimulationResultBase):
    pass

class SimulationResultUpdate(BaseModel):
    user_id: uuid.UUID | None = Field(None)
    district_id: int | None = Field(None)
    rainfall_change: float | None = Field(None)
    temperature_change: float | None = Field(None)
    humidity_change: float | None = Field(None)
    result_json: dict | None = Field(None)

class SimulationResult(SimulationResultBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
