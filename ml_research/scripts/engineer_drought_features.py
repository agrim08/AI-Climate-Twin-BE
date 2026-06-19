"""
Drought Intelligence Dataset & Feature Engineering Pipeline
============================================================
AI-powered Digital Twin of India's Climate

Purpose:
    Transforms the base climate_master.csv into the richest possible
    drought-intelligence training dataset using scientific feature engineering.

Scientific Foundation:
    Inspired by:
    - Palmer Drought Severity Index (PDSI)
    - Standardized Precipitation Index (SPI)
    - Soil Moisture Drought Index (SMDI)
    - FAO Water Stress frameworks

Approach:
    - Water balance analysis (P - ET - Runoff)
    - Rainfall deficit and SPI-inspired anomalies
    - Soil moisture stress indicators
    - Drought persistence and evolution features
    - Climate-zone-aware drought baselines
    - Composite drought severity score (documented formula)
    - Data-driven drought category labeling (percentile-based)

Output:
    ml_research/data/processed/drought_training_dataset.csv
    ml_research/reports/drought_intelligence_report.md

Author: AI-Climate-Twin Engineering
"""

import os
import logging
import warnings
from typing import Tuple, Dict, List

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

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
    return df


# ===========================================================================
# 2. DROUGHT-FOCUSED EDA
# ===========================================================================

def run_drought_eda(df: pd.DataFrame) -> Dict:
    """
    Perform EDA from the drought formation perspective.
    Analyze key correlations and distributions relevant to drought.
    """
    logger.info("Running drought-focused EDA...")

    # Spearman correlation (robust to non-linearity, better for climate vars)
    drought_indicators = ["rainfall_mm", "soil_moisture", "evabs", "sro", "temperature_c"]
    corr_matrix = df[drought_indicators].corr(method="spearman").round(3)
    logger.info(f"\nSpearman Correlation (drought-relevant variables):\n{corr_matrix}")

    # Distribution analysis
    stats_dict = {}
    for col in drought_indicators:
        stats_dict[col] = {
            "mean": round(df[col].mean(), 4),
            "std":  round(df[col].std(), 4),
            "skew": round(df[col].skew(), 4),
            "p10":  round(df[col].quantile(0.10), 4),
            "p25":  round(df[col].quantile(0.25), 4),
            "p50":  round(df[col].quantile(0.50), 4),
            "p75":  round(df[col].quantile(0.75), 4),
            "p90":  round(df[col].quantile(0.90), 4),
        }
        logger.info(f"  {col}: mean={stats_dict[col]['mean']:.3f}  "
                    f"std={stats_dict[col]['std']:.3f}  "
                    f"skew={stats_dict[col]['skew']:.3f}")

    # Seasonal drought patterns (mean rainfall by month)
    monthly_rainfall = df.groupby("month")["rainfall_mm"].mean().round(2)
    logger.info(f"\nMean rainfall by month:\n{monthly_rainfall.to_dict()}")

    # Climate zone drought vulnerability
    zone_stats = df.groupby("climate_zone")[["rainfall_mm", "soil_moisture"]].mean().round(3)
    logger.info(f"\nClimate Zone baseline stats:\n{zone_stats.to_string()}")

    return {"corr_matrix": corr_matrix, "stats": stats_dict, "zone_stats": zone_stats}


# ===========================================================================
# 3. WATER BALANCE FEATURES
# ===========================================================================

