import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

class UserService:
    @staticmethod
    async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100):
        query = select(User).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID):
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str):
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(db: AsyncSession, user_in: UserCreate):
        db_user = User(
            email=user_in.email,
            full_name=user_in.full_name,
            role=user_in.role
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user

    @staticmethod
    async def update_user(db: AsyncSession, user_id: uuid.UUID, user_in: UserUpdate):
        db_user = await UserService.get_user_by_id(db, user_id)
        if not db_user:
            return None
        update_data = user_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_user, key, value)
        await db.commit()
        await db.refresh(db_user)
        return db_user

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: uuid.UUID):
        db_user = await UserService.get_user_by_id(db, user_id)
        if not db_user:
            return None
        await db.delete(db_user)
        await db.commit()
        return db_user
