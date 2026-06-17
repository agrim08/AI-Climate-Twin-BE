import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.schemas.user import User, UserCreate, UserUpdate
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/", response_model=List[User])
async def read_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await UserService.get_users(db, skip=skip, limit=limit)

@router.get("/{user_id}", response_model=User)
async def read_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return user

@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await UserService.get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    return await UserService.create_user(db, user_in)

@router.put("/{user_id}", response_model=User)
async def update_user(user_id: uuid.UUID, user_in: UserUpdate, db: AsyncSession = Depends(get_db)):
    user = await UserService.update_user(db, user_id, user_in)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return user

@router.delete("/{user_id}", response_model=User)
async def delete_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    user = await UserService.delete_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return user
