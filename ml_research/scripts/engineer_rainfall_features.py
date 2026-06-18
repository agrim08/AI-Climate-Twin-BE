"""
Rainfall Feature Engineering Pipeline
======================================
AI-powered Digital Twin of India's Climate

Purpose:
    Transforms the base climate_master.csv into the richest possible
    rainfall-ready training dataset using domain-driven feature engineering.

Approach:
    - Monsoon intelligence (onset / active / withdrawal / dry phases)
    - Rainfall anomaly and variability features
    - Momentum and acceleration features
    - Climate-zone-aware relative anomalies
    - Soil moisture, evaporation, and runoff trends
    - Strict leakage prevention (no future information used)

Output:
    ml_research/data/processed/climate_master_rainfall.csv

Author: AI-Climate-Twin Engineering
"""

import os
import logging
import warnings
from typing import Tuple

import numpy as np
import pandas as pd

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

    # Replace infinities
    df = df.replace([np.inf, -np.inf], np.nan)

    # Drop rows with missing target
    before = len(df)
    df = df.dropna(subset=["rainfall_mm", "target_rainfall_next_month"])
    logger.info(f"Dropped {before - len(df)} rows missing target. Remaining: {len(df)}")

    # Drop duplicates
    before = len(df)
    df = df.drop_duplicates(subset=["city", "date"])
    logger.info(f"Dropped {before - len(df)} duplicates. Remaining: {len(df)}")

    df = df.sort_values(["city", "date"]).reset_index(drop=True)
    return df


# ===========================================================================
# 2. MONSOON INTELLIGENCE FEATURES
# ===========================================================================

