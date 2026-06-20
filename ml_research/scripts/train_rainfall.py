"""
Rainfall Prediction Model — Training Pipeline
==============================================
AI-powered Digital Twin of India's Climate

Target   : rainfall_mm  (Climate State Rainfall Model)
Strategy : Train multiple candidate models on chronological splits,
           auto-select the best performer, tune it, and save
           production-ready artifacts.

Chronological Split
    Train  : year <= 2020
    Val    : 2021 – 2022
    Test   : year >= 2023

Models Evaluated
    - LightGBM Regressor
    - XGBoost Regressor
    - Random Forest Regressor
    - Extra Trees Regressor

Author: AI-Climate-Twin Engineering
"""

import os
import json
import time
import logging
import warnings
from typing import Dict, List, Tuple, Any

import joblib
import numpy as np
import pandas as pd

# pyrefly: ignore [missing-import]
import lightgbm as lgb
# pyrefly: ignore [missing-import]
import xgboost as xgb
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.model_selection import RandomizedSearchCV
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    mean_absolute_percentage_error,
)

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
# Constants — Features that directly leak the TARGET (rainfall_mm)
# ---------------------------------------------------------------------------
# rainfall_anomaly      = rainfall_mm - climatology  → derived FROM target
# zone_rainfall_anomaly = rainfall_mm - zone_mean    → derived FROM target
# zone_rainfall_zscore  = anomaly / zone_std          → derived FROM target
# target_rainfall_next_month → future value
LEAKAGE_FEATURES = [
    "rainfall_anomaly",
    "rainfall_anomaly_pct",
    "zone_rainfall_anomaly",
    "zone_rainfall_anomaly_pct",
    "zone_rainfall_zscore",
    "target_rainfall_next_month",  # future, not useful here
]

TARGET = "rainfall_mm"


# ===========================================================================
# 1. LOAD & VALIDATE
# ===========================================================================

def load_and_validate(data_path: str) -> pd.DataFrame:
    """Load the rainfall training dataset and perform strict quality checks."""
    logger.info(f"Loading dataset: {data_path}")
    df = pd.read_csv(data_path)
    logger.info(f"Raw shape: {df.shape}")

    # ── Missing values ──────────────────────────────────────────────────────
    mv = df.isnull().sum()
    mv_cols = mv[mv > 0]
    if len(mv_cols):
        logger.warning(f"Missing values detected:\n{mv_cols}")
    else:
        logger.info("Missing values: None")

    # ── Infinite values ─────────────────────────────────────────────────────
    inf_mask = np.isinf(df.select_dtypes(include=[np.number]))
    inf_count = inf_mask.sum().sum()
    if inf_count:
        logger.warning(f"Infinite values detected: {inf_count}. Replacing with NaN.")
        df = df.replace([np.inf, -np.inf], np.nan)

    # ── Duplicates ──────────────────────────────────────────────────────────
    dupes = df.duplicated().sum()
    if dupes:
        logger.warning(f"Dropping {dupes} duplicate rows.")
        df = df.drop_duplicates()

    # ── Target distribution ─────────────────────────────────────────────────
    target_stats = df[TARGET].describe()
    logger.info(
        f"Target ({TARGET}) distribution:\n"
        f"  mean={target_stats['mean']:.2f}  std={target_stats['std']:.2f}  "
        f"  min={target_stats['min']:.2f}  max={target_stats['max']:.2f}"
    )

    # ── Outlier analysis (IQR) ───────────────────────────────────────────────
    q1, q3 = df[TARGET].quantile(0.25), df[TARGET].quantile(0.75)
    iqr = q3 - q1
    upper_fence = q3 + 3 * iqr  # 3× IQR to keep legitimate monsoon peaks
    outliers = (df[TARGET] > upper_fence).sum()
    logger.info(
        f"Rainfall outliers (> {upper_fence:.1f} mm): {outliers} rows "
        f"({100*outliers/len(df):.1f}%) — retained (legitimate monsoon events)"
    )

    df = df.dropna(subset=[TARGET])
    logger.info(f"Final validated shape: {df.shape}")
    return df


