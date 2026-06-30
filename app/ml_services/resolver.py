import httpx
import logging
from datetime import datetime, date, timezone
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.ml_services.lookup import ClimateLookup
from app.models.climate_observation import ClimateObservation

logger = logging.getLogger(__name__)

class ClimateStateResolver:
    """
    Climate State Resolver (Priority 1).
    Attempts to resolve current weather parameters from:
    1. LIVE (Open-Meteo API)
    2. DATABASE (climate_observations table)
    3. HISTORICAL (climate_master.csv via ClimateLookup)
    """

    @staticmethod
    async def resolve_state(db: Optional[AsyncSession], request_dict: Dict[str, Any]) -> Dict[str, Any]:
        req = request_dict.copy()
        
        # 1. Base historical lookup
        # This resolves coordinates, nearest city, months clamping, and loads historical context.
        payload = await ClimateLookup.get_lookup_state(db, req)
        
        lat = payload.get("latitude", 20.0)
        lon = payload.get("longitude", 80.0)
        district_id = req.get("district_id")
        use_live = req.get("use_live", False)
        
        try:
            year = int(float(payload.get("year", 2024)))
        except (ValueError, TypeError):
            year = 2024
        try:
            month = int(float(payload.get("month", 6)))
        except (ValueError, TypeError):
            month = 6
        
        # Default metadata values
        source = "HISTORICAL"
        confidence_source = 0.5
        last_updated = f"{year}-{month:02d}-01"
        
        resolved_temp = None
        resolved_rain = None
        resolved_sm = None
        resolved_humidity = None
        
        if use_live:
            # Step 1: Try Live (Open-Meteo)
            try:
                # Call Open-Meteo current API
                url = (
                    f"https://api.open-meteo.com/v1/forecast"
                    f"?latitude={lat}&longitude={lon}"
                    f"&current=temperature_2m,relative_humidity_2m,rain,soil_moisture_0_to_7cm"
                    f"&timezone=auto"
                )
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=5.0)
                    if response.status_code == 200:
                        data = response.json()
                        current = data.get("current", {})
                        
                        resolved_temp = current.get("temperature_2m")
                        resolved_rain = current.get("rain")
                        resolved_humidity = current.get("relative_humidity_2m")
                        resolved_sm = current.get("soil_moisture_0_to_7cm")
                        
                        source = "LIVE"
                        confidence_source = 1.0
                        last_updated = current.get("time", datetime.now(timezone.utc).isoformat())
                        
                        logger.info(f"Resolver: Resolved LIVE state from Open-Meteo for coordinates ({lat}, {lon})")
                    else:
                        logger.warning(f"Resolver: Open-Meteo returned status {response.status_code}. Checking Database.")
            except Exception as e:
                logger.warning(f"Resolver: Failed to fetch LIVE weather from Open-Meteo ({str(e)}). Checking Database.")
                
            # Step 2: Try Database (climate_observations)
            if resolved_temp is None and district_id is not None and db is not None:
                try:
                    query = select(ClimateObservation).where(
                        ClimateObservation.district_id == district_id
                    ).order_by(ClimateObservation.observation_date.desc()).limit(1)
                    res = await db.execute(query)
                    obs = res.scalar_one_or_none()
                    
                    if obs:
                        resolved_temp = obs.temperature
                        resolved_rain = obs.rainfall
                        resolved_humidity = obs.humidity
                        # Note: Observations table doesn't store soil moisture, we keep historical
                        
                        source = "DATABASE"
                        confidence_source = 0.8
                        last_updated = obs.observation_date.isoformat()
                        logger.info(f"Resolver: Resolved DATABASE state for district ID {district_id} on date {last_updated}")
                except Exception as e:
                    logger.error(f"Resolver: Database lookup failed for district ID {district_id} ({str(e)}). Using Historical.")
                    
        # Apply resolved values to payload
        if resolved_temp is not None:
            payload["temperature_c"] = float(resolved_temp)
        if resolved_rain is not None:
            payload["rainfall_mm"] = float(resolved_rain)
        if resolved_sm is not None:
            payload["soil_moisture"] = float(resolved_sm)
        if resolved_humidity is not None:
            payload["humidity"] = float(resolved_humidity)
            
        # Set source metadata in payload
        payload["source"] = source
        payload["confidence_source"] = float(confidence_source)
        payload["last_updated"] = str(last_updated)
        
        return payload