def add_monsoon_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Encode the Indian monsoon calendar with meteorological precision.

    Best-practice phase encoding based on IMD (India Meteorological Department)
    seasonal calendar:
        Pre-monsoon  : March, April, May (heat buildup, convective instability)
        Onset        : June (SW monsoon first arrives over Kerala ~June 1)
        Active       : July, August (peak monsoon; highest rainfall probability)
        Withdrawal   : September (monsoon retreats northward)
        Post-monsoon : October, November (NE monsoon; Tamil Nadu coast active)
        Winter-Dry   : December, January, February (dry, cold)

    is_monsoon captures the full JJAS window that drives ~70-80% of annual
    rainfall across most of India.
    """
    logger.info("Engineering monsoon intelligence features...")

    m = df["month"]

    # Binary flags
    df["is_monsoon"] = m.isin([6, 7, 8, 9]).astype(int)
    df["pre_monsoon"] = m.isin([3, 4, 5]).astype(int)
    df["post_monsoon"] = m.isin([10, 11]).astype(int)
    df["is_winter_dry"] = m.isin([12, 1, 2]).astype(int)

    # Ordinal monsoon phase (0–5)
    # Captures intra-monsoon progression; month 9 (withdrawal) is drier than
    # months 7-8 (peak), which a simple binary flag cannot express.
    phase_map = {
        1: 0,   # Winter-Dry
        2: 0,
        12: 0,
        3: 1,   # Pre-Monsoon
        4: 1,
        5: 1,
        6: 2,   # Onset
        7: 3,   # Active Peak
        8: 3,
        9: 4,   # Withdrawal
        10: 5,  # Post-Monsoon
        11: 5,
    }
    df["monsoon_phase"] = m.map(phase_map)

    # Cyclic encoding of monsoon phase so ML models understand circularity
    df["monsoon_phase_sin"] = np.sin(2 * np.pi * df["monsoon_phase"] / 6.0)
    df["monsoon_phase_cos"] = np.cos(2 * np.pi * df["monsoon_phase"] / 6.0)

    return df


# ===========================================================================
# 3. RAINFALL ANOMALY & VARIABILITY FEATURES
# ===========================================================================

def add_rainfall_anomaly_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create anomaly, variability, and persistence features for rainfall.

    All features are strictly computed from *past* data only to prevent leakage.
    Lag-1 means the previous month; rolling windows cover the preceding N months.
    """
    logger.info("Engineering rainfall anomaly and variability features...")

    # --- 3a. Long-term city-month climatology baseline ---
    # The historical mean rainfall for each (city, month) pair.
    # This is computed across the entire dataset (a static statistic) and is
    # safe to use as it describes long-term climate, not future observations.
    climo = (
        df.groupby(["city", "month"])["rainfall_mm"]
        .transform("mean")
    )
    df["rainfall_climatology"] = climo

    # Rainfall anomaly: how far current rainfall deviates from climatology
    df["rainfall_anomaly"] = df["rainfall_mm"] - df["rainfall_climatology"]
    df["rainfall_anomaly_pct"] = df["rainfall_anomaly"] / (df["rainfall_climatology"] + 1e-6)

    # --- 3b. Variability (rolling std over past windows) ---
    # Per-city rolling so we don't bleed between cities
    def rolling_std(series: pd.Series, window: int) -> pd.Series:
        return series.shift(1).rolling(window, min_periods=2).std()

    df["rolling_rainfall_std_3m"] = (
        df.groupby("city")["rainfall_mm"]
        .transform(lambda x: rolling_std(x, 3))
    )
    df["rolling_rainfall_std_6m"] = (
        df.groupby("city")["rainfall_mm"]
        .transform(lambda x: rolling_std(x, 6))
    )

    # Coefficient of variation (normalised variability)
    df["rolling_rainfall_cv_3m"] = (
        df["rolling_rainfall_std_3m"] / (df["rolling_rainfall_3m"] + 1e-6)
    )

    # --- 3c. Rolling median (robust to extreme events) ---
    def rolling_med(series: pd.Series, window: int) -> pd.Series:
        return series.shift(1).rolling(window, min_periods=2).median()

    df["rolling_rainfall_median_3m"] = (
        df.groupby("city")["rainfall_mm"]
        .transform(lambda x: rolling_med(x, 3))
    )
    df["rolling_rainfall_median_6m"] = (
        df.groupby("city")["rainfall_mm"]
        .transform(lambda x: rolling_med(x, 6))
    )

    # --- 3d. Persistence indicators ---
    # Consecutive dry months (rainfall < 5 mm) — key drought precursor
    def dry_streak(series: pd.Series, threshold: float = 5.0) -> pd.Series:
        is_dry = series.shift(1) < threshold
        streaks = []
        count = 0
        for val in is_dry:
            if val:
                count += 1
            else:
                count = 0
            streaks.append(count)
        return pd.Series(streaks, index=series.index, dtype=float)

    df["dry_months_streak"] = df.groupby("city")["rainfall_mm"].transform(dry_streak)

    # Consecutive wet months (rainfall > 50 mm) — monsoon persistence
    def wet_streak(series: pd.Series, threshold: float = 50.0) -> pd.Series:
        is_wet = series.shift(1) > threshold
        streaks = []
        count = 0
        for val in is_wet:
            if val:
                count += 1
            else:
                count = 0
            streaks.append(count)
        return pd.Series(streaks, index=series.index, dtype=float)

    df["wet_months_streak"] = df.groupby("city")["rainfall_mm"].transform(wet_streak)

    return df


# ===========================================================================
# 4. RAINFALL MOMENTUM & TREND FEATURES
# ===========================================================================

