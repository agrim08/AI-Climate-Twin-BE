import httpx
import logging
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.district import District
from app.models.climate_observation import ClimateObservation

logger = logging.getLogger(__name__)

class ClimateIngestionService:
    @staticmethod
    async def fetch_and_store_district_climate(db: AsyncSession, district_id: int) -> dict:
        """
        Fetch weather data from Open-Meteo for a specific district and insert observations.
        Avoids inserting duplicate records.
        """
        # 1. Retrieve district coordinates
        query = select(District).where(District.id == district_id)
        result = await db.execute(query)
        district = result.scalar_one_or_none()
        if not district:
            raise ValueError(f"District with ID {district_id} not found.")

        lat = district.latitude
        lon = district.longitude

        # 2. Call Open-Meteo API async
        # We fetch 7 past days. Daily variables: rain_sum, temperature_2m_max, relative_humidity_2m_mean
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&past_days=7"
            f"&daily=rain_sum,temperature_2m_max,relative_humidity_2m_mean"
            f"&timezone=auto"
        )

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=10.0)
                if response.status_code != 200:
                    logger.error(f"Open-Meteo API returned error {response.status_code} for district {district_id}")
                    raise RuntimeError(f"Open-Meteo API returned status code {response.status_code}")
                data = response.json()
            except httpx.RequestError as e:
                logger.error(f"HTTP request failed to Open-Meteo for district {district_id}: {str(e)}")
                raise RuntimeError(f"Failed to connect to weather provider: {str(e)}")

        daily = data.get("daily", {})
        times = daily.get("time", [])
        rain_sums = daily.get("rain_sum", [])
        temp_means = daily.get("temperature_2m_max", [])
        humidity_means = daily.get("relative_humidity_2m_mean", [])

        inserted_count = 0
        duplicate_count = 0
        today = date.today()

        # 3. Process each day's metrics
        for idx, time_str in enumerate(times):
            try:
                obs_date = datetime.strptime(time_str, "%Y-%m-%d").date()
                # Store only past observations
                if obs_date >= today:
                    continue

                # Check if observation already exists for this district + date
                dup_query = select(ClimateObservation).where(
                    ClimateObservation.district_id == district_id,
                    ClimateObservation.observation_date == obs_date
                )
                dup_res = await db.execute(dup_query)
                existing = dup_res.scalar_one_or_none()

                if existing:
                    duplicate_count += 1
                    continue

                rainfall = rain_sums[idx] if idx < len(rain_sums) and rain_sums[idx] is not None else 0.0
                temperature = temp_means[idx] if idx < len(temp_means) and temp_means[idx] is not None else 25.0
                humidity = humidity_means[idx] if idx < len(humidity_means) and humidity_means[idx] is not None else 50.0

                new_obs = ClimateObservation(
                    district_id=district_id,
                    rainfall=float(rainfall),
                    temperature=float(temperature),
                    humidity=float(humidity),
                    observation_date=obs_date
                )
                db.add(new_obs)
                inserted_count += 1
            except Exception as item_err:
                logger.warning(f"Error parsing day record at index {idx} for district {district_id}: {str(item_err)}")
                continue

        if inserted_count > 0:
            await db.commit()

        return {
            "district_id": district_id,
            "district_name": district.district_name,
            "state": district.state,
            "observations_processed": len(times),
            "observations_inserted": inserted_count,
            "duplicates_skipped": duplicate_count
        }

    @staticmethod
    async def fetch_and_store_all_districts_climate(db: AsyncSession) -> dict:
        """
        Fetch and store weather data from Open-Meteo for all registered districts.
        """
        query = select(District.id)
        result = await db.execute(query)
        district_ids = result.scalars().all()

        total_inserted = 0
        total_duplicates = 0
        successful_districts = 0
        failed_districts = 0
        errors = []

        for dist_id in district_ids:
            try:
                res = await ClimateIngestionService.fetch_and_store_district_climate(db, dist_id)
                total_inserted += res["observations_inserted"]
                total_duplicates += res["duplicates_skipped"]
                successful_districts += 1
            except Exception as e:
                failed_districts += 1
                errors.append({"district_id": dist_id, "error": str(e)})
                logger.error(f"Failed climate ingestion for district ID {dist_id}: {str(e)}")

        return {
            "total_districts_queried": len(district_ids),
            "successful_districts": successful_districts,
            "failed_districts": failed_districts,
            "total_inserted": total_inserted,
            "total_duplicates_skipped": total_duplicates,
            "errors": errors
        }
