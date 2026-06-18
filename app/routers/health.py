import httpx
from datetime import datetime
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from app.core.config import settings
from app.core.database import get_db

router = APIRouter(prefix="/health", tags=["Health & Monitoring"])

@router.get("", status_code=status.HTTP_200_OK)
async def get_health(db: AsyncSession = Depends(get_db)):
    """
    General API health check. Verifies database and Supabase connectivity.
    """
    db_status = "connected"
    supabase_api_status = "connected"
    api_status = "healthy"
    
    # 1. Test local database connection
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"
        api_status = "unhealthy"
        
    # 2. Test Supabase API connection
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/",
                headers={"apikey": settings.SUPABASE_ANON_KEY},
                timeout=3
            )
            # A status code of 200 or 401 indicates the endpoint responded and is reachable
            if response.status_code not in (200, 401):
                supabase_api_status = "degraded"
    except Exception:
        supabase_api_status = "disconnected"
        
    return {
        "status": api_status,
        "database": db_status,
        "supabase_connection": supabase_api_status,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/database", status_code=status.HTTP_200_OK)
async def get_database_health(db: AsyncSession = Depends(get_db)):
    """
    Detailed database latency and connectivity monitoring endpoint.
    """
    start_time = datetime.utcnow()
    try:
        await db.execute(text("SELECT 1"))
        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        return {
            "status": "connected",
            "latency_ms": round(latency_ms, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