def add_rainfall_momentum_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Capture rainfall change dynamics: trend, growth rate, acceleration.

    These features answer: "Is rainfall increasing or decreasing, and how fast?"
    This is critical for monsoon onset and retreat prediction.
    """
    logger.info("Engineering rainfall momentum and trend features...")

    # --- Rainfall change (prev_1 - prev_3): 2-month trend direction ---
    df["rainfall_trend"] = df["rainfall_prev_1"] - df["rainfall_prev_3"]

    # --- Rainfall acceleration (change in the rate of change) ---
    # Approximated as: (prev_1 - rolling_3m) vs. (rolling_3m - rolling_6m)
    short_trend = df["rainfall_prev_1"] - df["rolling_rainfall_3m"]
    long_trend = df["rolling_rainfall_3m"] - df["rolling_rainfall_6m"]
    df["rainfall_acceleration"] = short_trend - long_trend

    # --- Rainfall growth rate (percentage change from lag-3 to lag-1) ---
    df["rainfall_growth_rate"] = (
        (df["rainfall_prev_1"] - df["rainfall_prev_3"])
        / (df["rainfall_prev_3"] + 1e-6)
    )
    # Clip extreme growth rates (division by near-zero in arid months)
    df["rainfall_growth_rate"] = df["rainfall_growth_rate"].clip(-10, 10)

    # --- Rainfall momentum (lag-1 relative to climatological baseline) ---
    df["rainfall_momentum"] = (
        df["rainfall_prev_1"] - df["rainfall_climatology"]
    )

    # --- Seasonal deviation: lag-1 vs same-month mean (climate anomaly signal) ---
    prev_month = (df["month"] - 1).replace(0, 12)
    prev_month_climo = (
        df.groupby(["city", "month"])["rainfall_mm"]
        .mean()
        .reset_index()
        .rename(columns={"month": "prev_month", "rainfall_mm": "prev_climo"})
    )
    df["prev_month_val"] = prev_month.values
    df = df.merge(
        prev_month_climo.rename(columns={"prev_month": "prev_month_val"}),
        on=["city", "prev_month_val"],
        how="left"
    ).drop(columns=["prev_month_val"])

    df["rainfall_seasonal_deviation"] = df["rainfall_prev_1"] - df["prev_climo"]
    df = df.drop(columns=["prev_climo"], errors="ignore")

    return df


# ===========================================================================
# 5. TEMPERATURE ANOMALY (RAINFALL DRIVER)
# ===========================================================================

def add_temperature_anomaly_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Temperature anomalies drive evaporation and convective activity, which
    directly influence rainfall. A warmer-than-normal pre-monsoon increases
    convective instability and often brings earlier or heavier monsoon onset.
    """
    logger.info("Engineering temperature anomaly features...")

    temp_climo = (
        df.groupby(["city", "month"])["temperature_c"]
        .transform("mean")
    )
    df["temperature_climatology"] = temp_climo
    df["temperature_anomaly"] = df["temperature_c"] - temp_climo

    # Rolling temperature trend (signals warming/cooling regimes)
    df["temp_trend_3m"] = df["rolling_temp_3m"] - df["rolling_temp_6m"]

    return df


# ===========================================================================
# 6. SOIL MOISTURE, EVAPORATION & RUNOFF TRENDS
# ===========================================================================

def add_land_surface_trends(df: pd.DataFrame) -> pd.DataFrame:
    """
    Soil moisture, evaporation, and runoff are strong proxies for antecedent
    wetness conditions — a key predictor of whether rainfall will lead to
    surface runoff or be absorbed. These trend features capture the trajectory.
    """
    logger.info("Engineering land surface trend features...")

    def safe_shift_diff(group: pd.Series) -> pd.Series:
        return group.shift(1).diff()

    # Soil moisture change momentum
    df["soil_moisture_trend"] = (
        df.groupby("city")["soil_moisture"]
        .transform(safe_shift_diff)
    )

    # Evaporation trend (negative evabs = more evaporation)
    df["evabs_trend"] = (
        df.groupby("city")["evabs"]
        .transform(safe_shift_diff)
    )

    # Surface runoff trend (increased sro -> soil saturated -> more rainfall expected)
    df["sro_trend"] = (
        df.groupby("city")["sro"]
        .transform(safe_shift_diff)
    )

    # Soil moisture deviation from zone climatology (relative wetness)
    sm_zone_climo = (
        df.groupby(["climate_zone", "month"])["soil_moisture"]
        .transform("mean")
    )
    df["soil_moisture_zone_anomaly"] = df["soil_moisture"] - sm_zone_climo

    return df


# ===========================================================================
# 7. CLIMATE-ZONE-AWARE RAINFALL FEATURES
# ===========================================================================

def add_zone_relative_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rainfall of 50mm is a drought signal in the North-East, but a bonanza in
    the Thar Desert. Zone-relative anomalies normalise these differences so
    the model can reason about relative wetness, not just absolute amounts.
    """
    logger.info("Engineering climate-zone-relative rainfall features...")

    # Zone-level rainfall climatology per month
    zone_climo = (
        df.groupby(["climate_zone", "month"])["rainfall_mm"]
        .transform("mean")
    )
    df["zone_rainfall_climatology"] = zone_climo
    df["zone_rainfall_anomaly"] = df["rainfall_mm"] - zone_climo
    df["zone_rainfall_anomaly_pct"] = (
        df["zone_rainfall_anomaly"] / (zone_climo + 1e-6)
    )

    # Zone-level std for normalisation
    zone_std = (
        df.groupby(["climate_zone", "month"])["rainfall_mm"]
        .transform("std").fillna(1)
    )
    df["zone_rainfall_zscore"] = df["zone_rainfall_anomaly"] / (zone_std + 1e-6)

    return df


# ===========================================================================
# 8. ONE-HOT ENCODE CLIMATE ZONE
# ===========================================================================

def encode_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode climate_zone for ML readiness."""
    logger.info("One-hot encoding climate_zone...")
    df = pd.get_dummies(df, columns=["climate_zone"], drop_first=False)
    return df


