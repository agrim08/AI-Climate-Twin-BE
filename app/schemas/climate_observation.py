from datetime import date
from pydantic import BaseModel, Field, ConfigDict

class ClimateObservationBase(BaseModel):
    district_id: int = Field(..., description="ID of the associated district")
    rainfall: float = Field(..., description="Rainfall in mm", ge=0, examples=[4.5])
    temperature: float = Field(..., description="Temperature in Celsius", examples=[28.6])
    humidity: float = Field(..., description="Humidity percentage", ge=0, le=100, examples=[72.0])
    observation_date: date = Field(..., description="Date of observation")

class ClimateObservationCreate(ClimateObservationBase):
    pass

class ClimateObservationUpdate(BaseModel):
    district_id: int | None = Field(None)
    rainfall: float | None = Field(None, ge=0)
    temperature: float | None = Field(None)
    humidity: float | None = Field(None, ge=0, le=100)
    observation_date: date | None = Field(None)

class ClimateObservation(ClimateObservationBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