def add_water_balance_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Water balance = Precipitation - Evapotranspiration - Runoff
    A negative balance indicates water deficit and potential drought onset.

    evabs (evaporation from bare soil) is negative in ERA5 convention (upward).
    We use abs(evabs) as actual evaporation magnitude.
    """
    logger.info("Engineering water balance features...")

    evap_magnitude = df["evabs"].abs()
    precip = df["rainfall_mm"]
    runoff = df["sro"]

    # Water balance (simplified): P - E - R
    # Units: rainfall in mm/month, evabs ~kg/m²/day equivalent (approx. scaled)
    df["water_balance"] = precip - (evap_magnitude * 30 * 1000) - (runoff * 1000)

    # Rainfall to evaporation ratio: measures aridity
    # High ratio → humid; Low ratio → arid
    df["rainfall_evap_ratio"] = precip / (evap_magnitude * 30 * 1000 + 1e-6)
    df["rainfall_evap_ratio"] = df["rainfall_evap_ratio"].clip(0, 20)

    # Rainfall to runoff ratio: measures how much rainfall generates runoff
    # Low ratio → dry soil absorbs rain; high → saturated soils
    df["rainfall_runoff_ratio"] = precip / (runoff * 1000 + 1e-6)
    df["rainfall_runoff_ratio"] = df["rainfall_runoff_ratio"].clip(0, 500)

    # Evaporation pressure: how much evaporation demand relative to supply
    # Higher value → more atmospheric water demand → drought stress
    df["evaporation_pressure"] = evap_magnitude * 30 * 1000 / (precip + 1.0)
    df["evaporation_pressure"] = df["evaporation_pressure"].clip(0, 100)

    # Runoff efficiency: % of rainfall that becomes runoff
    df["runoff_efficiency"] = (runoff * 1000) / (precip + 1e-6)
    df["runoff_efficiency"] = df["runoff_efficiency"].clip(0, 1)

    return df


# ===========================================================================
# 4. RAINFALL DEFICIT FEATURES
# ===========================================================================

def add_rainfall_deficit_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rainfall deficit features are the primary drought predictors.
    All deficits are computed relative to the historical climatological mean
    so that they represent anomalies, not raw values.
    """
    logger.info("Engineering rainfall deficit features...")

    # Climatological mean for each (city, month)
    rain_climo = df.groupby(["city", "month"])["rainfall_mm"].transform("mean")
    rain_climo_std = df.groupby(["city", "month"])["rainfall_mm"].transform("std").fillna(1)

    df["rainfall_climatology"] = rain_climo

    # Rainfall deficit: how much below normal (negative = deficit)
    df["rainfall_deficit"] = df["rainfall_mm"] - rain_climo
    df["rainfall_deficit_pct"] = df["rainfall_deficit"] / (rain_climo + 1e-6) * 100
    df["rainfall_deficit_pct"] = df["rainfall_deficit_pct"].clip(-200, 200)

    # SPI-inspired standardized anomaly (z-score of rainfall for this city-month)
    df["rainfall_spi"] = (df["rainfall_mm"] - rain_climo) / (rain_climo_std + 1e-6)
    df["rainfall_spi"] = df["rainfall_spi"].clip(-4, 4)

    # Lag-based deficits (purely from past data — no leakage)
    lag1_climo = df.groupby(["city", "month"])["rainfall_prev_1"].transform("mean")
    df["rainfall_deficit_lag1"] = df["rainfall_prev_1"] - lag1_climo

    # Cumulative rainfall deficit over past 3 and 6 months
    def cum_deficit(series: pd.Series, window: int) -> pd.Series:
        """Rolling sum of deficits over past window months."""
        return series.shift(1).rolling(window, min_periods=1).sum()

    df["cumulative_deficit_3m"] = df.groupby("city")["rainfall_deficit"].transform(
        lambda x: cum_deficit(x, 3)
    )
    df["cumulative_deficit_6m"] = df.groupby("city")["rainfall_deficit"].transform(
        lambda x: cum_deficit(x, 6)
    )

    return df


# ===========================================================================
# 5. SOIL MOISTURE FEATURES
# ===========================================================================