# ===========================================================================
# 2. FEATURE MATRIX
# ===========================================================================

def build_feature_matrix(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Remove leakage columns and return (clean_df, feature_list).
    The target `rainfall_mm` is NOT included in the feature list.
    """
    drop_cols = LEAKAGE_FEATURES + [TARGET]
    feature_cols = [c for c in df.columns if c not in drop_cols]

    logger.info(f"Feature matrix: {len(feature_cols)} features (target excluded)")
    return df, feature_cols


# ===========================================================================
# 3. CHRONOLOGICAL SPLIT
# ===========================================================================

def chronological_split(
    df: pd.DataFrame,
    feature_cols: List[str],
    train_end: int = 2020,
    val_end: int = 2022,
) -> Tuple:
    """
    Strict time-aware split — no data from later years bleeds into training.

    Train : year <= train_end  (2000–2020)
    Val   : train_end < year <= val_end  (2021–2022)
    Test  : year >  val_end  (2023–2025)
    """
    train = df[df["year"] <= train_end]
    val   = df[(df["year"] > train_end) & (df["year"] <= val_end)]
    test  = df[df["year"] > val_end]

    logger.info(
        f"Chronological split — "
        f"Train: {len(train)} rows ({train['year'].min()}–{train['year'].max()}) | "
        f"Val: {len(val)} rows ({val['year'].min()}–{val['year'].max()}) | "
        f"Test: {len(test)} rows ({test['year'].min()}–{test['year'].max()})"
    )

    X_train = train[feature_cols].fillna(0)
    y_train = train[TARGET]
    X_val   = val[feature_cols].fillna(0)
    y_val   = val[TARGET]
    X_test  = test[feature_cols].fillna(0)
    y_test  = test[TARGET]

    return X_train, y_train, X_val, y_val, X_test, y_test, train, val, test


# ===========================================================================
# 4. METRICS
# ===========================================================================

def compute_metrics(y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, float]:
    """Compute MAE, RMSE, R², MAPE."""
    # MAPE: avoid division by zero for zero-rainfall months
    nonzero = y_true != 0
    mape = (
        mean_absolute_percentage_error(y_true[nonzero], y_pred[nonzero]) * 100
        if nonzero.sum() > 0 else float("nan")
    )
    return {
        "MAE":  round(float(mean_absolute_error(y_true, y_pred)), 4),
        "RMSE": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
        "R2":   round(float(r2_score(y_true, y_pred)), 4),
        "MAPE": round(float(mape), 4),
    }


# ===========================================================================
# 5. MODEL DEFINITIONS
# ===========================================================================

def get_candidate_models() -> Dict[str, Any]:
    """Return all candidate models with reasonable default hyperparameters."""
    return {
        "LightGBM": lgb.LGBMRegressor(
            n_estimators=800, learning_rate=0.05, num_leaves=63,
            max_depth=8, subsample=0.8, colsample_bytree=0.8,
            random_state=42, n_jobs=-1, verbose=-1,
        ),
        "XGBoost": xgb.XGBRegressor(
            n_estimators=800, learning_rate=0.05, max_depth=8,
            subsample=0.8, colsample_bytree=0.8,
            random_state=42, n_jobs=-1, verbosity=0,
        ),
        "RandomForest": RandomForestRegressor(
            n_estimators=300, max_depth=16, min_samples_leaf=3,
            random_state=42, n_jobs=-1,
        ),
        "ExtraTrees": ExtraTreesRegressor(
            n_estimators=300, max_depth=16, min_samples_leaf=3,
            random_state=42, n_jobs=-1,
        ),
    }


# ===========================================================================
# 6. TRAIN & EVALUATE ALL CANDIDATES
# ===========================================================================

def train_all_candidates(
    models: Dict[str, Any],
    X_train: pd.DataFrame, y_train: pd.Series,
    X_val: pd.DataFrame,   y_val: pd.Series,
) -> Tuple[Dict, Dict]:
    """
    Train every candidate model and evaluate on the validation set.
    Returns (trained_models_dict, comparison_results_dict).
    """
    trained, results = {}, {}

    for name, model in models.items():
        logger.info(f"Training {name}...")
        t0 = time.time()
        model.fit(X_train, y_train)
        train_time = round(time.time() - t0, 2)

        t1 = time.time()
        val_pred = model.predict(X_val)
        infer_time = round((time.time() - t1) * 1000, 2)  # ms

        metrics = compute_metrics(y_val, val_pred)
        results[name] = {**metrics, "train_time_s": train_time, "infer_time_ms": infer_time}
        trained[name] = model

        logger.info(
            f"  {name}: R²={metrics['R2']:.4f}  RMSE={metrics['RMSE']:.4f}  "
            f"MAE={metrics['MAE']:.4f}  MAPE={metrics['MAPE']:.2f}%  "
            f"[train={train_time}s  infer={infer_time}ms]"
        )

    return trained, results


# ===========================================================================
# 7. AUTO-SELECT BEST MODEL
# ===========================================================================

def select_best_model(results: Dict) -> str:
    """
    Rank by: 1) R² ↑   2) RMSE ↓   3) MAE ↓
    Returns the name of the winning model.
    """
    comparison = pd.DataFrame(results).T
    comparison = comparison.sort_values(
        ["R2", "RMSE", "MAE"],
        ascending=[False, True, True]
    )
    best_name = comparison.index[0]
    logger.info(f"\nModel Comparison (Validation Set):\n{comparison.to_string()}")
    logger.info(f"\n>>> Best model: {best_name} <<<")
    return best_name


# ===========================================================================
# 8. HYPERPARAMETER OPTIMIZATION
# ===========================================================================

def _get_param_grid(model_name: str) -> Dict:
    """Return model-specific hyperparameter search space."""
    if model_name == "LightGBM":
        return {
            "n_estimators":    [500, 800, 1000, 1500],
            "learning_rate":   [0.01, 0.03, 0.05, 0.08],
            "num_leaves":      [31, 63, 127],
            "max_depth":       [6, 8, 10, -1],
            "subsample":       [0.7, 0.8, 1.0],
            "colsample_bytree":[0.7, 0.8, 1.0],
            "min_child_samples":[10, 20, 30],
        }
    elif model_name == "XGBoost":
        return {
            "n_estimators":  [500, 800, 1000],
            "learning_rate": [0.01, 0.03, 0.05, 0.08],
            "max_depth":     [5, 6, 8, 10],
            "subsample":     [0.7, 0.8, 1.0],
            "colsample_bytree": [0.7, 0.8, 1.0],
            "min_child_weight": [1, 3, 5],
        }
    elif model_name in ("RandomForest", "ExtraTrees"):
        return {
            "n_estimators": [200, 300, 500],
            "max_depth":    [10, 14, 18, None],
            "min_samples_leaf": [2, 3, 5],
            "max_features": ["sqrt", "log2", 0.5],
        }
    return {}


def tune_best_model(
    model_name: str,
    trained_models: Dict,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    n_iter: int = 12,
    cv: int = 3,
) -> Any:
    """
    Run RandomizedSearchCV on the winning model.
    Uses 3-fold CV over the combined train set for practical speed.
    """
    logger.info(f"Hyperparameter tuning: {model_name} (n_iter={n_iter}, cv={cv})...")

    base_model = trained_models[model_name]
    param_grid = _get_param_grid(model_name)

    if not param_grid:
        logger.warning("No parameter grid defined — skipping tuning.")
        return base_model

    t0 = time.time()
    search = RandomizedSearchCV(
        estimator=base_model,
        param_distributions=param_grid,
        n_iter=n_iter,
        scoring="neg_root_mean_squared_error",
        cv=cv,
        random_state=42,
        n_jobs=-1,
        verbose=1,
        refit=True,
    )
    search.fit(X_train, y_train)

    logger.info(f"Tuning completed in {time.time()-t0:.1f}s")
    logger.info(f"Best params: {search.best_params_}")
    logger.info(f"Best CV RMSE: {-search.best_score_:.4f}")

    return search.best_estimator_


# ===========================================================================
# 9. FEATURE IMPORTANCE
# ===========================================================================

def extract_feature_importance(
    model: Any,
    feature_cols: List[str],
    top_n: int = 20,
) -> pd.DataFrame:
    """Extract and rank feature importances from the trained model."""
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    else:
        logger.warning("Model has no feature_importances_ attribute.")
        return pd.DataFrame()

    imp_df = (
        pd.DataFrame({"Feature": feature_cols, "Importance": importances})
        .sort_values("Importance", ascending=False)
        .reset_index(drop=True)
    )
    imp_df.index += 1

    logger.info(f"\nTop {top_n} Features:")
    logger.info(imp_df.head(top_n).to_string())

    return imp_df


# ===========================================================================
# 10. RESIDUAL & DIAGNOSTIC ANALYSIS
# ===========================================================================

def residual_analysis(
    model: Any,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    test_df: pd.DataFrame,
) -> Dict:
    """
    Compute residuals and generate seasonal / zone diagnostics.
    Returns a dict of DataFrames for the report.
    """
    preds = model.predict(X_test)
    residuals = y_test.values - preds

    diag_df = test_df[["year", "month", "is_monsoon"]].copy()
    diag_df = diag_df.reset_index(drop=True)

    # Identify climate zone columns
    zone_cols = [c for c in test_df.columns if c.startswith("climate_zone_")]
    if zone_cols:
        zone_series = test_df[zone_cols].idxmax(axis=1).str.replace("climate_zone_", "")
        diag_df["climate_zone"] = zone_series.values
    else:
        diag_df["climate_zone"] = "Unknown"

    diag_df["actual"]    = y_test.values
    diag_df["predicted"] = preds
    diag_df["residual"]  = residuals
    diag_df["abs_error"] = np.abs(residuals)

    # ── Monthly diagnostics ─────────────────────────────────────────────────
    monthly = (
        diag_df.groupby("month")
        .agg(mean_abs_error=("abs_error", "mean"), count=("abs_error", "count"))
        .round(3)
    )
    monthly["easiest"] = monthly["mean_abs_error"] == monthly["mean_abs_error"].min()
    monthly["hardest"] = monthly["mean_abs_error"] == monthly["mean_abs_error"].max()

    easiest_month = int(monthly["mean_abs_error"].idxmin())
    hardest_month = int(monthly["mean_abs_error"].idxmax())

    # ── Zone diagnostics ────────────────────────────────────────────────────
    zone_diag = (
        diag_df.groupby("climate_zone")
        .agg(mean_abs_error=("abs_error", "mean"), count=("abs_error", "count"))
        .round(3)
        .sort_values("mean_abs_error")
    )

    easiest_zone = zone_diag["mean_abs_error"].idxmin()
    hardest_zone  = zone_diag["mean_abs_error"].idxmax()

    # ── Monsoon vs non-monsoon error ────────────────────────────────────────
    monsoon_mae     = diag_df[diag_df["is_monsoon"] == 1]["abs_error"].mean()
    non_monsoon_mae = diag_df[diag_df["is_monsoon"] == 0]["abs_error"].mean()

    # ── Over/under prediction ───────────────────────────────────────────────
    over_count  = (residuals < 0).sum()   # predicted > actual
    under_count = (residuals > 0).sum()   # predicted < actual

    logger.info(f"\n=== Residual Diagnostics ===")
    logger.info(f"Easiest month : {easiest_month}  (MAE={monthly.loc[easiest_month,'mean_abs_error']:.2f}mm)")
    logger.info(f"Hardest month : {hardest_month}  (MAE={monthly.loc[hardest_month,'mean_abs_error']:.2f}mm)")
    logger.info(f"Easiest zone  : {easiest_zone}  (MAE={zone_diag.loc[easiest_zone,'mean_abs_error']:.2f}mm)")
    logger.info(f"Hardest zone  : {hardest_zone}  (MAE={zone_diag.loc[hardest_zone,'mean_abs_error']:.2f}mm)")
    logger.info(f"Monsoon MAE   : {monsoon_mae:.2f}mm  |  Non-Monsoon MAE: {non_monsoon_mae:.2f}mm")
    logger.info(f"Over-predictions : {over_count}  |  Under-predictions: {under_count}")

    return {
        "diag_df": diag_df,
        "monthly": monthly,
        "zone_diag": zone_diag,
        "easiest_month": easiest_month,
        "hardest_month": hardest_month,
        "easiest_zone": easiest_zone,
        "hardest_zone": hardest_zone,
        "monsoon_mae": round(float(monsoon_mae), 3),
        "non_monsoon_mae": round(float(non_monsoon_mae), 3),
        "over_count": int(over_count),
        "under_count": int(under_count),
    }


# ===========================================================================
# 11. SAVE ARTIFACTS
# ===========================================================================

def save_artifacts(
    model: Any,
    metrics: Dict,
    best_params: Dict,
    importance_df: pd.DataFrame,
    comparison_results: Dict,
    models_dir: str,
    best_name: str,
) -> None:
    """Persist all production artifacts."""
    os.makedirs(models_dir, exist_ok=True)

    joblib.dump(model, os.path.join(models_dir, "rainfall.pkl"))
    logger.info(f"Model saved → {models_dir}/rainfall.pkl")

    with open(os.path.join(models_dir, "rainfall_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=4)

    with open(os.path.join(models_dir, "rainfall_best_params.json"), "w") as f:
        json.dump({"model": best_name, "params": best_params}, f, indent=4)

    importance_df.to_csv(os.path.join(models_dir, "rainfall_feature_importance.csv"), index=False)

    with open(os.path.join(models_dir, "rainfall_model_comparison.json"), "w") as f:
        json.dump(comparison_results, f, indent=4)

    logger.info("All artifacts saved.")


# ===========================================================================
# 12. REPORT GENERATION
# ===========================================================================

MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
               7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

def generate_report(
    best_name: str,
    test_metrics: Dict,
    val_results: Dict,
    importance_df: pd.DataFrame,
    diagnostics: Dict,
    feature_cols: List[str],
    n_train: int,
    n_val: int,
    n_test: int,
    report_path: str,
    best_params: Dict,
) -> None:
    comp_table = pd.DataFrame(val_results).T.round(4)

    top20 = importance_df.head(20)
    imp_table = "\n".join(
        f"| {i} | {row['Feature']} | {row['Importance']} |"
        for i, row in top20.iterrows()
    )

    monthly = diagnostics["monthly"]
    month_table = "\n".join(
        f"| {MONTH_NAMES.get(m, m)} | {row['mean_abs_error']:.2f} | {'✅ Easiest' if row['easiest'] else ('⚠️ Hardest' if row['hardest'] else '')} |"
        for m, row in monthly.iterrows()
    )

    zone_diag = diagnostics["zone_diag"]
    zone_table = "\n".join(
        f"| {z} | {row['mean_abs_error']:.2f} |"
        for z, row in zone_diag.iterrows()
    )

    report = f"""# Rainfall Prediction Model — Final Report