# ===========================================================================
# 9. FINAL CLEANING & LEAKAGE AUDIT
# ===========================================================================

LEAKAGE_COLUMNS = [
    # Future values — direct leakage
    "target_temperature_next_month",
    # Risk labels are derived FROM rainfall, not from past rainfall signals
    "drought_risk",
    "heatwave_risk",
    "climate_risk_score",
]

def remove_leakage_and_clean(df: pd.DataFrame) -> Tuple[pd.DataFrame, list]:
    """
    Drop any columns that could leak future rainfall information,
    remove remaining NaNs from rolling/lag features, and return
    the final clean dataset plus the feature list.
    """
    logger.info("Performing leakage audit and final cleaning...")

    # Drop explicit leakage columns
    df = df.drop(columns=[c for c in LEAKAGE_COLUMNS if c in df.columns], errors="ignore")

    # Drop the raw date string (year/month already encoded)
    df = df.drop(columns=["date"], errors="ignore")

    # Drop city name (encoded via lat/lon + zone OHE)
    df = df.drop(columns=["city"], errors="ignore")

    # Replace any remaining inf
    df = df.replace([np.inf, -np.inf], np.nan)

    before = len(df)
    df = df.dropna()
    logger.info(f"Dropped {before - len(df)} rows with NaN after feature engineering. Final rows: {len(df)}")

    feature_cols = [c for c in df.columns if c != "target_rainfall_next_month"]
    return df, feature_cols


# ===========================================================================
# 10. FEATURE QUALITY ANALYSIS
# ===========================================================================

def analyse_feature_quality(df: pd.DataFrame, feature_cols: list, report_path: str) -> pd.DataFrame:
    """
    Compute and log:
        - Pearson correlation of each feature with target
        - Variance (near-zero variance features are useless)
        - Pairwise high-correlation pairs (multicollinearity)
    Returns a ranked correlation dataframe.
    """
    logger.info("Analysing feature quality...")

    target = df["target_rainfall_next_month"]
    feat_df = df[feature_cols]

    # Correlation with target
    corr_with_target = (
        feat_df.corrwith(target)
        .abs()
        .sort_values(ascending=False)
        .rename("abs_corr_with_target")
    )

    # Variance
    variances = feat_df.var().rename("variance")

    # Combine
    quality_df = pd.concat([corr_with_target, variances], axis=1).reset_index()
    quality_df.columns = ["Feature", "abs_corr_with_target", "variance"]
    quality_df = quality_df.sort_values("abs_corr_with_target", ascending=False)

    logger.info("\nTop 20 Feature Correlations with target_rainfall_next_month:")
    logger.info(quality_df.head(20).to_string(index=False))

    # High multicollinearity check (pairs > 0.95)
    corr_matrix = feat_df.corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    high_corr = [
        (col, row, upper.loc[row, col])
        for col in upper.columns
        for row in upper.index
        if upper.loc[row, col] > 0.95
    ]
    if high_corr:
        logger.warning(f"Found {len(high_corr)} highly correlated feature pairs (>0.95):")
        for c1, c2, v in high_corr[:10]:
            logger.warning(f"  {c1} <-> {c2}: {v:.3f}")

    return quality_df


# ===========================================================================
# 11. REPORT GENERATION
# ===========================================================================