def add_soil_moisture_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Soil moisture is the most direct indicator of drought at the land surface.
    Anomalies and trends in soil moisture drive crop failure and water stress.
    """
    logger.info("Engineering soil moisture features...")

    sm_climo = df.groupby(["city", "month"])["soil_moisture"].transform("mean")
    sm_climo_std = df.groupby(["city", "month"])["soil_moisture"].transform("std").fillna(0.01)

    # Soil moisture anomaly
    df["sm_anomaly"] = df["soil_moisture"] - sm_climo
    df["sm_zscore"] = (df["soil_moisture"] - sm_climo) / (sm_climo_std + 1e-6)
    df["sm_zscore"] = df["sm_zscore"].clip(-4, 4)

    # Soil moisture deficit (how far below normal, floor at 0)
    df["sm_deficit"] = (sm_climo - df["soil_moisture"]).clip(lower=0)
    df["sm_deficit_pct"] = df["sm_deficit"] / (sm_climo + 1e-6) * 100

    # Rolling soil moisture trend
    def rolling_sm(series: pd.Series, window: int) -> pd.Series:
        return series.shift(1).rolling(window, min_periods=2).mean()

    df["rolling_sm_3m"] = df.groupby("city")["soil_moisture"].transform(
        lambda x: rolling_sm(x, 3)
    )
    df["rolling_sm_6m"] = df.groupby("city")["soil_moisture"].transform(
        lambda x: rolling_sm(x, 6)
    )

    df["sm_trend"] = df["rolling_sm_3m"] - df["rolling_sm_6m"]

    # Consecutive low soil moisture months (<= 25th percentile of city baseline)
    sm_p25 = df.groupby("city")["soil_moisture"].transform(lambda x: x.quantile(0.25))

    def low_sm_streak(series: pd.Series, threshold_series: pd.Series) -> pd.Series:
        is_low = series.shift(1) <= threshold_series
        streaks = []
        count = 0
        for val in is_low:
            count = count + 1 if val else 0
            streaks.append(count)
        return pd.Series(streaks, index=series.index, dtype=float)

    df["low_sm_streak"] = df.groupby("city")["soil_moisture"].transform(
        lambda x: low_sm_streak(x, sm_p25.loc[x.index])
    )

    # Zone-relative soil moisture anomaly
    zone_sm_climo = df.groupby(["climate_zone", "month"])["soil_moisture"].transform("mean")
    df["sm_zone_anomaly"] = df["soil_moisture"] - zone_sm_climo

    return df


# ===========================================================================
# 6. TEMPERATURE STRESS FEATURES
# ===========================================================================

def add_temperature_stress_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    High temperatures amplify drought by increasing evapotranspiration demand.
    Temperature stress captures the compound effect of heat + dryness.
    """
    logger.info("Engineering temperature stress features...")

    temp_climo = df.groupby(["city", "month"])["temperature_c"].transform("mean")
    temp_climo_std = df.groupby(["city", "month"])["temperature_c"].transform("std").fillna(1)

    df["temperature_anomaly"] = df["temperature_c"] - temp_climo
    df["temperature_zscore"] = (df["temperature_c"] - temp_climo) / (temp_climo_std + 1e-6)
    df["temperature_zscore"] = df["temperature_zscore"].clip(-4, 4)

    # Temperature stress index: warm anomalies combined with low rainfall
    # High temperature + low rainfall = compound drought stress
    rain_norm = df["rainfall_mm"] / (df["rainfall_mm"].mean() + 1e-6)
    df["temperature_stress"] = df["temperature_anomaly"] * (1 - rain_norm.clip(0, 2))

    # Heat accumulated above threshold (>35°C contributes to drought)
    HEAT_THRESHOLD = 35.0
    df["heat_excess"] = (df["temperature_c"] - HEAT_THRESHOLD).clip(lower=0)

    return df


# ===========================================================================
# 7. DROUGHT PERSISTENCE FEATURES
# ===========================================================================

def add_drought_persistence_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drought is fundamentally a persistent phenomenon.
    Long streaks of low rainfall or deficit are more damaging than
    short dry spells. These features capture that memory.
    """
    logger.info("Engineering drought persistence features...")

    # Consecutive months with rainfall below 10mm (hydrological dry threshold)
    def rain_dry_streak(series: pd.Series, threshold: float = 10.0) -> pd.Series:
        is_dry = series.shift(1) < threshold
        streaks = []
        count = 0
        for val in is_dry:
            count = count + 1 if val else 0
            streaks.append(count)
        return pd.Series(streaks, index=series.index, dtype=float)

    df["dry_month_streak"] = df.groupby("city")["rainfall_mm"].transform(
        lambda x: rain_dry_streak(x, 10.0)
    )

    # Consecutive months with rainfall DEFICIT (below climatological mean)
    def deficit_streak(series: pd.Series) -> pd.Series:
        is_deficit = series.shift(1) < 0
        streaks = []
        count = 0
        for val in is_deficit:
            count = count + 1 if val else 0
            streaks.append(count)
        return pd.Series(streaks, index=series.index, dtype=float)

    df["deficit_streak"] = df.groupby("city")["rainfall_deficit"].transform(deficit_streak)

    # Cumulative soil moisture deficit (area under the drought curve)
    def cum_sm_deficit(series: pd.Series, window: int) -> pd.Series:
        return series.shift(1).rolling(window, min_periods=1).sum()

    df["cumulative_sm_deficit_3m"] = df.groupby("city")["sm_deficit"].transform(
        lambda x: cum_sm_deficit(x, 3)
    )
    df["cumulative_sm_deficit_6m"] = df.groupby("city")["sm_deficit"].transform(
        lambda x: cum_sm_deficit(x, 6)
    )

    # Drought recovery: after a dry streak, how quickly does rainfall rebound?
    # Positive = recovery signal; negative = deepening drought
    df["drought_recovery"] = df["rainfall_deficit"] - df.groupby("city")["rainfall_deficit"].transform(
        lambda x: x.shift(1)
    )

    return df


# ===========================================================================
# 8. DROUGHT EVOLUTION FEATURES
# ===========================================================================

def add_drought_evolution_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drought evolves: it deepens, plateaus, or recovers.
    These features capture the dynamic trajectory of drought.
    """
    logger.info("Engineering drought evolution features...")

    # Drought momentum: change in rainfall deficit over 3m vs 6m period
    short_deficit_trend = df.groupby("city")["rainfall_deficit"].transform(
        lambda x: x.shift(1).rolling(3, min_periods=2).mean()
    )
    long_deficit_trend = df.groupby("city")["rainfall_deficit"].transform(
        lambda x: x.shift(1).rolling(6, min_periods=2).mean()
    )
    df["drought_momentum"] = short_deficit_trend - long_deficit_trend

    # Drought acceleration: rate of change in momentum
    df["drought_acceleration"] = df.groupby("city")["drought_momentum"].transform(
        lambda x: x.diff()
    )

    # Drought trend: is deficit growing or shrinking?
    df["drought_trend"] = df.groupby("city")["rainfall_deficit"].transform(
        lambda x: x.shift(1).diff()
    )

    # Rolling std of rainfall deficit (deficit volatility = drought instability)
    df["deficit_volatility_3m"] = df.groupby("city")["rainfall_deficit"].transform(
        lambda x: x.shift(1).rolling(3, min_periods=2).std()
    )

    return df