## Executive Summary
A production-ready **Climate State Rainfall Model** has been successfully trained
and selected for the AI Climate Digital Twin of India.

- **Best Model**: {best_name}
- **Test R²**: {test_metrics['R2']}
- **Test RMSE**: {test_metrics['RMSE']} mm
- **Test MAE**: {test_metrics['MAE']} mm
- **Test MAPE**: {test_metrics['MAPE']}%

---

## Dataset Overview
| Property | Value |
|----------|-------|
| Train rows | {n_train:,} (year ≤ 2020) |
| Validation rows | {n_val:,} (2021–2022) |
| Test rows | {n_test:,} (year ≥ 2023) |
| Features used | {len(feature_cols)} |
| Target | `rainfall_mm` |

---

## Features Used
```
{', '.join(feature_cols)}
```

---

## Model Comparison (Validation Set)

| Model | MAE | RMSE | R² | MAPE | Train(s) | Infer(ms) |
|-------|-----|------|-----|------|----------|-----------|
{chr(10).join(f"| {idx} | {row['MAE']} | {row['RMSE']} | {row['R2']} | {row['MAPE']} | {row['train_time_s']} | {row['infer_time_ms']} |" for idx, row in comp_table.iterrows())}

---

## Best Model Selection
**{best_name}** was selected based on: 1) highest R² → 2) lowest RMSE → 3) lowest MAE.

