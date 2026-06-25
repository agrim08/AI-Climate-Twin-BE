import os
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.district import District

logger = logging.getLogger(__name__)

class ClimateLookup:
    """
    Climate Lookup Service (Gap 1).
    Loads historical climatology averages and rolling/lag variables from the processed climate dataset.
    Allows the FastAPI routers to resolve district IDs and coordinates automatically,
    minimizing client request payloads.
    """
    _df = None
    _coords = None
    _climo_city_month = None
    _climo_zone_month = None
    _climo_seasonal = None
    
    @classmethod
    def initialize(cls):
        """Pre-computes and caches climatologies from climate_master.csv once on boot."""
        if cls._df is not None:
            return
            
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.join(script_dir, "..", "..", "ml_research", "data", "processed", "climate_master.csv")
            
            logger.info(f"Lookup Engine: Loading historical dataset from {data_path}")
            df = pd.read_csv(data_path)
            
            # Save raw dataframe
            cls._df = df
            
            # Extract unique coordinates
            cls._coords = df.groupby("city")[["latitude", "longitude", "climate_zone"]].first().reset_index()
            
            # City × Month climatologies
            cls._climo_city_month = df.groupby(["city", "month"]).agg(
                temp_climo_mean=("temperature_c", "mean"),
                temp_climo_std=("temperature_c", "std"),
                rain_climo_mean=("rainfall_mm", "mean"),
                rain_climo_std=("rainfall_mm", "std"),
                sm_climo_mean=("soil_moisture", "mean"),
                sm_climo_std=("soil_moisture", "std"),
            ).reset_index()
            # Replace 0 stds to avoid division by zero
            cls._climo_city_month["temp_climo_std"] = cls._climo_city_month["temp_climo_std"].replace(0, 0.1)
            cls._climo_city_month["rain_climo_std"] = cls._climo_city_month["rain_climo_std"].replace(0, 0.01)
            cls._climo_city_month["sm_climo_std"] = cls._climo_city_month["sm_climo_std"].replace(0, 0.001)

            # Zone × Month climatologies
            cls._climo_zone_month = df.groupby(["climate_zone", "month"]).agg(
                zone_temp_mean=("temperature_c", "mean"),
                zone_temp_std=("temperature_c", "std"),
                zone_rain_mean=("rainfall_mm", "mean"),
                zone_rain_std=("rainfall_mm", "std"),
            ).reset_index()
            cls._climo_zone_month["zone_temp_std"] = cls._climo_zone_month["zone_temp_std"].replace(0, 0.1)
            cls._climo_zone_month["zone_rain_std"] = cls._climo_zone_month["zone_rain_std"].replace(0, 0.01)

            # India-wide seasonal monthly climatology
            cls._climo_seasonal = df.groupby("month").agg(
                seasonal_temp_mean=("temperature_c", "mean"),
                seasonal_rain_mean=("rainfall_mm", "mean"),
            ).reset_index()

            logger.info("Lookup Engine initialized successfully with 47 cities and climatology baselines.")
        except Exception as e:
            logger.critical(f"Lookup Engine failed to initialize: {str(e)}", exc_info=True)
            raise

    @classmethod
    def find_nearest_city(cls, lat: float, lon: float) -> Tuple[str, float, float, str]:
        """Finds the nearest coordinate out of the 47 cities using Euclidean distance."""
        if cls._coords is None:
            cls.initialize()
            
        distances = np.sqrt(
            (cls._coords["latitude"] - lat) ** 2 + 
            (cls._coords["longitude"] - lon) ** 2
        )
        idx = distances.idxmin()
        row = cls._coords.iloc[idx]
        return str(row["city"]), float(row["latitude"]), float(row["longitude"]), str(row["climate_zone"])

    @classmethod
    async def resolve_district(cls, db: AsyncSession, district_id: int) -> Tuple[float, float, str]:
        """Queries coordinate information for a given district_id from the database."""
        result = await db.execute(select(District).where(District.id == district_id))
        district = result.scalar_one_or_none()
        if not district:
            raise ValueError(f"District ID {district_id} does not exist in the database.")
        return float(district.latitude), float(district.longitude), district.district_name

    @classmethod
    async def get_lookup_state(
        cls, db: Optional[AsyncSession], request_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Builds a comprehensive baseline climate and climatological state dict.
        Resolves district ID or coordinates, matches the nearest city, fetches lag stats,
        and overrides with the caller's request inputs.
        """
        if cls._df is None:
            cls.initialize()
            
        req = request_dict.copy()
        
        # 1. Resolve coordinates
        district_id = req.get("district_id")
        lat = req.get("latitude")
        lon = req.get("longitude")
        
        if district_id is not None and db is not None:
            lat, lon, d_name = await cls.resolve_district(db, district_id)
            req["latitude"] = lat
            req["longitude"] = lon
            
        if lat is None or lon is None:
            # Fallback to defaults
            lat = 20.0
            lon = 80.0
            req["latitude"] = lat
            req["longitude"] = lon
            
        # 2. Get nearest city match
        city, city_lat, city_lon, climate_zone = cls.find_nearest_city(lat, lon)
        
        # 3. Get calendar date parameters
        try:
            month = int(float(req.get("month", 6)))
        except (ValueError, TypeError):
            month = 6
        if not (1 <= month <= 12):
            logger.warning(f"Lookup Engine: Invalid month {month} provided. Clamping to [1, 12].")
            month = max(1, min(12, month))
        try:
            year = int(float(req.get("year", 2024)))
        except (ValueError, TypeError):
            year = 2024
        
        # 4. Fetch Climatology Baselines
        climo_city = cls._climo_city_month[
            (cls._climo_city_month["city"] == city) & (cls._climo_city_month["month"] == month)
        ].iloc[0].to_dict()
        
        climo_zone = cls._climo_zone_month[
            (cls._climo_zone_month["climate_zone"] == climate_zone) & (cls._climo_zone_month["month"] == month)
        ].iloc[0].to_dict()
        
        climo_sea = cls._climo_seasonal[
            cls._climo_seasonal["month"] == month
        ].iloc[0].to_dict()
        
        # Merge all climatologies
        f_state = {}
        f_state.update(climo_city)
        f_state.update(climo_zone)
        f_state.update(climo_sea)
        
        # 5. Fetch Historical Record for Lags & Streaks
        # Find exact year/month for that city, if not found fallback to the latest year containing this month
        city_rows = cls._df[cls._df["city"] == city]
        hist_row = city_rows[(city_rows["year"] == year) & (city_rows["month"] == month)]
        
        if hist_row.empty:
            # Fallback 1: Get the latest available year for that city that has the requested month
            month_rows = city_rows[city_rows["month"] == month]
            if not month_rows.empty:
                max_year_for_month = int(month_rows["year"].max())
                hist_row = month_rows[month_rows["year"] == max_year_for_month]
                logger.info(
                    f"Lookup Engine Fallback 1: Exact record for {city} {year}-{month:02d} not found. "
                    f"Using latest historical year containing this month: {max_year_for_month}-{month:02d}."
                )
            
            # Fallback 2: Find the absolute nearest record in time (minimizing month difference)
            if hist_row.empty and not city_rows.empty:
                time_diff = (city_rows["year"] - year) * 12 + (city_rows["month"] - month)
                abs_time_diff = time_diff.abs()
                idx = abs_time_diff.idxmin()
                hist_row = city_rows.loc[[idx]]
                fb_year = int(hist_row.iloc[0]["year"])
                fb_month = int(hist_row.iloc[0]["month"])
                logger.warning(
                    f"Lookup Engine Fallback 2: Month {month:02d} not found for {city}. "
                    f"Using closest chronological record: {fb_year}-{fb_month:02d}."
                )
            
        if not hist_row.empty:
            h_data = hist_row.iloc[0].to_dict()
            
            def get_valid_val(key: str, default: float) -> float:
                val = h_data.get(key)
                if val is None or pd.isna(val):
                    return default
                return float(val)
                
            # Add variables
            f_state.update({
                "temperature_c": get_valid_val("temperature_c", 30.0),
                "rainfall_mm": get_valid_val("rainfall_mm", 10.0),
                "soil_moisture": get_valid_val("soil_moisture", 0.20),
                "evabs": get_valid_val("evabs", -0.001),
                "sro": get_valid_val("sro", 0.001),
                "temperature_prev_1": get_valid_val("temperature_prev_1", 29.0),
                "temperature_prev_3": get_valid_val("temperature_prev_3", 28.0),
                "rainfall_prev_1": get_valid_val("rainfall_prev_1", 5.0),
                "rainfall_prev_3": get_valid_val("rainfall_prev_3", 2.0),
                "soil_moisture_prev_1": get_valid_val("soil_moisture_prev_1", 0.18),
                "rolling_temp_3m": get_valid_val("rolling_temp_3m", 28.5),
                "rolling_rainfall_3m": get_valid_val("rolling_rainfall_3m", 15.0),
                "rolling_temp_6m": get_valid_val("rolling_temp_6m", 25.0),
                "rolling_rainfall_6m": get_valid_val("rolling_rainfall_6m", 30.0),
                "rolling_sm_3m": get_valid_val("rolling_sm_3m", 0.22) if "rolling_sm_3m" in h_data else 0.22,
                "rolling_sm_6m": get_valid_val("rolling_sm_6m", 0.25) if "rolling_sm_6m" in h_data else 0.25,
                "dry_month_streak": get_valid_val("dry_month_streak", 0.0) if "dry_month_streak" in h_data else 0.0,
                "deficit_streak": get_valid_val("deficit_streak", 0.0) if "deficit_streak" in h_data else 0.0,
                "low_sm_streak": get_valid_val("low_sm_streak", 0.0) if "low_sm_streak" in h_data else 0.0,
                "cumulative_deficit_3m": get_valid_val("cumulative_deficit_3m", -10.0) if "cumulative_deficit_3m" in h_data else -10.0,
                "cumulative_deficit_6m": get_valid_val("cumulative_deficit_6m", -25.0) if "cumulative_deficit_6m" in h_data else -25.0,
                "cumulative_sm_deficit_3m": get_valid_val("cumulative_sm_deficit_3m", 0.05) if "cumulative_sm_deficit_3m" in h_data else 0.05,
                "cumulative_sm_deficit_6m": get_valid_val("cumulative_sm_deficit_6m", 0.10) if "cumulative_sm_deficit_6m" in h_data else 0.10,
                "lag1_climatology": get_valid_val("lag1_climatology", 10.0) if "lag1_climatology" in h_data else 10.0,
                "zone_rain_climatology": get_valid_val("zone_rain_climatology", 10.0) if "zone_rain_climatology" in h_data else 10.0,
                "zone_rain_climatology_std": get_valid_val("zone_rain_climatology_std", 4.0) if "zone_rain_climatology_std" in h_data else 4.0,
                "zone_sm_climatology": get_valid_val("zone_sm_climatology", 0.20) if "zone_sm_climatology" in h_data else 0.20,
                "zone_sm_climatology_std": get_valid_val("zone_sm_climatology_std", 0.04) if "zone_sm_climatology_std" in h_data else 0.04,
                "zone_aridity_index": get_valid_val("zone_aridity_index", 1.5) if "zone_aridity_index" in h_data else 1.5,
                "drought_acceleration": get_valid_val("drought_acceleration", 0.0) if "drought_acceleration" in h_data else 0.0,
                "deficit_volatility_3m": get_valid_val("deficit_volatility_3m", 5.0) if "deficit_volatility_3m" in h_data else 5.0,
                "consecutive_hot_months": get_valid_val("hw_consecutive_hot_months", 0.0) if "hw_consecutive_hot_months" in h_data else 0.0,
                "consecutive_wet_months": get_valid_val("er_consecutive_wet_months", 0.0) if "er_consecutive_wet_months" in h_data else 0.0
            })
            
        # 6. Override lookup values with the explicit request values
        f_state.update(req)
        
        # Enforce name mappings
        f_state["climate_zone"] = climate_zone
        f_state["city"] = city
        try:
            f_state["year"] = int(float(f_state.get("year", year)))
        except (ValueError, TypeError):
            f_state["year"] = int(year)
        try:
            f_state["month"] = int(float(f_state.get("month", month)))
        except (ValueError, TypeError):
            f_state["month"] = int(month)
        f_state["temperature_climatology"] = f_state.get("temp_climo_mean", 28.0)
        f_state["temperature_climatology_std"] = f_state.get("temp_climo_std", 2.0)
        f_state["rainfall_climatology"] = f_state.get("rain_climo_mean", 12.0)
        f_state["rainfall_climatology_std"] = f_state.get("rain_climo_std", 5.0)
        f_state["sm_climatology"] = f_state.get("sm_climo_mean", 0.25)
        f_state["sm_climatology_std"] = f_state.get("sm_climo_std", 0.05)
        
        return f_state