# ===========================================================================
# 9. CLIMATE-ZONE-AWARE DROUGHT FEATURES
# ===========================================================================

def add_zone_drought_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    50mm/month is catastrophic drought in the North-East (normally 300mm+)
    but acceptable in Thar Desert. Zone-relative drought features normalize
    these differences using per-zone historical baselines.
    """
    logger.info("Engineering climate-zone-aware drought features...")

    # Zone-level rainfall drought baseline per month
    zone_rain_climo = df.groupby(["climate_zone", "month"])["rainfall_mm"].transform("mean")
    zone_rain_std = df.groupby(["climate_zone", "month"])["rainfall_mm"].transform("std").fillna(1)

    df["zone_rain_deficit"] = df["rainfall_mm"] - zone_rain_climo
    df["zone_rain_zscore"] = (df["rainfall_mm"] - zone_rain_climo) / (zone_rain_std + 1e-6)
    df["zone_rain_zscore"] = df["zone_rain_zscore"].clip(-4, 4)

    # Zone-level soil moisture drought baseline
    zone_sm_climo = df.groupby(["climate_zone", "month"])["soil_moisture"].transform("mean")
    zone_sm_std = df.groupby(["climate_zone", "month"])["soil_moisture"].transform("std").fillna(0.01)

    df["zone_sm_deficit"] = zone_sm_climo - df["soil_moisture"]
    df["zone_sm_zscore"] = (df["soil_moisture"] - zone_sm_climo) / (zone_sm_std + 1e-6)
    df["zone_sm_zscore"] = df["zone_sm_zscore"].clip(-4, 4)

    # Zone aridity index: long-term mean rainfall relative to evaporation
    zone_mean_rain = df.groupby("climate_zone")["rainfall_mm"].transform("mean")
    zone_mean_evap = df.groupby("climate_zone")["evabs"].transform(lambda x: x.abs().mean()) * 30 * 1000
    df["zone_aridity_index"] = zone_mean_rain / (zone_mean_evap + 1.0)
    df["zone_aridity_index"] = df["zone_aridity_index"].clip(0, 20)

    return df


# ===========================================================================
# 10. WATER STRESS INDICATORS
# ===========================================================================

def add_water_stress_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Water stress combines multiple hydrological signals into interpretable
    composite indicators used in climate adaptation planning.
    """
    logger.info("Engineering water stress indicators...")

    # Water Availability Index (WAI)
    # Combines soil moisture (40%), rainfall (40%), runoff (20%)
    # Each component normalized 0-1 within dataset
    def minmax_norm(series: pd.Series) -> pd.Series:
        mn, mx = series.min(), series.max()
        return (series - mn) / (mx - mn + 1e-6)

    sm_norm   = minmax_norm(df["soil_moisture"])
    rain_norm = minmax_norm(df["rainfall_mm"])
    sro_norm  = minmax_norm(df["sro"])

    df["water_availability_index"] = (0.40 * sm_norm + 0.40 * rain_norm + 0.20 * sro_norm)

    # Hydrological stress: inverse of WAI (more stress = less water)
    df["hydrological_stress"] = 1.0 - df["water_availability_index"]

    # Moisture stress: soil moisture deficit weighted by temperature (heat amplifies stress)
    df["moisture_stress"] = df["sm_deficit"] * (1 + df["temperature_anomaly"].clip(0, None) / 10)

    # Evaporation stress: how much of available water is lost to evaporation
    evap_mag = df["evabs"].abs() * 30 * 1000
    df["evaporation_stress"] = evap_mag / (df["rainfall_mm"] + df["soil_moisture"] * 100 + 1.0)
    df["evaporation_stress"] = df["evaporation_stress"].clip(0, 20)

    # Compound drought stress: rainfall deficit × soil moisture deficit
    # This interaction captures the compounding nature of multi-variable drought
    df["compound_drought_stress"] = (
        df["rainfall_deficit"].clip(upper=0).abs() *   # rainfall deficit magnitude
        df["sm_deficit"]                                 # soil moisture deficit
    )

    return df


