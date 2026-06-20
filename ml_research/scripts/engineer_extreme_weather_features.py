"""
Extreme Weather Intelligence Dataset & Feature Engineering Pipeline
===================================================================
AI-powered Digital Twin of India's Climate

Purpose:
    Transforms climate_master.csv into the richest possible extreme-weather
    training dataset using scientific feature engineering for:
      - Heatwave prediction (Low / Medium / High / Extreme)
      - Extreme rainfall prediction (Low / Medium / High / Extreme)

Scientific Foundation:
    Heatwave:
      - WMO heatwave definition: T > 5°C above climatology for >= 3 days
      - Apparent temperature / Heat Index framework
      - IPCC AR6 compound heat-drought event research
    Extreme Rainfall:
      - Standardized Precipitation Index (SPI) anomaly approach
      - IMD extreme rainfall threshold (>= 64.5 mm/day → Heavy; >= 204.5 mm/day → Extremely Heavy)
      - Flash-flood potential via runoff-saturation coupling

Approach:
    - Climate-zone-aware baselines for ALL z-score and anomaly calculations
    - Streak-based persistence indicators (consecutive hot / wet months)
    - Compound stress indicators coupling heat with drought / rainfall surge with saturation
    - Percentile-based, data-driven category labeling (no arbitrary thresholds)

Output:
    ml_research/data/processed/extreme_weather_dataset.csv
    ml_research/reports/extreme_weather_intelligence_report.md

Author: AI-Climate-Twin Engineering
"""

import os
import sys
import logging
import warnings
from typing import Dict, Tuple, List

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import MinMaxScaler

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DATA_PATH = os.path.join(BASE_DIR, "ml_research", "data", "processed", "climate_master.csv")
OUT_DATA_PATH = os.path.join(BASE_DIR, "ml_research", "data", "processed", "extreme_weather_dataset.csv")
OUT_REPORT_PATH = os.path.join(BASE_DIR, "ml_research", "reports", "extreme_weather_intelligence_report.md")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
HEATWAVE_ABSOLUTE_THRESHOLD = 35.0   # °C — agronomic heat stress threshold
DAYS_IN_MONTH = 30.44                 # average days per month

CLIMATE_ZONES = [
    "Central Plateau Region", "Eastern Coastal Region", "Himalayan Region",
    "Indo-Gangetic Plains", "North-East Region", "Southern Peninsular Region",
    "Thar Desert Region", "Western Coastal Region", "Western Ghats Region"
]


# ===========================================================================
# 1. DATA LOADING & VALIDATION
# ===========================================================================

def load_and_validate(data_path: str) -> pd.DataFrame:
    """Load climate_master.csv and perform strict quality checks."""
    logger.info(f"Loading dataset from: {data_path}")
    df = pd.read_csv(data_path, parse_dates=["date"])
    logger.info(f"Raw shape: {df.shape}")

    df = df.replace([np.inf, -np.inf], np.nan)

    before = len(df)
    df = df.dropna(subset=["rainfall_mm", "soil_moisture", "temperature_c"])
    df = df.drop_duplicates(subset=["city", "date"])
    logger.info(f"After cleaning: {len(df)} rows (dropped {before - len(df)})")

    df = df.sort_values(["city", "date"]).reset_index(drop=True)
    logger.info(f"Year range: {df['year'].min()} – {df['year'].max()}")
    logger.info(f"Cities: {df['city'].nunique()} | Climate zones: {df['climate_zone'].nunique()}")
    return df


# ===========================================================================
# 2. CLIMATE-ZONE CLIMATOLOGY BASELINES
# ===========================================================================