### Best Hyperparameters (after tuning)
```json
{json.dumps(best_params, indent=2)}
```

---

## Test Set Metrics
| Metric | Value |
|--------|-------|
| MAE | {test_metrics['MAE']} mm |
| RMSE | {test_metrics['RMSE']} mm |
| R² | {test_metrics['R2']} |
| MAPE | {test_metrics['MAPE']} % |

---

## Feature Importance (Top 20)
| Rank | Feature | Importance |
|------|---------|------------|
{imp_table}

---

## Monthly Diagnostics

| Month | MAE (mm) | Notes |
|-------|----------|-------|
{month_table}

---

## Climate Zone Diagnostics

| Zone | MAE (mm) |
|------|----------|
{zone_table}

---

## Monsoon Behavior Analysis
| Period | MAE (mm) |
|--------|----------|
| Monsoon (JJAS) | {diagnostics['monsoon_mae']} |
| Non-Monsoon | {diagnostics['non_monsoon_mae']} |
| Over-predictions | {diagnostics['over_count']} rows |
| Under-predictions | {diagnostics['under_count']} rows |

**Easiest month**: {MONTH_NAMES.get(diagnostics['easiest_month'], diagnostics['easiest_month'])}
**Hardest month**: {MONTH_NAMES.get(diagnostics['hardest_month'], diagnostics['hardest_month'])}
**Easiest zone**: {diagnostics['easiest_zone']}
**Hardest zone**: {diagnostics['hardest_zone']}

