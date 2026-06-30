from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Create async engine
# Note: pool_pre_ping=True is highly recommended for serverless or connection-pooled databases like Supabase,
# as it automatically checks connection health before issuing queries and re-establishes broken connections.
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=False,  # Set to True to output generated SQL statements to standard console
    future=True,
    pool_pre_ping=True,
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Declarative base class for models
class Base(DeclarativeBase):
    pass

# Dependency to get async database session per request
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
