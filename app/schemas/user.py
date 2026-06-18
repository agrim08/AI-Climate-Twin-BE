import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.user import UserRole

class UserBase(BaseModel):
    email: EmailStr = Field(..., description="User's unique email address")
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name of the user")
    role: UserRole = Field(default=UserRole.CITIZEN, description="Assigned role")

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    email: EmailStr | None = Field(None)
    full_name: str | None = Field(None, min_length=1, max_length=255)
    role: UserRole | None = Field(None)

class User(UserBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
