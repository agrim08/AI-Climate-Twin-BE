import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from app.core.config import settings
from app.core.database import get_db
from app.core.auth import get_current_user
from app.schemas.user import User, UserCreate
from app.models.user import UserRole

router = APIRouter(prefix="/auth", tags=["Authentication"])

class UserSignup(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.CITIZEN

class UserLogin(BaseModel):
    email: EmailStr
    password: str

@router.post("/signup", response_model=User)
async def signup(user_in: UserSignup, db: AsyncSession = Depends(get_db)):
    """
    Register a new user in Supabase Auth and provision them in the local database.
    Falls back to direct local registration if Supabase keys are placeholders or fail.
    """
    use_mock = settings.SUPABASE_ANON_KEY == "your-supabase-anon-key" or "your-supabase-project-id" in settings.SUPABASE_URL
    
    if not use_mock:
        try:
            # 1. Call Supabase Auth API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.SUPABASE_URL}/auth/v1/signup",
                    headers={"apikey": settings.SUPABASE_ANON_KEY, "Content-Type": "application/json"},
                    json={
                        "email": user_in.email,
                        "password": user_in.password,
                        "options": {
                            "data": {
                                "full_name": user_in.full_name
                            }
                        }
                    }
                )
                if response.status_code != 200:
                    # Check if invalid credentials error, otherwise fall back to mock
                    if response.status_code == 401 or response.status_code == 403:
                        use_mock = True
                    else:
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=response.json().get("msg", "Failed to sign up in Supabase")
                        )
        except Exception as e:
            print(f"Supabase connection failed, entering local mock auth: {e}")
            use_mock = True
            
    # 2. Sync to local database
    from app.services.user import UserService
    db_user = await UserService.get_user_by_email(db, user_in.email)
    if not db_user:
        local_user_in = UserCreate(email=user_in.email, full_name=user_in.full_name, role=user_in.role)
        db_user = await UserService.create_user(db, local_user_in)
        
    return db_user

@router.post("/login")
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Log in a user via Supabase Auth and return access token JWTs.
    Falls back to local JWT issuance if Supabase credentials are missing or fail.
    """
    use_mock = settings.SUPABASE_ANON_KEY == "your-supabase-anon-key" or "your-supabase-project-id" in settings.SUPABASE_URL
    
    if not use_mock:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
                    headers={"apikey": settings.SUPABASE_ANON_KEY, "Content-Type": "application/json"},
                    json={
                        "email": user_in.email,
                        "password": user_in.password
                    }
                )
                if response.status_code == 200:
                    return response.json()
                elif response.status_code in [401, 403, 400]:
                    # Let Supabase credentials fail natively if we have valid configs
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=response.json().get("error_description", "Invalid login credentials")
                    )
        except HTTPException:
            raise
        except Exception as e:
            print(f"Supabase connection failed on login, entering local mock auth: {e}")
            use_mock = True

    if use_mock:
        from app.services.user import UserService
        db_user = await UserService.get_user_by_email(db, user_in.email)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid login credentials (local user not found)"
            )
        
        # Issue a mock Supabase JWT token locally
        from jose import jwt
        from datetime import datetime, timedelta
        
        token_data = {
            "sub": str(db_user.id),
            "email": db_user.email,
            "role": db_user.role.value if hasattr(db_user.role, "value") else db_user.role,
            "user_metadata": {
                "full_name": db_user.full_name
            },
            "exp": datetime.utcnow() + timedelta(days=1)
        }
        
        # Sign token using the secret configured in settings
        token = jwt.encode(token_data, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": db_user.id,
                "email": db_user.email,
                "user_metadata": {
                    "full_name": db_user.full_name
                }
            }
        }


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Retrieve the current logged-in user details.
    """
    return current_user
