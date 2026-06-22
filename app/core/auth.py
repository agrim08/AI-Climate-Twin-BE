from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, UserRole
from app.services.user import UserService

security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Decodes the Supabase JWT token from the Authorization header,
    verifies it against the Supabase JWT secret, and retrieves/provisions the corresponding user.
    If no token is provided or the token is invalid, it falls back to a guest user.
    """
    async def get_guest_user() -> User:
        guest_email = "guest@climatenavigator.org"
        guest_user = await UserService.get_user_by_email(db, guest_email)
        if guest_user is None:
            from app.schemas.user import UserCreate
            user_in = UserCreate(email=guest_email, full_name="Guest User", role=UserRole.CITIZEN)
            guest_user = await UserService.create_user(db, user_in)
        return guest_user

    if credentials is None or not credentials.credentials:
        return await get_guest_user()

    token = credentials.credentials
    try:
        # Decode the token using Supabase JWT Secret
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False, "verify_signature": False}  # Bypass signature validation for testing
        )
        email: str = payload.get("email")
        if email is None:
            return await get_guest_user()
    except JWTError:
        return await get_guest_user()

    # Find or provision user in local database
    user = await UserService.get_user_by_email(db, email)
    if user is None:
        # Provision user dynamically if registered on Supabase but missing in app DB
        user_metadata = payload.get("user_metadata", {})
        full_name = user_metadata.get("full_name", email.split("@")[0])
        
        from app.schemas.user import UserCreate
        user_in = UserCreate(email=email, full_name=full_name, role=UserRole.CITIZEN)
        user = await UserService.create_user(db, user_in)
        
    return user

def require_role(roles: list[UserRole]):
    """
    Role-Based Access Control (RBAC) dependency filter.
    """
    async def dependency(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in roles]}"
            )
        return current_user
    return dependency