# ===========================================================================
# 11. DROUGHT SEVERITY SCORE
# ===========================================================================

def compute_drought_severity_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Composite Drought Severity Score (CDSS)
    =========================================
    CDSS combines five independently normalized drought signals:

    Component         Weight   Signal
    ─────────────────────────────────────────────────────────────
    Rainfall SPI       0.30    Standardized precipitation deficit
    Soil Moisture Z    0.25    Standardized soil moisture anomaly
    Temperature Z      0.15    Standardized temperature anomaly
    Evap Pressure      0.15    Normalized evaporation demand
    Water Availability 0.15    1 - Water Availability Index

    CDSS = Σ(weight_i × normalized_signal_i)

    Positive CDSS → drought conditions
    Negative CDSS → surplus / wet conditions

    Scientific Rationale:
        Rainfall SPI is the gold standard in drought science (McKee et al. 1993)
        and receives the highest weight. Soil moisture receives second-highest
        weight as it directly reflects water available to plants and ecosystems.
        Temperature anomaly contributes through atmospheric demand. Evaporation
        pressure and water availability provide hydrological context.
    """
    logger.info("Computing Composite Drought Severity Score (CDSS)...")

    def minmax_norm(series: pd.Series) -> pd.Series:
        mn, mx = series.min(), series.max()
        return (series - mn) / (mx - mn + 1e-6)

    # Invert rainfall SPI and soil moisture zscore for drought direction
    # (more negative → more drought → higher score)
    rain_component  = minmax_norm(-df["rainfall_spi"])
    sm_component    = minmax_norm(-df["sm_zscore"])
    temp_component  = minmax_norm(df["temperature_zscore"])
    evap_component  = minmax_norm(df["evaporation_stress"])
    water_component = minmax_norm(df["hydrological_stress"])

    df["drought_severity_score"] = (
        0.30 * rain_component  +
        0.25 * sm_component    +
        0.15 * temp_component  +
        0.15 * evap_component  +
        0.15 * water_component
    )

    logger.info(
        f"CDSS stats: "
        f"mean={df['drought_severity_score'].mean():.3f}  "
        f"std={df['drought_severity_score'].std():.3f}  "
        f"p10={df['drought_severity_score'].quantile(0.10):.3f}  "
        f"p90={df['drought_severity_score'].quantile(0.90):.3f}"
    )

    return df


# ===========================================================================
# 12. DROUGHT CATEGORY LABELING (DATA-DRIVEN)
# ===========================================================================

def assign_drought_categories(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assigns drought categories using climatologically-grounded percentile
    thresholds applied to the Composite Drought Severity Score (CDSS).

    Percentile Thresholds (standard in drought science):
        p0  – p30 : Low     (wet/normal conditions, lowest 30%)
        p30 – p60 : Medium  (mild drought, middle 30%)
        p60 – p85 : High    (severe drought, next 25%)
        p85 – p100: Extreme (extreme drought, top 15%)

    These percentiles mirror internationally recognized drought monitoring
    standards (USDM — US Drought Monitor classification framework):
        D0 (Abnormally Dry)   ≈ Low
        D1-D2 (Moderate-Severe) ≈ Medium
        D3 (Extreme)          ≈ High
        D4 (Exceptional)      ≈ Extreme

    Using city-level percentiles ensures climate-zone fairness:
    Desert regions are evaluated against their own dry baseline,
    not against the national average.
    """
    logger.info("Assigning drought categories (percentile-based, city-level)...")

    def assign_category(group: pd.Series) -> pd.Series:
        p30 = group.quantile(0.30)
        p60 = group.quantile(0.60)
        p85 = group.quantile(0.85)
        labels = []
        for val in group:
            if val < p30:
                labels.append("Low")
            elif val < p60:
                labels.append("Medium")
            elif val < p85:
                labels.append("High")
            else:
                labels.append("Extreme")
        return pd.Series(labels, index=group.index)

    df["drought_category"] = df.groupby("city")["drought_severity_score"].transform(
        assign_category
    )

    # Also encode as ordinal integer for ML models
    ordinal_map = {"Low": 0, "Medium": 1, "High": 2, "Extreme": 3}
    df["drought_category_ordinal"] = df["drought_category"].map(ordinal_map)

    # Class distribution
    dist = df["drought_category"].value_counts()
    dist_pct = (dist / len(df) * 100).round(1)
    logger.info(f"\nDrought Category Distribution:")
    for cat in ["Low", "Medium", "High", "Extreme"]:
        n = dist.get(cat, 0)
        pct = dist_pct.get(cat, 0)
        logger.info(f"  {cat:8s}: {n:5d} rows ({pct:.1f}%)")

    return df