def generate_report(
    df: pd.DataFrame,
    feature_cols: list,
    quality_df: pd.DataFrame,
    report_path: str,
) -> None:
    """Write a comprehensive Markdown feature engineering report."""
    logger.info(f"Generating report: {report_path}")

    top_features = quality_df.head(20)

    mandatory = quality_df[quality_df["abs_corr_with_target"] >= 0.3]["Feature"].tolist()
    useful = quality_df[
        (quality_df["abs_corr_with_target"] >= 0.1) &
        (quality_df["abs_corr_with_target"] < 0.3)
    ]["Feature"].tolist()
    experimental = quality_df[quality_df["abs_corr_with_target"] < 0.1]["Feature"].tolist()

    report = f"""# Rainfall Feature Engineering Report

## Pipeline Summary
- **Total Records**: {len(df):,}
- **Total Features Engineered**: {len(feature_cols)}
- **Target Variable**: `target_rainfall_next_month`
- **Leakage Prevention**: Future labels (`drought_risk`, `target_temperature_next_month`) removed.

---

## Feature Classification

### Mandatory Features (Correlation ≥ 0.30 with target)
{chr(10).join(f"- `{f}`" for f in mandatory)}

### Useful Features (0.10 ≤ Correlation < 0.30)
{chr(10).join(f"- `{f}`" for f in useful[:30])}

### Experimental Features (Correlation < 0.10)
{chr(10).join(f"- `{f}`" for f in experimental[:20])}

---

## Top 20 Features by Correlation with Next-Month Rainfall

| Rank | Feature | |Correlation| |
|------|---------|------------|
{chr(10).join(f"| {i+1} | {row['Feature']} | {row['abs_corr_with_target']:.4f} |" for i, row in top_features.iterrows())}

---

## Feature Explanations

### Monsoon Intelligence
| Feature | Why It Helps | Risk |
|---------|-------------|------|
| `is_monsoon` | Captures the JJAS window responsible for ~80% of annual rainfall | None |
| `monsoon_phase` | Encodes intra-monsoon progression (onset vs peak vs withdrawal) | Ordinal encoding may overweight linear relationship |
| `monsoon_phase_sin/cos` | Cyclic encoding preserves continuity across phase boundaries | None |
| `pre_monsoon` | Heat buildup in MAM drives convective instability for onset | None |
| `post_monsoon` | NE monsoon active over S. India Oct-Nov; captures different mechanism | None |

### Rainfall Anomaly & Variability
| Feature | Why It Helps | Risk |
|---------|-------------|------|
| `rainfall_anomaly` | Deviations from climatology persist month to month (autocorrelation) | Climatology uses full dataset mean — assume stationarity |
| `rainfall_anomaly_pct` | Normalised deviation more comparable across arid vs humid zones | Division near zero needs clipping |
| `rolling_rainfall_std_3m` | High variability precedes uncertain/extreme rainfall | Requires ≥2 months of history |
| `rolling_rainfall_cv_3m` | Coefficient of variation normalises std by mean | Unstable when mean ≈ 0 |
| `dry_months_streak` | Consecutive dry months predict drought conditions | Threshold (5mm) is heuristic |
| `wet_months_streak` | Consecutive wet months predict monsoon persistence | Threshold (50mm) is heuristic |

### Rainfall Momentum & Trend
| Feature | Why It Helps | Risk |
|---------|-------------|------|
| `rainfall_trend` | Direction of change (increasing/decreasing) from lag-3 to lag-1 | May alias with lag features |
| `rainfall_acceleration` | Rate of change in the trend — catching surges or collapses | Second-order differences are noisy |
| `rainfall_growth_rate` | Percentage change captures magnitude of trend | Clips needed when denominator ≈ 0 |
| `rainfall_momentum` | Lag-1 deviation from climatology | Correlated with `rainfall_anomaly` |
| `rainfall_seasonal_deviation` | Lag-1 vs same-month historical average — anomaly signal | Requires joining prev-month climatology |

### Temperature Anomaly
| Feature | Why It Helps | Risk |
|---------|-------------|------|
| `temperature_anomaly` | Warm anomaly → enhanced evaporation → higher monsoon rainfall potential | Indirect relationship; weak outside monsoon season |
| `temp_trend_3m` | Warming/cooling trajectory drives convection strength | Noise outside monsoon months |

### Land Surface
| Feature | Why It Helps | Risk |
|---------|-------------|------|
| `soil_moisture_trend` | Rising moisture → soil saturation → next-month runoff/flooding | Lag introduces 1-month delay correctly |
| `sro_trend` | Increasing runoff signals peak saturation state | Highly correlated with `soil_moisture_trend` |
| `soil_moisture_zone_anomaly` | How wet a city is relative to its climate zone peers | Uses full-dataset groupby (static, not future) |

### Zone-Relative Features
| Feature | Why It Helps | Risk |
|---------|-------------|------|
| `zone_rainfall_anomaly` | 50mm in Thar Desert is extreme; 50mm in NE is dry. Zone context is critical | Groupby is static — safe |
| `zone_rainfall_zscore` | Standardised anomaly, dimensionless — comparable across all zones | Assumes zone std is stable |

---

## Leakage Prevention Summary

The following columns were **deliberately excluded** to prevent data leakage:

| Column | Reason |
|--------|--------|
| `target_temperature_next_month` | Future temperature (cannot know at prediction time) |
| `drought_risk` | Derived post-hoc from rainfall patterns — circular dependency |
| `heatwave_risk` | Derived post-hoc from temperature labels |
| `climate_risk_score` | Composite of multiple derived labels |
| `date` | Encoded as `year`, `month`, `month_sin/cos` |
| `city` | Encoded via `latitude`, `longitude`, and OHE climate zones |

---

## Recommendations for Model Training

1. Use **time-based split**: Train on ≤ 2022, test on > 2022.
2. Consider `log1p` transformation of `target_rainfall_next_month` — rainfall is right-skewed.
3. Monitor feature importance at training time to confirm experimental features add value.
4. Evaluate `zone_rainfall_zscore` as an alternate to raw `rainfall_mm` for generalisation.
"""

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info("Report saved.")


