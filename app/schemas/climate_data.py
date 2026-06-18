from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class ClimateRecordBase(BaseModel):
    location: str = Field(..., max_length=100, examples=["New Delhi"])
    state: str = Field(..., max_length=100, examples=["Delhi"])
    temperature: float = Field(..., description="Temperature in Celsius", examples=[32.5])
    humidity: float = Field(..., description="Humidity percentage", ge=0, le=100, examples=[65.0])
    precipitation: float = Field(..., description="Precipitation in mm", ge=0, examples=[12.4])

class ClimateRecordCreate(ClimateRecordBase):
    recorded_at: datetime | None = Field(default=None, description="Time of observation (UTC)")

class ClimateRecordUpdate(BaseModel):
    location: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    temperature: float | None = Field(None)
    humidity: float | None = Field(None, ge=0, le=100)
    precipitation: float | None = Field(None, ge=0)
    recorded_at: datetime | None = Field(None)

class ClimateRecord(ClimateRecordBase):
    id: int
    recorded_at: datetime

    # config option to support SQLAlchemy lazy-loading and attribute mapping (from_attributes replaces Pydantic v1's orm_mode=True)
    model_config = ConfigDict(from_attributes=True)