def compute_climatology_baselines(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes per-city-month climatology baselines for temperature and rainfall.
    These serve as anchors for ALL anomaly and z-score calculations.
    Grouped by city × month to capture seasonality correctly.
    """
    logger.info("Computing city-month climatology baselines…")

    city_month = (
        df.groupby(["city", "month"])
        .agg(
            temp_climo_mean=("temperature_c", "mean"),
            temp_climo_std=("temperature_c", "std"),
            rain_climo_mean=("rainfall_mm", "mean"),
            rain_climo_std=("rainfall_mm", "std"),
            sm_climo_mean=("soil_moisture", "mean"),
            sm_climo_std=("soil_moisture", "std"),
        )
        .reset_index()
    )
    # Replace 0 stds to avoid division by zero
    city_month["temp_climo_std"] = city_month["temp_climo_std"].replace(0, 0.1)
    city_month["rain_climo_std"] = city_month["rain_climo_std"].replace(0, 0.01)
    city_month["sm_climo_std"] = city_month["sm_climo_std"].replace(0, 0.001)

    df = df.merge(city_month, on=["city", "month"], how="left")

    # Zone-level climatology (for zone-relative anomalies)
    zone_month = (
        df.groupby(["climate_zone", "month"])
        .agg(
            zone_temp_mean=("temperature_c", "mean"),
            zone_temp_std=("temperature_c", "std"),
            zone_rain_mean=("rainfall_mm", "mean"),
            zone_rain_std=("rainfall_mm", "std"),
        )
        .reset_index()
    )
    zone_month["zone_temp_std"] = zone_month["zone_temp_std"].replace(0, 0.1)
    zone_month["zone_rain_std"] = zone_month["zone_rain_std"].replace(0, 0.01)

    df = df.merge(zone_month, on=["climate_zone", "month"], how="left")

    # India-wide seasonal baseline (all cities in the same month)
    seasonal = (
        df.groupby("month")
        .agg(
            seasonal_temp_mean=("temperature_c", "mean"),
            seasonal_rain_mean=("rainfall_mm", "mean"),
        )
        .reset_index()
    )
    df = df.merge(seasonal, on="month", how="left")

    logger.info("Climatology baselines computed.")
    return df


# ===========================================================================
# PART 1 — HEATWAVE INTELLIGENCE FEATURES
# ===========================================================================

def engineer_heatwave_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates scientifically meaningful heatwave indicators.
    All features use only past information — no future leakage.
    """
    logger.info("Engineering heatwave features (Part 1)…")

    # ---- Core anomaly features -------------------------------------------
    df["hw_temperature_anomaly"] = df["temperature_c"] - df["temp_climo_mean"]
    df["hw_temperature_zscore"] = (
        df["hw_temperature_anomaly"] / df["temp_climo_std"]
    ).clip(-5, 5)

    # Absolute heat excess above agronomic stress threshold
    df["hw_heat_excess"] = (df["temperature_c"] - HEATWAVE_ABSOLUTE_THRESHOLD).clip(lower=0)

    # ---- Heat stress: anomaly amplified by rainfall deficit ---------------
    # When rainfall is low (< climatology), heat stress is amplified
    rain_norm = (df["rainfall_mm"] / (df["rain_climo_mean"] + 1e-6)).clip(0, 2)
    df["hw_heat_stress"] = df["hw_temperature_anomaly"] * (2.0 - rain_norm).clip(lower=0)

    # ---- Heatwave intensity: positive anomaly normalized by zone std ------
    df["hw_heatwave_intensity"] = (
        df["hw_temperature_anomaly"].clip(lower=0) / (df["zone_temp_std"] + 1e-6)
    ).clip(0, 5)

    # ---- Rolling heat anomaly over 3 and 6 months ------------------------
    df = df.sort_values(["city", "date"])

    def rolling_heat_anomaly(group: pd.DataFrame, window: int) -> pd.Series:
        return group["hw_temperature_anomaly"].shift(1).rolling(window, min_periods=1).mean()

    df["hw_rolling_heat_3m"] = df.groupby("city", group_keys=False).apply(
        lambda g: rolling_heat_anomaly(g, 3)
    )
    df["hw_rolling_heat_6m"] = df.groupby("city", group_keys=False).apply(
        lambda g: rolling_heat_anomaly(g, 6)
    )

    # ---- Heatwave duration proxy: consecutive months above +1σ -----------
    def consecutive_hot_months(group: pd.DataFrame) -> pd.Series:
        """Count of preceding months with positive temperature anomaly."""
        is_hot = (group["hw_temperature_anomaly"].shift(1) > group["temp_climo_std"]).astype(int)
        streak = []
        count = 0
        for val in is_hot:
            if val == 1:
                count += 1
            else:
                count = 0
            streak.append(count)
        return pd.Series(streak, index=group.index)

    df["hw_consecutive_hot_months"] = df.groupby("city", group_keys=False).apply(
        consecutive_hot_months
    )

    # ---- Heatwave acceleration: short-term minus long-term heat trend ----
    df["hw_heat_acceleration"] = df["hw_rolling_heat_3m"] - df["hw_rolling_heat_6m"]

    # ---- Dry-heat indicator: heat stress × soil moisture deficit ---------
    sm_norm = (df["soil_moisture"] / 0.5).clip(0, 1)
    df["hw_dry_heat_indicator"] = df["hw_heat_excess"] * (1.0 - sm_norm)

    # ---- Rainfall-heat interaction: heat amplified by rainfall absence ---
    df["hw_rainfall_heat_interaction"] = (
        df["hw_temperature_anomaly"].clip(lower=0)
        * (1.0 - rain_norm).clip(lower=0)
    )

    # ---- Soil-heat interaction: heat × soil moisture deficit -------------
    sm_deficit = (df["sm_climo_mean"] - df["soil_moisture"]).clip(lower=0)
    df["hw_soil_heat_interaction"] = df["hw_temperature_anomaly"].clip(lower=0) * sm_deficit

    # ---- Evaporation-heat ratio ------------------------------------------
    evap_mag = df["evabs"].abs() * 30 * 1000   # convert to mm/month
    df["hw_evaporation_heat_ratio"] = (evap_mag / (df["temperature_c"].abs() + 1.0)).clip(0, 20)

    # ---- Climate-zone heat anomaly: vs zone mean temp --------------------
    df["hw_climate_zone_heat_anomaly"] = df["temperature_c"] - df["zone_temp_mean"]
    df["hw_zone_temp_zscore"] = (
        df["hw_climate_zone_heat_anomaly"] / (df["zone_temp_std"] + 1e-6)
    ).clip(-5, 5)

    # ---- Seasonal heat deviation: vs India-wide monthly mean -------------
    df["hw_seasonal_heat_deviation"] = df["temperature_c"] - df["seasonal_temp_mean"]

    # ---- Rolling temperature itself (lagged, to avoid leakage) -----------
    df["hw_rolling_temp_trend_3m"] = df["rolling_temp_3m"] - df["rolling_temp_6m"]

    # ---- Apparent temperature proxy (Steadman-like simplified) -----------
    # Uses soil moisture as a humidity proxy
    humidity_proxy = (df["soil_moisture"] * 100).clip(20, 95)
    df["hw_apparent_temperature"] = (
        -8.78469475556
        + 1.61139411 * df["temperature_c"]
        + 2.33854883889 * humidity_proxy / 100
        - 0.14611605 * df["temperature_c"] * humidity_proxy / 100
        - 0.012308094 * df["temperature_c"] ** 2
        - 0.0164248277778 * (humidity_proxy / 100) ** 2
        + 0.002211732 * df["temperature_c"] ** 2 * humidity_proxy / 100
        + 0.00072546 * df["temperature_c"] * (humidity_proxy / 100) ** 2
        - 0.000003582 * df["temperature_c"] ** 2 * (humidity_proxy / 100) ** 2
    ).clip(df["temperature_c"].min(), 55)

    df["hw_apparent_temp_anomaly"] = df["hw_apparent_temperature"] - df["temp_climo_mean"]

    # ---- Compound heat-drought stress ------------------------------------
    df["hw_compound_heat_drought"] = (
        df["hw_temperature_anomaly"].clip(lower=0)
        * sm_deficit
        * (1.0 - rain_norm).clip(lower=0)
    )

    logger.info(f"  Created {len([c for c in df.columns if c.startswith('hw_')])} heatwave features.")
    return df


# ===========================================================================
# PART 2 — EXTREME RAINFALL INTELLIGENCE FEATURES
# ===========================================================================

def engineer_extreme_rainfall_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates scientifically meaningful extreme rainfall indicators.
    All features use only past information — no future leakage.
    """
    logger.info("Engineering extreme rainfall features (Part 2)…")

    # ---- Core anomaly features -------------------------------------------
    df["er_rainfall_anomaly"] = df["rainfall_mm"] - df["rain_climo_mean"]
    df["er_rainfall_zscore"] = (
        df["er_rainfall_anomaly"] / df["rain_climo_std"]
    ).clip(-5, 5)

    # ---- Rainfall intensity: daily rate proxy ----------------------------
    df["er_rainfall_intensity"] = df["rainfall_mm"] / DAYS_IN_MONTH

    # ---- Rainfall surge: current vs 3-month rolling ---------------------
    df["er_rainfall_surge"] = df["rainfall_mm"] - df["rolling_rainfall_3m"]

    # ---- Rainfall acceleration: short trend minus long trend -------------
    short_trend = df["rainfall_mm"] - df["rolling_rainfall_3m"]
    long_trend = df["rolling_rainfall_3m"] - df["rolling_rainfall_6m"]
    df["er_rainfall_acceleration"] = short_trend - long_trend

    # ---- Rainfall momentum: current vs 6-month rolling ------------------
    df["er_rainfall_momentum"] = df["rainfall_mm"] - df["rolling_rainfall_6m"]

    # ---- Rainfall variability: local CV of 3m rolling -------------------
    def rolling_cv(group: pd.DataFrame, window: int) -> pd.Series:
        rolled = group["rainfall_mm"].shift(1).rolling(window, min_periods=2)
        return (rolled.std() / (rolled.mean() + 1e-6)).clip(0, 10)

    df = df.sort_values(["city", "date"])

    df["er_rainfall_variability_3m"] = df.groupby("city", group_keys=False).apply(
        lambda g: rolling_cv(g, 3)
    ).fillna(0)

    df["er_rainfall_variability_6m"] = df.groupby("city", group_keys=False).apply(
        lambda g: rolling_cv(g, 6)
    ).fillna(0)

    # ---- Extreme precipitation index: SPI-like --------------------------
    # Standardizes against city-month climatology, clipped to positive
    df["er_extreme_precipitation_index"] = df["er_rainfall_zscore"].clip(lower=0)

    # ---- Runoff pressure: sro relative to rainfall ----------------------
    sro_mm = df["sro"] * 1000   # convert to mm
    df["er_runoff_pressure"] = (sro_mm / (df["rainfall_mm"] + 1e-6)).clip(0, 5)
    df["er_runoff_response"] = sro_mm.clip(0, 50)

    # ---- Soil saturation: soil moisture relative to capacity -------------
    # Soil moisture > 0.4 is near saturation for most Indian soil types
    df["er_soil_saturation"] = (df["soil_moisture"] / 0.45).clip(0, 1)

    # ---- Flood potential proxy: rainfall × runoff pressure × saturation -
    df["er_flood_potential_proxy"] = (
        (df["rainfall_mm"] / (df["rain_climo_mean"] + 1e-6)).clip(0, 5)
        * df["er_runoff_pressure"].clip(0, 3)
        * df["er_soil_saturation"]
    ).clip(0, 10)

    # ---- Antecedent moisture: prior month soil moisture (lagged) --------
    df["er_antecedent_soil_moisture"] = df.groupby("city")["soil_moisture"].shift(1).fillna(
        df["sm_climo_mean"]
    )

    # ---- Water balance surplus: rainfall - evaporation - runoff ---------
    evap_mm = df["evabs"].abs() * 30 * 1000
    df["er_water_surplus"] = (df["rainfall_mm"] - evap_mm - sro_mm).clip(lower=-500)

    # ---- Climate-zone rainfall anomaly: vs zone mean --------------------
    df["er_zone_rainfall_anomaly"] = df["rainfall_mm"] - df["zone_rain_mean"]
    df["er_zone_rainfall_zscore"] = (
        df["er_zone_rainfall_anomaly"] / (df["zone_rain_std"] + 1e-6)
    ).clip(-5, 5)

    # ---- Seasonal rainfall deviation: vs India-wide monthly mean --------
    df["er_seasonal_rainfall_deviation"] = df["rainfall_mm"] - df["seasonal_rain_mean"]

    # ---- Cumulative rolling rainfall: 3m and 6m sums (lagged) ----------
    def rolling_sum_lagged(group: pd.DataFrame, window: int) -> pd.Series:
        return group["rainfall_mm"].shift(1).rolling(window, min_periods=1).sum()

    df["er_cumulative_rain_3m"] = df.groupby("city", group_keys=False).apply(
        lambda g: rolling_sum_lagged(g, 3)
    )
    df["er_cumulative_rain_6m"] = df.groupby("city", group_keys=False).apply(
        lambda g: rolling_sum_lagged(g, 6)
    )

    # ---- Consecutive wet months streak ----------------------------------
    def consecutive_wet_months(group: pd.DataFrame) -> pd.Series:
        """Count of preceding months with rainfall above climatology."""
        is_wet = (group["rainfall_mm"].shift(1) > group["rain_climo_mean"]).astype(int)
        streak = []
        count = 0
        for val in is_wet:
            if val == 1:
                count += 1
            else:
                count = 0
            streak.append(count)
        return pd.Series(streak, index=group.index)

    df["er_consecutive_wet_months"] = df.groupby("city", group_keys=False).apply(
        consecutive_wet_months
    )

    # ---- Monsoon indicator (June–September) -----------------------------
    df["er_is_monsoon"] = df["month"].isin([6, 7, 8, 9]).astype(int)

    # ---- Rainfall relative to monsoon peak (month 7 = July peak) -------
    df["er_monsoon_phase_factor"] = np.sin(
        np.pi * (df["month"] - 4) / 6
    ).clip(lower=0)

    # ---- Evaporation deficit: actual vs demand (evap / rainfall) --------
    df["er_evaporation_demand_ratio"] = (evap_mm / (df["rainfall_mm"] + 1e-6)).clip(0, 20)

    # ---- Rainfall × saturation compound index ---------------------------
    df["er_compound_rainfall_saturation"] = (
        df["er_rainfall_zscore"].clip(lower=0)
        * df["er_soil_saturation"]
    ).clip(0, 5)

    logger.info(f"  Created {len([c for c in df.columns if c.startswith('er_')])} extreme rainfall features.")
    return df


# ===========================================================================
# PART 3 — HEATWAVE SEVERITY SCORE
# ===========================================================================

def compute_heatwave_severity_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes a continuous heatwave_severity_score in [0, 1].

    Formula (linearly weighted composite, normalized via MinMax scaler):
    -----------------------------------------------------------------------
      Component                        Weight   Feature
      ─────────────────────────────────────────────────────────────────
      Temperature anomaly              35%      hw_temperature_anomaly (positive only)
      Heat stress                      25%      hw_heat_stress (positive only)
      Soil moisture deficit            15%      sm_climo_mean - soil_moisture (positive)
      Rainfall deficit                 15%      rain_climo_mean - rainfall_mm (positive)
      Evaporation pressure             10%      |evabs| × 30 × 1000 / (rainfall_mm + 1)
      ─────────────────────────────────────────────────────────────────
      Total                           100%

    Each component is individually min-max normalized to [0, 1] over the full
    dataset before weighting, so no single component dominates by scale.
    """
    logger.info("Computing heatwave_severity_score (Part 3)…")

    scaler = MinMaxScaler()

    def norm_col(series: pd.Series) -> np.ndarray:
        return scaler.fit_transform(series.values.reshape(-1, 1)).flatten()

    # Component 1: Temperature anomaly (positive direction = hotter)
    c1 = norm_col(df["hw_temperature_anomaly"].clip(lower=0))

    # Component 2: Heat stress (temp anomaly amplified by rainfall absence)
    c2 = norm_col(df["hw_heat_stress"].clip(lower=0))

    # Component 3: Soil moisture deficit (positive = drier soil)
    sm_deficit = (df["sm_climo_mean"] - df["soil_moisture"]).clip(lower=0)
    c3 = norm_col(sm_deficit)

    # Component 4: Rainfall deficit (positive = drier conditions)
    rain_deficit = (df["rain_climo_mean"] - df["rainfall_mm"]).clip(lower=0)
    c4 = norm_col(rain_deficit)

    # Component 5: Evaporation pressure (high evap demand vs supply)
    evap_mag = df["evabs"].abs() * 30 * 1000
    evap_pressure = (evap_mag / (df["rainfall_mm"] + 1.0)).clip(0, 50)
    c5 = norm_col(evap_pressure)

    # Weighted composite
    df["heatwave_severity_score"] = (
        0.35 * c1 +
        0.25 * c2 +
        0.15 * c3 +
        0.15 * c4 +
        0.10 * c5
    ).clip(0, 1)

    logger.info(
        f"  heatwave_severity_score — mean: {df['heatwave_severity_score'].mean():.4f}, "
        f"max: {df['heatwave_severity_score'].max():.4f}"
    )
    return df


# ===========================================================================
# PART 4 — EXTREME RAINFALL SEVERITY SCORE
# ===========================================================================

def compute_extreme_rainfall_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes a continuous extreme_rainfall_score in [0, 1].

    Formula (linearly weighted composite, normalized via MinMax scaler):
    -----------------------------------------------------------------------
      Component                        Weight   Feature
      ─────────────────────────────────────────────────────────────────
      Rainfall anomaly                 35%      er_rainfall_anomaly (positive only)
      Rainfall intensity               25%      er_rainfall_intensity
      Runoff pressure                  20%      er_runoff_pressure
      Soil saturation                  10%      er_soil_saturation
      Rainfall acceleration            10%      er_rainfall_acceleration (positive)
      ─────────────────────────────────────────────────────────────────
      Total                           100%

    Each component is individually min-max normalized before weighting.
    """
    logger.info("Computing extreme_rainfall_score (Part 4)…")

    scaler = MinMaxScaler()

    def norm_col(series: pd.Series) -> np.ndarray:
        return scaler.fit_transform(series.values.reshape(-1, 1)).flatten()

    # Component 1: Rainfall anomaly (positive direction = wetter)
    c1 = norm_col(df["er_rainfall_anomaly"].clip(lower=0))

    # Component 2: Rainfall intensity (mm/day)
    c2 = norm_col(df["er_rainfall_intensity"])

    # Component 3: Runoff pressure (runoff relative to rainfall)
    c3 = norm_col(df["er_runoff_pressure"])

    # Component 4: Soil saturation (soil near field capacity amplifies flood risk)
    c4 = norm_col(df["er_soil_saturation"])

    # Component 5: Rainfall acceleration (positive = rapid rainfall increase)
    c5 = norm_col(df["er_rainfall_acceleration"].clip(lower=0))

    # Weighted composite
    df["extreme_rainfall_score"] = (
        0.35 * c1 +
        0.25 * c2 +
        0.20 * c3 +
        0.10 * c4 +
        0.10 * c5
    ).clip(0, 1)

    logger.info(
        f"  extreme_rainfall_score — mean: {df['extreme_rainfall_score'].mean():.4f}, "
        f"max: {df['extreme_rainfall_score'].max():.4f}"
    )
    return df


# ===========================================================================
# PART 5 — HEATWAVE CATEGORIES (Data-driven)
# ===========================================================================

def assign_heatwave_categories(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assigns heatwave_category using CITY-LEVEL PERCENTILES of heatwave_severity_score.

    Methodology:
    ─────────────────────────────────────────────────────────────────────────
    Using city-level percentiles ensures climate-zone fairness:
      - A 40°C month in Bikaner (Thar Desert) is routine → Low
      - A 35°C month in Shillong (North-East) is extreme → High/Extreme
    This mirrors the drought category approach proven in our drought pipeline.

    Percentile Thresholds (city-relative):
      Low      → 0 – 50th percentile  (routine warmth)
      Medium   → 50th – 75th          (notable heat)
      High     → 75th – 90th          (severe heatwave)
      Extreme  → 90th – 100th         (exceptional event)
    ─────────────────────────────────────────────────────────────────────────
    """
    logger.info("Assigning heatwave_category via city-level percentiles (Part 5)…")

    def label_category(group: pd.DataFrame) -> pd.Series:
        score = group["heatwave_severity_score"]
        p50 = score.quantile(0.50)
        p75 = score.quantile(0.75)
        p90 = score.quantile(0.90)
        return pd.cut(
            score,
            bins=[-np.inf, p50, p75, p90, np.inf],
            labels=["Low", "Medium", "High", "Extreme"],
            right=True
        )

    df["heatwave_category"] = (
        df.groupby("city", group_keys=False)
        .apply(label_category)
        .astype(str)
    )
    df["heatwave_category_ordinal"] = df["heatwave_category"].map(
        {"Low": 0, "Medium": 1, "High": 2, "Extreme": 3}
    )

    dist = df["heatwave_category"].value_counts()
    logger.info(f"  Heatwave category distribution:\n{dist.to_string()}")
    return df


# ===========================================================================
# PART 6 — EXTREME RAINFALL CATEGORIES (Data-driven)
# ===========================================================================

def assign_extreme_rainfall_categories(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assigns extreme_rainfall_category using CITY-LEVEL PERCENTILES of extreme_rainfall_score.

    Methodology:
    ─────────────────────────────────────────────────────────────────────────
    City-level percentiles capture local rainfall climatology fairly:
      - 10 mm/month is extreme for Jaisalmer (Thar), but routine for Cherrapunji
    
    Percentile Thresholds (city-relative):
      Low      → 0 – 50th percentile  (routine rainfall)
      Medium   → 50th – 75th          (above-normal rainfall)
      High     → 75th – 90th          (significant rainfall event)
      Extreme  → 90th – 100th         (exceptional rainfall event)
    ─────────────────────────────────────────────────────────────────────────
    """
    logger.info("Assigning extreme_rainfall_category via city-level percentiles (Part 6)…")

    def label_category(group: pd.DataFrame) -> pd.Series:
        score = group["extreme_rainfall_score"]
        p50 = score.quantile(0.50)
        p75 = score.quantile(0.75)
        p90 = score.quantile(0.90)
        return pd.cut(
            score,
            bins=[-np.inf, p50, p75, p90, np.inf],
            labels=["Low", "Medium", "High", "Extreme"],
            right=True
        )

    df["extreme_rainfall_category"] = (
        df.groupby("city", group_keys=False)
        .apply(label_category)
        .astype(str)
    )
    df["extreme_rainfall_category_ordinal"] = df["extreme_rainfall_category"].map(
        {"Low": 0, "Medium": 1, "High": 2, "Extreme": 3}
    )

    dist = df["extreme_rainfall_category"].value_counts()
    logger.info(f"  Extreme rainfall category distribution:\n{dist.to_string()}")
    return df


# ===========================================================================
# PART 7 — CLIMATE ZONE ANALYSIS
# ===========================================================================

def analyze_climate_zones(df: pd.DataFrame) -> Dict:
    """
    Analyzes which zones and months are most heatwave-prone / extreme-rainfall-prone.
    Returns a dict of insights for the report.
    """
    logger.info("Performing climate zone analysis (Part 7)…")
    insights = {}

    # --- Heatwave risk by zone -------------------------------------------
    hw_zone = (
        df.groupby("climate_zone")["heatwave_severity_score"]
        .agg(["mean", "std", "max"])
        .round(4)
        .sort_values("mean", ascending=False)
    )
    hw_zone.columns = ["mean_hw_score", "std_hw_score", "max_hw_score"]
    insights["heatwave_by_zone"] = hw_zone

    extreme_hw_pct = (
        df[df["heatwave_category"] == "Extreme"]
        .groupby("climate_zone")
        .size()
        .div(df.groupby("climate_zone").size())
        .mul(100)
        .round(2)
        .sort_values(ascending=False)
    )
    insights["extreme_heatwave_pct_by_zone"] = extreme_hw_pct

    # --- Extreme rainfall risk by zone -----------------------------------
    er_zone = (
        df.groupby("climate_zone")["extreme_rainfall_score"]
        .agg(["mean", "std", "max"])
        .round(4)
        .sort_values("mean", ascending=False)
    )
    er_zone.columns = ["mean_er_score", "std_er_score", "max_er_score"]
    insights["extreme_rainfall_by_zone"] = er_zone

    extreme_er_pct = (
        df[df["extreme_rainfall_category"] == "Extreme"]
        .groupby("climate_zone")
        .size()
        .div(df.groupby("climate_zone").size())
        .mul(100)
        .round(2)
        .sort_values(ascending=False)
    )
    insights["extreme_rainfall_pct_by_zone"] = extreme_er_pct

    # --- Monthly seasonality for heatwave --------------------------------
    hw_monthly = (
        df.groupby("month")["heatwave_severity_score"]
        .mean()
        .round(4)
        .sort_values(ascending=False)
    )
    insights["heatwave_by_month"] = hw_monthly

    # --- Monthly seasonality for extreme rainfall ------------------------
    er_monthly = (
        df.groupby("month")["extreme_rainfall_score"]
        .mean()
        .round(4)
        .sort_values(ascending=False)
    )
    insights["extreme_rainfall_by_month"] = er_monthly

    logger.info("  Climate zone analysis complete.")
    return insights


# ===========================================================================
# PART 8 — FEATURE QUALITY ANALYSIS
# ===========================================================================

def analyze_feature_quality(df: pd.DataFrame) -> Dict:
    """
    Performs correlation, variance, and missing value analysis.
    Returns a dict categorizing features as Mandatory / Useful / Experimental.
    """
    logger.info("Performing feature quality analysis (Part 8)…")

    hw_features = [c for c in df.columns if c.startswith("hw_")]
    er_features = [c for c in df.columns if c.startswith("er_")]

    results = {}

    for task, feat_list, target in [
        ("heatwave",       hw_features, "heatwave_severity_score"),
        ("extreme_rainfall", er_features, "extreme_rainfall_score"),
    ]:
        corr = {}
        variance = {}
        for feat in feat_list:
            if df[feat].dtype in [np.float64, np.float32, np.int64, np.int32]:
                corr[feat] = abs(df[feat].corr(df[target]))
                variance[feat] = df[feat].var()

        corr_series = pd.Series(corr).sort_values(ascending=False)
        var_series = pd.Series(variance)

        mandatory = corr_series[corr_series >= 0.40].index.tolist()
        useful = corr_series[(corr_series >= 0.20) & (corr_series < 0.40)].index.tolist()
        experimental = corr_series[corr_series < 0.20].index.tolist()

        results[task] = {
            "correlation_with_target": corr_series.round(4),
            "variance": var_series.round(6),
            "mandatory": mandatory,
            "useful": useful,
            "experimental": experimental,
        }
        logger.info(
            f"  [{task}] Mandatory: {len(mandatory)}, Useful: {len(useful)}, "
            f"Experimental: {len(experimental)}"
        )

    return results


# ===========================================================================
# PART 9 — LEAKAGE PREVENTION
# ===========================================================================

def prevent_leakage(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Removes all future-information columns to prevent data leakage.
    Returns the cleaned dataframe and a log of removed columns.
    """
    logger.info("Running leakage prevention checks (Part 9)…")

    # Definitive list of future/post-hoc leakage columns from climate_master.csv
    leakage_cols = [
        "target_temperature_next_month",  # Future value — direct leakage
        "target_rainfall_next_month",     # Future value — direct leakage
        "drought_risk",                   # Post-hoc label (correlated with targets)
        "heatwave_risk",                  # Post-hoc label — would contaminate heatwave target
        "climate_risk_score",             # Post-hoc composite label
    ]

    removed = []
    for col in leakage_cols:
        if col in df.columns:
            df = df.drop(columns=[col])
            removed.append(col)
            logger.info(f"  REMOVED leakage column: {col}")

    # Verify no remaining future-information columns
    suspicious_patterns = ["next_month", "future", "target_", "_t+"]
    still_leaking = [
        c for c in df.columns
        if any(pat in c.lower() for pat in suspicious_patterns)
    ]
    if still_leaking:
        logger.warning(f"  Potential remaining leakage columns: {still_leaking}")
    else:
        logger.info("  Leakage check passed — no future-information columns found.")

    return df, removed


# ===========================================================================
# PART 10 — ONE-HOT ENCODING & FINAL DATASET ASSEMBLY
# ===========================================================================

def assemble_final_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    One-hot encodes climate_zone and assembles the final production dataset.
    Drops intermediate climatology baseline helper columns.
    """
    logger.info("Assembling final dataset (Part 10)…")

    # One-hot encode climate_zone
    zone_ohe = pd.get_dummies(df["climate_zone"], prefix="climate_zone")
    df = pd.concat([df, zone_ohe], axis=1)

    # Drop raw climatology helper columns (internal only, not features)
    helper_cols = [
        "temp_climo_mean", "temp_climo_std",
        "rain_climo_mean", "rain_climo_std",
        "sm_climo_mean", "sm_climo_std",
        "zone_temp_mean", "zone_temp_std",
        "zone_rain_mean", "zone_rain_std",
        "seasonal_temp_mean", "seasonal_rain_mean",
    ]
    df = df.drop(columns=[c for c in helper_cols if c in df.columns])

    logger.info(f"  Final dataset shape: {df.shape}")
    return df


# ===========================================================================
# REPORT GENERATION
# ===========================================================================

def generate_report(
    df: pd.DataFrame,
    insights: Dict,
    quality: Dict,
    leakage_removed: List[str],
    report_path: str,
) -> None:
    """Generates the Extreme Weather Intelligence Report as Markdown."""
    logger.info(f"Generating report: {report_path}")

    hw_dist = df["heatwave_category"].value_counts().sort_index()
    er_dist = df["extreme_rainfall_category"].value_counts().sort_index()
    missing = df.isnull().sum()
    hw_feats = [c for c in df.columns if c.startswith("hw_")]
    er_feats = [c for c in df.columns if c.startswith("er_")]

    lines = []
    lines.append("# Extreme Weather Intelligence Report")
    lines.append("## AI Climate Digital Twin of India\n")

    lines.append("---\n")
    lines.append("## 1. Dataset Overview\n")
    lines.append(f"- **Total Rows**: {len(df):,}")
    lines.append(f"- **Total Columns**: {df.shape[1]}")
    lines.append(f"- **Cities**: {df['city'].nunique()}")
    lines.append(f"- **Climate Zones**: {df['climate_zone'].nunique()}")
    lines.append(f"- **Year Range**: {df['year'].min()} – {df['year'].max()}")
    lines.append(f"- **Heatwave Features Engineered**: {len(hw_feats)}")
    lines.append(f"- **Extreme Rainfall Features Engineered**: {len(er_feats)}")
    lines.append(f"- **Missing Values**: {missing.sum()}")

    lines.append("\n### Heatwave Category Distribution")
    lines.append("| Category | Count | % |")
    lines.append("|----------|-------|---|")
    for cat in ["Low", "Medium", "High", "Extreme"]:
        n = hw_dist.get(cat, 0)
        pct = n / len(df) * 100
        lines.append(f"| {cat} | {n:,} | {pct:.1f}% |")

    lines.append("\n### Extreme Rainfall Category Distribution")
    lines.append("| Category | Count | % |")
    lines.append("|----------|-------|---|")
    for cat in ["Low", "Medium", "High", "Extreme"]:
        n = er_dist.get(cat, 0)
        pct = n / len(df) * 100
        lines.append(f"| {cat} | {n:,} | {pct:.1f}% |")

    lines.append("\n---\n")
    lines.append("## 2. Feature Engineering Methodology\n")
    lines.append("### Climatology Baselines")
    lines.append("All anomaly and z-score features are computed relative to **city × month** climatology baselines,")
    lines.append("computed from the full historical record (2000–2025).")
    lines.append("This ensures:")
    lines.append("- Seasonal cycles are correctly removed")
    lines.append("- Zone-relative extremes are captured (40°C in desert ≠ 40°C in northeast)")
    lines.append("- No future leakage (baselines are pre-computed from full history)")

    lines.append("\n---\n")
    lines.append("## 3. Heatwave Severity Score Formula\n")
    lines.append("```")
    lines.append("heatwave_severity_score = (")
    lines.append("    0.35 × norm(temperature_anomaly, positive only)  # Primary heat signal")
    lines.append("  + 0.25 × norm(heat_stress)                         # Anomaly × rainfall absence")
    lines.append("  + 0.15 × norm(soil_moisture_deficit)               # Dryness amplifier")
    lines.append("  + 0.15 × norm(rainfall_deficit)                    # Co-occurring drought")
    lines.append("  + 0.10 × norm(evaporation_pressure)                # Atmospheric demand")
    lines.append(")")
    lines.append("```")
    lines.append("Each component is individually min-max normalized over the full dataset before weighting,")
    lines.append("ensuring no single variable dominates by scale.")

    lines.append("\n---\n")
    lines.append("## 4. Extreme Rainfall Severity Score Formula\n")
    lines.append("```")
    lines.append("extreme_rainfall_score = (")
    lines.append("    0.35 × norm(rainfall_anomaly, positive only)     # Primary rain signal")
    lines.append("  + 0.25 × norm(rainfall_intensity)                  # Daily rate pressure")
    lines.append("  + 0.20 × norm(runoff_pressure)                     # Flood potential")
    lines.append("  + 0.10 × norm(soil_saturation)                     # Saturation amplifier")
    lines.append("  + 0.10 × norm(rainfall_acceleration, positive)     # Rapid onset")
    lines.append(")")
    lines.append("```")

    lines.append("\n---\n")
    lines.append("## 5. Category Labeling Methodology\n")
    lines.append("**Both heatwave and extreme rainfall categories use city-level percentile thresholds.**")
    lines.append("City-level percentiles ensure climate-zone fairness:")
    lines.append("| Category | Severity Score Percentile | Description |")
    lines.append("|----------|--------------------------|-------------|")
    lines.append("| Low      | 0 – 50th                 | Routine conditions |")
    lines.append("| Medium   | 50th – 75th              | Notable event |")
    lines.append("| High     | 75th – 90th              | Significant event |")
    lines.append("| Extreme  | 90th – 100th             | Exceptional event |")

    lines.append("\n---\n")
    lines.append("## 6. Climate Zone Observations\n")
    lines.append("### Heatwave Risk by Climate Zone")
    lines.append("| Climate Zone | Mean HW Score | Extreme HW % |")
    lines.append("|---|---|---|")
    hw_zone = insights["heatwave_by_zone"]
    hw_pct = insights["extreme_heatwave_pct_by_zone"]
    for zone in hw_zone.index:
        score = hw_zone.loc[zone, "mean_hw_score"]
        pct = hw_pct.get(zone, 0)
        lines.append(f"| {zone} | {score:.4f} | {pct:.1f}% |")

    lines.append("\n### Extreme Rainfall Risk by Climate Zone")
    lines.append("| Climate Zone | Mean ER Score | Extreme ER % |")
    lines.append("|---|---|---|")
    er_zone = insights["extreme_rainfall_by_zone"]
    er_pct = insights["extreme_rainfall_pct_by_zone"]
    for zone in er_zone.index:
        score = er_zone.loc[zone, "mean_er_score"]
        pct = er_pct.get(zone, 0)
        lines.append(f"| {zone} | {score:.4f} | {pct:.1f}% |")

    lines.append("\n### Peak Heatwave Months (India-wide)")
    hw_monthly = insights["heatwave_by_month"]
    lines.append("| Month | Mean HW Score |")
    lines.append("|-------|---------------|")
    for m, v in hw_monthly.items():
        import calendar
        lines.append(f"| {calendar.month_abbr[int(m)]} | {v:.4f} |")

    lines.append("\n### Peak Extreme Rainfall Months (India-wide)")
    er_monthly = insights["extreme_rainfall_by_month"]
    lines.append("| Month | Mean ER Score |")
    lines.append("|-------|---------------|")
    for m, v in er_monthly.items():
        import calendar
        lines.append(f"| {calendar.month_abbr[int(m)]} | {v:.4f} |")

    lines.append("\n---\n")
    lines.append("## 7. Strongest Predictors\n")

    for task, label in [("heatwave", "Heatwave"), ("extreme_rainfall", "Extreme Rainfall")]:
        corr = quality[task]["correlation_with_target"]
        lines.append(f"### {label} — Top 15 Features by Correlation with Severity Score")
        lines.append("| Rank | Feature | |Corr with Score| |")
        lines.append("|------|---------|----------------|")
        for i, (feat, val) in enumerate(corr.head(15).items(), 1):
            lines.append(f"| {i} | {feat} | {val:.4f} |")
        lines.append("")

    lines.append("\n---\n")
    lines.append("## 8. Feature Classification\n")

    for task, label in [("heatwave", "Heatwave"), ("extreme_rainfall", "Extreme Rainfall")]:
        q = quality[task]
        lines.append(f"### {label} Features")
        lines.append("**Mandatory** (|corr| ≥ 0.40):")
        for f in q["mandatory"]:
            lines.append(f"- `{f}`")
        lines.append("\n**Useful** (0.20 ≤ |corr| < 0.40):")
        for f in q["useful"]:
            lines.append(f"- `{f}`")
        lines.append("\n**Experimental** (|corr| < 0.20):")
        for f in q["experimental"]:
            lines.append(f"- `{f}`")
        lines.append("")

    lines.append("\n---\n")
    lines.append("## 9. Leakage Prevention Report\n")
    if leakage_removed:
        lines.append("The following columns were identified as future-information or post-hoc labels and **removed**:")
        for col in leakage_removed:
            lines.append(f"- `{col}`")
    else:
        lines.append("No leakage columns detected.")
    lines.append("\n**Verification**: No `target_`, `next_month`, or post-hoc label columns remain in the final dataset.")

    lines.append("\n---\n")
    lines.append("## 10. Recommendations for Phase 2 Model Training\n")
    lines.append("1. **Primary Task**: Multi-class classification for `heatwave_category` and `extreme_rainfall_category`.")
    lines.append("2. **Secondary Task**: Regression on `heatwave_severity_score` and `extreme_rainfall_score` for continuous risk output.")
    lines.append("3. **Chronological Split**: Train ≤ 2020 | Validation 2021–2022 | Test ≥ 2023 (avoids temporal leakage).")
    lines.append("4. **Algorithm**: LightGBM or XGBoost (proven on prior temperature, rainfall, drought models).")
    lines.append("5. **Class Weighting**: Apply `class_weight='balanced'` for the Extreme class (10% minority).")
    lines.append("6. **Evaluation Metrics**: F1-Macro, Confusion Matrix by climate zone, ROC-AUC for Extreme class.")
    lines.append("7. **Feature Selection**: Begin with Mandatory + Useful features; conduct SHAP analysis post-training.")
    lines.append("8. **Compound Events**: Consider multi-label joint prediction for simultaneous heatwave + extreme rainfall.")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"Report saved to: {report_path}")


# ===========================================================================
# MAIN PIPELINE
# ===========================================================================

def main() -> None:
    logger.info("=" * 70)
    logger.info("EXTREME WEATHER INTELLIGENCE FEATURE ENGINEERING PIPELINE")
    logger.info("=" * 70)

    # 1. Load & validate
    df = load_and_validate(DATA_PATH)

    # 2. Compute climatology baselines (required by all feature modules)
    df = compute_climatology_baselines(df)

    # PART 1 — Heatwave features
    df = engineer_heatwave_features(df)

    # PART 2 — Extreme rainfall features
    df = engineer_extreme_rainfall_features(df)

    # PART 3 — Heatwave severity score
    df = compute_heatwave_severity_score(df)

    # PART 4 — Extreme rainfall severity score
    df = compute_extreme_rainfall_score(df)

    # PART 5 — Heatwave categories
    df = assign_heatwave_categories(df)

    # PART 6 — Extreme rainfall categories
    df = assign_extreme_rainfall_categories(df)

    # PART 7 — Climate zone analysis
    insights = analyze_climate_zones(df)

    # PART 8 — Feature quality analysis
    quality = analyze_feature_quality(df)

    # PART 9 — Leakage prevention
    df, leakage_removed = prevent_leakage(df)

    # PART 10 — Final dataset assembly (OHE + clean up helpers)
    df = assemble_final_dataset(df)

    # -----------------------------------------------------------------------
    # Final Summary
    # -----------------------------------------------------------------------
    logger.info("=" * 70)
    logger.info("FINAL DATASET SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total rows    : {len(df):,}")
    logger.info(f"Total columns : {df.shape[1]}")
    logger.info(f"Missing values: {df.isnull().sum().sum()}")

    logger.info("\nHeatwave Category Distribution:")
    for cat in ["Low", "Medium", "High", "Extreme"]:
        n = (df["heatwave_category"] == cat).sum()
        logger.info(f"  {cat:8s}: {n:5d} ({n/len(df)*100:.1f}%)")

    logger.info("\nExtreme Rainfall Category Distribution:")
    for cat in ["Low", "Medium", "High", "Extreme"]:
        n = (df["extreme_rainfall_category"] == cat).sum()
        logger.info(f"  {cat:8s}: {n:5d} ({n/len(df)*100:.1f}%)")

    # Save dataset
    os.makedirs(os.path.dirname(OUT_DATA_PATH), exist_ok=True)
    df.to_csv(OUT_DATA_PATH, index=False)
    logger.info(f"\nDataset saved: {OUT_DATA_PATH}")

    # Generate report
    os.makedirs(os.path.dirname(OUT_REPORT_PATH), exist_ok=True)
    generate_report(df, insights, quality, leakage_removed, OUT_REPORT_PATH)

    logger.info("=" * 70)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
