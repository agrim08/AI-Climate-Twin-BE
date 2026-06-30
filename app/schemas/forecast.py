from datetime import date
from pydantic import BaseModel, Field, ConfigDict

class ForecastBase(BaseModel):
    district_id: int = Field(..., description="ID of the associated district")
    predicted_rainfall: float = Field(..., description="Predicted rainfall in mm", ge=0, examples=[5.2])
    predicted_temperature: float = Field(..., description="Predicted temperature in Celsius", examples=[29.4])
    forecast_date: date = Field(..., description="Forecast target date")

class ForecastCreate(ForecastBase):
    pass

class ForecastUpdate(BaseModel):
    district_id: int | None = Field(None)
    predicted_rainfall: float | None = Field(None, ge=0)
    predicted_temperature: float | None = Field(None)
    forecast_date: date | None = Field(None)

class Forecast(ForecastBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