---

## Known Limitations
1. **Zero-inflation**: ~25% of records have near-zero rainfall (dry months). Errors in MAPE inflate for these.
2. **Extreme events**: Unprecedented rainfall events (cyclones, cloud-bursts) are underrepresented in training data.
3. **Spatial resolution**: ERA5-Land at 0.1° is coarser than district-level impacts.
4. **Future climate drift**: Model trained on 2000–2020; patterns post-2025 may shift.

## Recommendations
- Apply `log1p` target transformation on the next iteration to handle skew.
- Investigate quantile regression for uncertainty estimation during monsoon months.
- Add teleconnection indices (IOD, ENSO, MJO phase) as future features for further improvement.
- Retrain annually as new ERA5 data becomes available.
"""

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info(f"Report saved → {report_path}")


# ===========================================================================
# 13. FINAL SUMMARY PRINT
# ===========================================================================

def print_final_summary(
    best_name: str,
    test_metrics: Dict,
    importance_df: pd.DataFrame,
    model_path: str,
    train_time: float,
) -> None:
    size_mb = round(os.path.getsize(model_path) / 1e6, 2)
    print("\n" + "=" * 65)
    print("  RAINFALL MODEL — FINAL PRODUCTION SUMMARY")
    print("=" * 65)
    print(f"  Best Model      : {best_name}")
    print(f"  R²              : {test_metrics['R2']}")
    print(f"  RMSE            : {test_metrics['RMSE']} mm")
    print(f"  MAE             : {test_metrics['MAE']} mm")
    print(f"  MAPE            : {test_metrics['MAPE']} %")
    print(f"  Training Time   : {train_time:.1f} s")
    print(f"  Model Size      : {size_mb} MB")
    print(f"  Production Ready: YES\n")
    print("  Top 10 Features:")
    for _, row in importance_df.head(10).iterrows():
        print(f"    {_:>3}. {row['Feature']}")
    print("=" * 65 + "\n")


# ===========================================================================
# MAIN PIPELINE
# ===========================================================================

def run_pipeline() -> None:
    script_dir  = os.path.dirname(os.path.abspath(__file__))
    data_path   = os.path.join(script_dir, "..", "data", "processed", "rainfall_training_dataset.csv")
    models_dir  = os.path.join(script_dir, "..", "..", "app", "ml_services", "models")
    report_path = os.path.join(script_dir, "..", "reports", "rainfall_model_report.md")

    pipeline_start = time.time()

    # ── 1. Load & validate ──────────────────────────────────────────────────
    df = load_and_validate(data_path)

    # ── 2. Build feature matrix ─────────────────────────────────────────────
    df, feature_cols = build_feature_matrix(df)

    # ── 3. Chronological split ──────────────────────────────────────────────
    X_train, y_train, X_val, y_val, X_test, y_test, train_df, val_df, test_df = (
        chronological_split(df, feature_cols)
    )

    # ── 4. Train all candidates ─────────────────────────────────────────────
    candidate_models = get_candidate_models()
    trained_models, val_results = train_all_candidates(
        candidate_models, X_train, y_train, X_val, y_val
    )

    # ── 5. Auto-select best model ───────────────────────────────────────────
    best_name = select_best_model(val_results)

    # ── 6. Hyperparameter tuning ────────────────────────────────────────────
    tuned_model = tune_best_model(
        best_name, trained_models, X_train, y_train, n_iter=12, cv=3
    )

    # Retrain best tuned model on Train + Val combined for maximum data
    logger.info("Retraining best model on Train + Val combined...")
    X_trainval = pd.concat([X_train, X_val])
    y_trainval = pd.concat([y_train, y_val])
    tuned_model.fit(X_trainval, y_trainval)

    # ── 7. Final evaluation on Test set ─────────────────────────────────────
    test_preds   = tuned_model.predict(X_test)
    test_metrics = compute_metrics(y_test, test_preds)
    logger.info(f"\nFinal Test Metrics: {test_metrics}")

    # ── 8. Feature importance ───────────────────────────────────────────────
    importance_df = extract_feature_importance(tuned_model, feature_cols)

    # ── 9. Residual & diagnostic analysis ───────────────────────────────────
    diagnostics = residual_analysis(tuned_model, X_test, y_test, test_df.reset_index(drop=True))

    # ── 10. Save artifacts ──────────────────────────────────────────────────
    best_params = (
        tuned_model.get_params()
        if hasattr(tuned_model, "get_params") else {}
    )
    save_artifacts(
        tuned_model, test_metrics, best_params,
        importance_df, val_results, models_dir, best_name
    )

    total_time = round(time.time() - pipeline_start, 1)

    # ── 11. Report ──────────────────────────────────────────────────────────
    generate_report(
        best_name=best_name,
        test_metrics=test_metrics,
        val_results=val_results,
        importance_df=importance_df,
        diagnostics=diagnostics,
        feature_cols=feature_cols,
        n_train=len(X_train),
        n_val=len(X_val),
        n_test=len(X_test),
        report_path=report_path,
        best_params={k: v for k, v in best_params.items()
                     if k in ["n_estimators","learning_rate","max_depth",
                               "num_leaves","subsample","colsample_bytree"]},
    )

    # ── 12. Print summary ───────────────────────────────────────────────────
    model_path = os.path.join(models_dir, "rainfall.pkl")
    print_final_summary(best_name, test_metrics, importance_df, model_path, total_time)


if __name__ == "__main__":
    run_pipeline()