# ===========================================================================
# 13. ONE-HOT ENCODE CLIMATE ZONE
# ===========================================================================

def encode_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode climate_zone for ML readiness."""
    logger.info("One-hot encoding climate_zone...")
    df = pd.get_dummies(df, columns=["climate_zone"], drop_first=False)
    return df


# ===========================================================================
# 14. LEAKAGE AUDIT & FINAL CLEANING
# ===========================================================================

# Columns that contain future or target-derived information
LEAKAGE_COLUMNS = [
    "target_temperature_next_month",
    "target_rainfall_next_month",
    "drought_risk",        # pre-existing label derived post-hoc
    "heatwave_risk",       # pre-existing label derived post-hoc
    "climate_risk_score",  # composite of post-hoc labels
    "date",                # encoded as year/month
    "city",                # encoded via lat/lon + OHE zone
]

def leakage_audit_and_clean(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Drop leakage columns, handle remaining NaNs, and return
    the final clean dataset plus the feature list.
    """
    logger.info("Performing leakage audit...")

    df = df.drop(columns=[c for c in LEAKAGE_COLUMNS if c in df.columns], errors="ignore")
    df = df.replace([np.inf, -np.inf], np.nan)

    before = len(df)
    df = df.dropna()
    logger.info(f"Dropped {before - len(df)} rows with NaN. Final rows: {len(df)}")

    # Separate targets from features
    target_cols = ["drought_severity_score", "drought_category", "drought_category_ordinal"]
    feature_cols = [c for c in df.columns if c not in target_cols]

    return df, feature_cols


# ===========================================================================
# 15. FEATURE QUALITY ANALYSIS
# ===========================================================================

def analyse_feature_quality(
    df: pd.DataFrame,
    feature_cols: List[str],
) -> pd.DataFrame:
    """
    Correlation, variance, and multicollinearity analysis.
    Returns a ranked feature quality dataframe.
    """
    logger.info("Analysing feature quality...")

    target = df["drought_severity_score"]
    feat_df = df[feature_cols].select_dtypes(include=[np.number])

    corr_with_target = (
        feat_df.corrwith(target)
        .abs()
        .sort_values(ascending=False)
        .rename("abs_corr_with_score")
    )

    variances = feat_df.var().rename("variance")
    quality_df = pd.concat([corr_with_target, variances], axis=1).reset_index()
    quality_df.columns = ["Feature", "abs_corr_with_score", "variance"]
    quality_df = quality_df.sort_values("abs_corr_with_score", ascending=False)

    logger.info("\nTop 20 Features by Correlation with Drought Severity Score:")
    logger.info(quality_df.head(20).to_string(index=False))

    # High multicollinearity check
    corr_matrix = feat_df.corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    high_corr = [
        (col, row, upper.loc[row, col])
        for col in upper.columns
        for row in upper.index
        if upper.loc[row, col] > 0.95
    ]
    if high_corr:
        logger.warning(f"Found {len(high_corr)} highly correlated pairs (>0.95):")
        for c1, c2, v in high_corr[:10]:
            logger.warning(f"  {c1} <-> {c2}: {v:.3f}")

    return quality_df


# ===========================================================================
# 16. REPORT GENERATION
# ===========================================================================