# ===========================================================================
# 12. SUMMARY PRINT
# ===========================================================================

def print_dataset_summary(df: pd.DataFrame, feature_cols: list) -> None:
    """Print final dataset summary to stdout."""
    print("\n" + "=" * 60)
    print("  RAINFALL FEATURE ENGINEERING — DATASET SUMMARY")
    print("=" * 60)
    print(f"  Total Rows    : {len(df):,}")
    print(f"  Total Features: {len(feature_cols)}")
    print(f"  Target        : target_rainfall_next_month\n")

    print("  Feature List:")
    for i, col in enumerate(feature_cols, 1):
        print(f"    {i:>3}. {col}")

    print(f"\n  Missing Values Summary:")
    mv = df.isnull().sum()
    mv = mv[mv > 0]
    if len(mv) == 0:
        print("    None — dataset is clean.")
    else:
        print(mv.to_string())

    print(f"\n  Feature Statistics (key variables):")
    key = ["rainfall_mm", "rainfall_anomaly", "rainfall_trend",
           "rolling_rainfall_std_3m", "zone_rainfall_zscore", "target_rainfall_next_month"]
    key = [c for c in key if c in df.columns]
    print(df[key].describe().round(3).to_string())
    print("=" * 60 + "\n")


# ===========================================================================
# MAIN PIPELINE
# ===========================================================================

def run_pipeline() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, "..", "data", "processed", "climate_master.csv")
    output_path = os.path.join(script_dir, "..", "data", "processed", "rainfall_training_dataset.csv")
    report_path = os.path.join(script_dir, "..", "reports", "rainfall_feature_engineering_report.md")

    # Step 1 — Load & validate
    df = load_and_validate(data_path)

    # Step 2 — Monsoon intelligence
    df = add_monsoon_features(df)

    # Step 3 — Rainfall anomaly & variability
    df = add_rainfall_anomaly_features(df)

    # Step 4 — Momentum & trend
    df = add_rainfall_momentum_features(df)

    # Step 5 — Temperature anomaly
    df = add_temperature_anomaly_features(df)

    # Step 6 — Land surface trends
    df = add_land_surface_trends(df)

    # Step 7 — Zone-relative features
    df = add_zone_relative_features(df)

    # Step 8 — Encode categoricals
    df = encode_categoricals(df)

    # Step 9 — Leakage audit & final clean
    df, feature_cols = remove_leakage_and_clean(df)

    # Step 10 — Feature quality analysis
    quality_df = analyse_feature_quality(df, feature_cols, report_path)

    # Step 11 — Print summary
    print_dataset_summary(df, feature_cols)

    # Step 12 — Save output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info(f"Rainfall training dataset saved to: {output_path}")

    # Step 13 — Generate report
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    generate_report(df, feature_cols, quality_df, report_path)

    logger.info("Pipeline complete.")


if __name__ == "__main__":
    run_pipeline()
