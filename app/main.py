from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import user, district, climate_observation, forecast, simulation, auth, analytics, dashboard, climate_import, health, climate_ingestion, drought, extreme_weather, temperature, rainfall, rankings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="ClimateTwin India API - Climate simulation and monitoring backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Set CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include Routers
# Root-level health check endpoints (/health and /health/database)
app.include_router(health.router)

# Versioned resource routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(user.router, prefix=settings.API_V1_STR)
app.include_router(district.router, prefix=settings.API_V1_STR)
app.include_router(climate_observation.router, prefix=settings.API_V1_STR)
app.include_router(forecast.router, prefix=settings.API_V1_STR)
app.include_router(simulation.router, prefix=settings.API_V1_STR)
app.include_router(analytics.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(climate_import.router, prefix=settings.API_V1_STR)
app.include_router(climate_ingestion.router, prefix=settings.API_V1_STR)
app.include_router(drought.router, prefix=settings.API_V1_STR)
app.include_router(extreme_weather.router, prefix=settings.API_V1_STR)
app.include_router(temperature.router, prefix=settings.API_V1_STR)
app.include_router(rainfall.router, prefix=settings.API_V1_STR)
app.include_router(rankings.router, prefix=settings.API_V1_STR)

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "documentation": "/docs",
        "status": "running"
    }