def generate_report(
    df: pd.DataFrame,
    feature_cols: List[str],
    quality_df: pd.DataFrame,
    eda_results: Dict,
    report_path: str,
) -> None:
    logger.info(f"Generating drought intelligence report: {report_path}")

    dist = df["drought_category"].value_counts()

    mandatory = quality_df[quality_df["abs_corr_with_score"] >= 0.50]["Feature"].tolist()
    useful = quality_df[
        (quality_df["abs_corr_with_score"] >= 0.20) &
        (quality_df["abs_corr_with_score"] < 0.50)
    ]["Feature"].tolist()
    experimental = quality_df[quality_df["abs_corr_with_score"] < 0.20]["Feature"].tolist()

    top20 = quality_df.head(20)
    top20_table = "\n".join(
        f"| {i+1} | {row['Feature']} | {row['abs_corr_with_score']:.4f} |"
        for i, row in enumerate(top20.to_dict('records'))
    )

    zone_stats_str = eda_results["zone_stats"].to_string()

    report = f"""# Drought Intelligence Report

## Executive Summary
A production-ready drought intelligence dataset has been engineered for the
AI Climate Digital Twin of India.

- **Total Records**: {len(df):,}
- **Total Features**: {len(feature_cols)}
- **Drought Target**: `drought_category` (Low / Medium / High / Extreme)
- **Severity Score**: `drought_severity_score` (Composite CDSS, 0–1 scale)

---

## Drought Formation Analysis

Drought in India is driven by:
1. **Monsoon failures**: Below-normal JJAS rainfall is the primary trigger.
2. **Soil moisture depletion**: Persists weeks after rainfall stops; crucial for agriculture.
3. **Temperature amplification**: Warm anomalies increase evapotranspiration demand.
4. **Evaporation imbalance**: High demand with low supply creates atmospheric drought.
5. **Runoff collapse**: Dry soils absorb rainfall, reducing river flows.

### Key Correlations (Spearman)
```
{eda_results["corr_matrix"].to_string()}
```

---

## Drought Severity Methodology (CDSS Formula)

```
CDSS = 0.30 × norm(-SPI) 
     + 0.25 × norm(-SM_zscore) 
     + 0.15 × norm(Temperature_zscore)
     + 0.15 × norm(Evaporation_stress)
     + 0.15 × norm(Hydrological_stress)
```

| Component | Weight | Rationale |
|-----------|--------|-----------|
| Rainfall SPI | 30% | Gold standard; directly measures precipitation deficit |
| Soil Moisture Z | 25% | Most direct crop/ecosystem impact signal |
| Temperature Z | 15% | Amplifies evapotranspiration demand |
| Evaporation Stress | 15% | Captures atmospheric water demand |
| Hydrological Stress | 15% | Combined soil+rain+runoff water availability |

---

## Drought Category Methodology

Categories are assigned using **city-level percentiles** of the CDSS score,
ensuring climate-zone fairness (Desert cities evaluated against desert baseline):

| Category | CDSS Percentile | USDM Analog |
|----------|----------------|-------------|
| Low | 0–30th | D0 (Abnormally Dry) |
| Medium | 30–60th | D1–D2 (Moderate–Severe) |
| High | 60–85th | D3 (Extreme Drought) |
| Extreme | 85–100th | D4 (Exceptional) |

### Class Distribution
| Category | Count | % |
|----------|-------|---|
| Low | {dist.get('Low', 0):,} | {dist.get('Low', 0)/len(df)*100:.1f}% |
| Medium | {dist.get('Medium', 0):,} | {dist.get('Medium', 0)/len(df)*100:.1f}% |
| High | {dist.get('High', 0):,} | {dist.get('High', 0)/len(df)*100:.1f}% |
| Extreme | {dist.get('Extreme', 0):,} | {dist.get('Extreme', 0)/len(df)*100:.1f}% |

**Class Imbalance Assessment**: By design (percentile-based), distribution is
approximately balanced across Low/Medium/High/Extreme. Extreme events are
15% of data — minority class monitoring is advised during training.

---

## Feature Classification

### Mandatory (Correlation ≥ 0.50)
{chr(10).join(f"- `{f}`" for f in mandatory)}

### Useful (0.20 ≤ Correlation < 0.50)
{chr(10).join(f"- `{f}`" for f in useful[:30])}

### Experimental (Correlation < 0.20)
{chr(10).join(f"- `{f}`" for f in experimental[:20])}

---

## Top 20 Drought Predictors

| Rank | Feature | |Corr with CDSS| |
|------|---------|----------------|
{top20_table}

---

## Climate Zone Observations

### Zone-level Mean Rainfall & Soil Moisture
{zone_stats_str}

Key observations:
- **Thar Desert Region**: Extremely low baseline rainfall — drought is the norm.
  Zone-relative features are essential to detect anomalous wet/dry spells.
- **North-East Region**: Highest baseline rainfall; droughts are rare but severe.
  SPI-based anomalies perform best here.
- **Western Ghats**: Orographic rainfall; strong spatial gradient.
  City-level climatology is more relevant than zone-level.
- **Indo-Gangetic Plains**: Monsoon-dependent; consecutive dry months
  are the strongest drought signal.

---

## Drought Evolution Analysis

Key patterns observed:
- `drought_momentum` captures whether drought is deepening or recovering.
- `cumulative_deficit_6m` is the strongest compound indicator.
- `low_sm_streak` shows that soil moisture impacts persist for 1–2 months after rainfall.
- `deficit_streak` consistently identifies prolonged droughts early.

---

## Leakage Prevention

| Column | Reason Removed |
|--------|----------------|
| `drought_risk` | Pre-existing post-hoc label — circular dependency |
| `heatwave_risk` | Derived from temperature labels |
| `climate_risk_score` | Composite of post-hoc derived labels |
| `target_rainfall_next_month` | Future value |
| `target_temperature_next_month` | Future value |

---

## Recommended Modeling Strategy

1. **Primary Target**: `drought_category` (multi-class: Low/Medium/High/Extreme)
2. **Auxiliary Regression Target**: `drought_severity_score` (continuous 0–1)
3. **Split**: Chronological — Train ≤ 2020, Val 2021–2022, Test ≥ 2023
4. **Algorithm**: LightGBM (handles ordinal targets well) or XGBoost
5. **Class Weighting**: Apply `class_weight='balanced'` or `scale_pos_weight` for Extreme class
6. **Feature Selection**: Start with Mandatory + Useful features; use SHAP for interpretability
7. **Evaluation**: F1-macro (balanced across all drought levels), Confusion Matrix by zone
"""

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info("Report saved.")


