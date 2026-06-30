from pydantic import BaseModel, Field, ConfigDict

class DistrictBase(BaseModel):
    state: str = Field(..., max_length=100, examples=["Maharashtra"])
    district_name: str = Field(..., max_length=100, examples=["Pune"])
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate", examples=[18.5204])
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate", examples=[73.8567])

class DistrictCreate(DistrictBase):
    pass

class DistrictUpdate(BaseModel):
    state: str | None = Field(None, max_length=100)
    district_name: str | None = Field(None, max_length=100)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)

class District(DistrictBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
