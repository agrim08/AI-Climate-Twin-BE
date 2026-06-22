import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def clear_user_data(email: str):
    engine = create_async_engine(settings.ASYNC_DATABASE_URL)
    async with engine.begin() as conn:
        print(f"Finding user with email: {email}")
        
        # 1. Delete from public.users (this should cascade to simulation_results etc. based on the model)
        result = await conn.execute(
            text("DELETE FROM public.users WHERE email = :email RETURNING id"),
            {"email": email}
        )
        deleted_public_users = result.fetchall()
        print(f"Deleted public users: {deleted_public_users}")
        
        # 2. Delete from auth.users (Supabase authentication table)
        result = await conn.execute(
            text("DELETE FROM auth.users WHERE email = :email RETURNING id"),
            {"email": email}
        )
        deleted_auth_users = result.fetchall()
        print(f"Deleted auth users: {deleted_auth_users}")

if __name__ == "__main__":
    asyncio.run(clear_user_data("agrimgupta8105@gmail.com"))