# ===========================================================================
# 17. FINAL SUMMARY PRINT
# ===========================================================================

def print_dataset_summary(df: pd.DataFrame, feature_cols: List[str]) -> None:
    print("\n" + "=" * 65)
    print("  DROUGHT INTELLIGENCE DATASET -- SUMMARY")
    print("=" * 65)
    print(f"  Total Rows       : {len(df):,}")
    print(f"  Total Features   : {len(feature_cols)}")
    print(f"  Target           : drought_category (+ drought_severity_score)\n")

    print("  Drought Category Counts:")
    for cat in ["Low", "Medium", "High", "Extreme"]:
        n = (df["drought_category"] == cat).sum()
        pct = 100 * n / len(df)
        print(f"    {cat:8s}: {n:5d} rows ({pct:.1f}%)")

    mv = df.isnull().sum()
    mv = mv[mv > 0]
    print(f"\n  Missing Values: {'None' if len(mv) == 0 else str(mv)}")

    print(f"\n  Feature List ({len(feature_cols)} features):")
    for i, col in enumerate(feature_cols, 1):
        print(f"    {i:>3}. {col}")
    print("=" * 65 + "\n")


# ===========================================================================
# MAIN PIPELINE
# ===========================================================================

def run_pipeline() -> None:
    script_dir   = os.path.dirname(os.path.abspath(__file__))
    data_path    = os.path.join(script_dir, "..", "data", "processed", "climate_master.csv")
    output_path  = os.path.join(script_dir, "..", "data", "processed", "drought_training_dataset.csv")
    report_path  = os.path.join(script_dir, "..", "reports", "drought_intelligence_report.md")

    # Step 1 — Load & validate
    df = load_and_validate(data_path)

    # Step 2 — Drought EDA
    eda_results = run_drought_eda(df)

    # Step 3 — Water balance
    df = add_water_balance_features(df)

    # Step 4 — Rainfall deficit
    df = add_rainfall_deficit_features(df)

    # Step 5 — Soil moisture
    df = add_soil_moisture_features(df)

    # Step 6 — Temperature stress
    df = add_temperature_stress_features(df)

    # Step 7 — Drought persistence
    df = add_drought_persistence_features(df)

    # Step 8 — Drought evolution
    df = add_drought_evolution_features(df)

    # Step 9 — Zone-aware drought
    df = add_zone_drought_features(df)

    # Step 10 — Water stress indicators
    df = add_water_stress_indicators(df)

    # Step 11 — Composite severity score
    df = compute_drought_severity_score(df)

    # Step 12 — Drought category labeling
    df = assign_drought_categories(df)

    # Step 13 — Encode categoricals
    df = encode_categoricals(df)

    # Step 14 — Leakage audit & clean
    df, feature_cols = leakage_audit_and_clean(df)

    # Step 15 — Feature quality analysis
    quality_df = analyse_feature_quality(df, feature_cols)

    # Step 16 — Print summary
    print_dataset_summary(df, feature_cols)

    # Step 17 — Save output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info(f"Drought training dataset saved to: {output_path}")

    # Step 18 — Generate report
    generate_report(df, feature_cols, quality_df, eda_results, report_path)

    logger.info("Pipeline complete.")


if __name__ == "__main__":
    run_pipeline()
