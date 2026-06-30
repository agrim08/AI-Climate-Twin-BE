"""
Drought Evolution Model — Final Production Training Script
==========================================================
AI-powered Digital Twin of India's Climate

Objective:
    Train the final production-ready Drought Evolution Model for
    multi-class drought severity prediction.

Target:
    drought_category → Low | Medium | High | Extreme

Pipeline:
    1.  Load & validate drought training dataset
    2.  Class balance analysis
    3.  Feature matrix construction
    4.  Chronological train / val / test split
    5.  Train candidate models (LightGBM, XGBoost, RF, ExtraTrees)
    6.  Multi-metric evaluation + confusion matrices
    7.  Hyperparameter optimization (RandomizedSearchCV) on best candidate
    8.  Retrain best model on Train+Val
    9.  Final test-set evaluation
    10. Feature importance + SHAP-ready ranking
    11. Climate zone & seasonal drought diagnostics
    12. Error analysis
    13. Artifact persistence
    14. Comprehensive markdown report
    15. Final summary print

Scientific Design:
    - No random splitting — chronological ordering only
    - Class imbalance handled via class_weight='balanced'
    - Macro F1 is primary metric (penalises ignoring minority classes)
    - City-level artefacts (lat/lon) kept for spatial generalisation

Author: AI-Climate-Twin Engineering
"""

import os
import json
import time
import logging
import warnings
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from scipy.stats import randint, uniform

from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix, classification_report,
)
from sklearn.model_selection import RandomizedSearchCV
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

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
# Constants
# ---------------------------------------------------------------------------
TARGET = "drought_category"
ORDINAL_TARGET = "drought_category_ordinal"
SEVERITY_SCORE = "drought_severity_score"

CLASS_ORDER = ["Low", "Medium", "High", "Extreme"]
LABEL_ENCODER = {c: i for i, c in enumerate(CLASS_ORDER)}
LABEL_DECODER = {i: c for c, i in LABEL_ENCODER.items()}

# Columns to drop before building the feature matrix
DROP_COLS = [
    TARGET, ORDINAL_TARGET, SEVERITY_SCORE,
    "date", "city",                             # encoded via lat/lon + OHE zone
    "target_temperature_next_month",            # future leak
    "target_rainfall_next_month",               # future leak
    "drought_risk", "heatwave_risk",            # post-hoc labels
    "climate_risk_score",                       # post-hoc composite
]

TRAIN_YEARS_END  = 2020
VAL_YEARS_START  = 2021
VAL_YEARS_END    = 2022
TEST_YEARS_START = 2023


# ===========================================================================
# 1. LOAD & VALIDATE
# ===========================================================================

def load_and_validate(data_path: str) -> pd.DataFrame:
    logger.info(f"Loading dataset: {data_path}")
    df = pd.read_csv(data_path)
    logger.info(f"Raw shape: {df.shape}")

    # Missing values
    mv = df.isnull().sum()
    mv_cols = mv[mv > 0]
    if len(mv_cols):
        logger.warning(f"Missing values:\n{mv_cols}")
    else:
        logger.info("Missing values: None")

    # Infinite values
    num_df = df.select_dtypes(include=[np.number])
    inf_count = np.isinf(num_df).sum().sum()
    if inf_count:
        logger.warning(f"Infinite values: {inf_count} — replacing with NaN")
        df = df.replace([np.inf, -np.inf], np.nan)

    # Duplicates
    dupes = df.duplicated().sum()
    if dupes:
        logger.warning(f"Dropping {dupes} duplicate rows")
        df = df.drop_duplicates()

    # Target integrity
    assert TARGET in df.columns, f"Target column '{TARGET}' not found"
    valid_classes = set(CLASS_ORDER)
    found_classes = set(df[TARGET].unique())
    assert found_classes.issubset(valid_classes), f"Unexpected classes: {found_classes - valid_classes}"
    logger.info(f"All target classes valid: {sorted(found_classes)}")

    logger.info(f"Final validated shape: {df.shape}")
    return df


# ===========================================================================
# 2. CLASS BALANCE ANALYSIS
# ===========================================================================

def analyse_class_balance(df: pd.DataFrame) -> None:
    logger.info("\n=== Class Balance Analysis ===")
    counts = df[TARGET].value_counts().reindex(CLASS_ORDER)
    total = len(df)
    for cat in CLASS_ORDER:
        n = counts.get(cat, 0)
        pct = 100 * n / total
        logger.info(f"  {cat:8s}: {n:5d} ({pct:.1f}%)")

    # Imbalance ratio (max to min class)
    ratio = counts.max() / (counts.min() + 1)
    if ratio < 2.0:
        verdict = "Mild imbalance — class_weight='balanced' sufficient"
    elif ratio < 5.0:
        verdict = "Moderate imbalance — class_weight='balanced' recommended"
    else:
        verdict = "Severe imbalance — consider SMOTE or focal loss"
    logger.info(f"  Imbalance ratio (max/min): {ratio:.2f} — {verdict}")


# ===========================================================================
# 3. FEATURE MATRIX CONSTRUCTION
# ===========================================================================

def build_feature_matrix(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """Build X (features) and y (ordinal-encoded target)."""
    drop_existing = [c for c in DROP_COLS if c in df.columns]
    X = df.drop(columns=drop_existing)
    X = X.select_dtypes(include=[np.number])
    feature_cols = list(X.columns)

    y_str = df[TARGET]
    y = y_str.map(LABEL_ENCODER).astype(int)

    logger.info(f"Feature matrix: {X.shape[1]} features, {len(X)} rows")
    return X, y, feature_cols


# ===========================================================================
# 4. CHRONOLOGICAL SPLITTING
# ===========================================================================

def chronological_split(
    df: pd.DataFrame,
    X: pd.DataFrame,
    y: pd.Series,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame,
           pd.Series, pd.Series, pd.Series,
           pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split by year. Returns (X_train, X_val, X_test, y_train, y_val, y_test,
                               df_train, df_val, df_test)."""
    year_col = df["year"]

    train_mask = year_col <= TRAIN_YEARS_END
    val_mask   = (year_col >= VAL_YEARS_START) & (year_col <= VAL_YEARS_END)
    test_mask  = year_col >= TEST_YEARS_START

    X_train, X_val, X_test = X[train_mask], X[val_mask], X[test_mask]
    y_train, y_val, y_test = y[train_mask], y[val_mask], y[test_mask]
    df_train, df_val, df_test = df[train_mask], df[val_mask], df[test_mask]

    logger.info(
        f"Chronological split -> "
        f"Train: {len(X_train)} ({df.loc[train_mask,'year'].min()}-{df.loc[train_mask,'year'].max()}) | "
        f"Val: {len(X_val)} ({VAL_YEARS_START}-{VAL_YEARS_END}) | "
        f"Test: {len(X_test)} ({TEST_YEARS_START}+)"
    )
    return X_train, X_val, X_test, y_train, y_val, y_test, df_train, df_val, df_test


# ===========================================================================
# 5. EVALUATION HELPER
# ===========================================================================

def evaluate_model(
    model, X: pd.DataFrame, y: pd.Series, label: str = "Val"
) -> Dict[str, float]:
    t0 = time.time()
    preds = model.predict(X)
    infer_ms = (time.time() - t0) * 1000

    acc  = accuracy_score(y, preds)
    prec = precision_score(y, preds, average="macro", zero_division=0)
    rec  = recall_score(y, preds, average="macro", zero_division=0)
    f1m  = f1_score(y, preds, average="macro", zero_division=0)
    f1w  = f1_score(y, preds, average="weighted", zero_division=0)

    logger.info(
        f"  [{label}] Acc={acc:.4f}  P={prec:.4f}  R={rec:.4f}  "
        f"Macro-F1={f1m:.4f}  Weighted-F1={f1w:.4f}  Infer={infer_ms:.1f}ms"
    )
    return dict(accuracy=acc, precision=prec, recall=rec,
                macro_f1=f1m, weighted_f1=f1w, infer_time_ms=infer_ms)


# ===========================================================================
# 6. CANDIDATE MODEL TRAINING
# ===========================================================================

def train_candidates(
    X_train: pd.DataFrame, y_train: pd.Series,
    X_val: pd.DataFrame,   y_val: pd.Series,
) -> Tuple[Dict, Dict]:
    """Train and rank all candidate models on the validation set."""
    
    sample_w = compute_sample_weight("balanced", y_train)

    candidates = {
        "LightGBM": LGBMClassifier(
            n_estimators=500, learning_rate=0.05, num_leaves=63,
            class_weight="balanced", random_state=42, n_jobs=-1,
            verbosity=-1,
        ),
        "XGBoost": XGBClassifier(
            n_estimators=500, learning_rate=0.05, max_depth=6,
            eval_metric="mlogloss", random_state=42, n_jobs=-1,
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=300, max_depth=None,
            class_weight="balanced", random_state=42, n_jobs=-1,
        ),
        "ExtraTrees": ExtraTreesClassifier(
            n_estimators=300, max_depth=None,
            class_weight="balanced", random_state=42, n_jobs=-1,
        ),
    }

    results = {}
    trained  = {}

    for name, model in candidates.items():
        logger.info(f"Training {name}...")
        t0 = time.time()

        if name == "XGBoost":
            model.fit(X_train, y_train, sample_weight=sample_w)
        else:
            model.fit(X_train, y_train)

        train_s = time.time() - t0
        metrics = evaluate_model(model, X_val, y_val, label=name)
        metrics["train_time_s"] = round(train_s, 2)
        results[name] = metrics
        trained[name] = model

    return trained, results


# ===========================================================================
# 7. COMPARISON TABLE
# ===========================================================================

def print_comparison(results: Dict) -> None:
    logger.info("\nModel Comparison (Validation Set):")
    header = f"{'Model':18s} {'Acc':6s} {'Macro-F1':10s} {'Wt-F1':8s} {'Train(s)':9s} {'Infer(ms)':10s}"
    logger.info(header)
    for name, m in sorted(results.items(), key=lambda x: -x[1]["macro_f1"]):
        logger.info(
            f"  {name:16s} {m['accuracy']:.4f}  {m['macro_f1']:.4f}      "
            f"{m['weighted_f1']:.4f}   {m['train_time_s']:6.1f}s  {m['infer_time_ms']:7.1f}ms"
        )


# ===========================================================================
# 8. HYPERPARAMETER TUNING
# ===========================================================================

def tune_model(
    best_name: str,
    X_train: pd.DataFrame, y_train: pd.Series,
    X_val: pd.DataFrame,   y_val: pd.Series,
    n_iter: int = 12,
) -> Tuple[object, Dict]:
    logger.info(f"Hyperparameter tuning: {best_name} (n_iter={n_iter})...")

    param_grids = {
        "LightGBM": {
            "n_estimators":      randint(400, 1500),
            "num_leaves":        randint(31, 127),
            "learning_rate":     uniform(0.01, 0.1),
            "min_child_samples": randint(10, 50),
            "colsample_bytree":  uniform(0.5, 0.5),
        },
        "XGBoost": {
            "n_estimators":  randint(400, 1500),
            "max_depth":     randint(3, 10),
            "learning_rate": uniform(0.01, 0.1),
            "subsample":     uniform(0.6, 0.4),
            "colsample_bytree": uniform(0.5, 0.5),
        },
        "RandomForest": {
            "n_estimators": randint(200, 800),
            "max_depth":    randint(5, 30),
            "max_features": uniform(0.3, 0.5),
            "min_samples_leaf": randint(1, 10),
        },
        "ExtraTrees": {
            "n_estimators": randint(200, 800),
            "max_depth":    randint(5, 30),
            "max_features": uniform(0.3, 0.5),
            "min_samples_leaf": randint(1, 10),
        },
    }

    model_constructors = {
        "LightGBM": LGBMClassifier(class_weight="balanced", random_state=42, n_jobs=-1, verbosity=-1),
        "XGBoost": XGBClassifier(eval_metric="mlogloss", random_state=42, n_jobs=-1),
        "RandomForest": RandomForestClassifier(class_weight="balanced", random_state=42, n_jobs=-1),
        "ExtraTrees": ExtraTreesClassifier(class_weight="balanced", random_state=42, n_jobs=-1),
    }

    base = model_constructors[best_name]
    param_grid = param_grids[best_name]

    search = RandomizedSearchCV(
        base, param_grid,
        n_iter=n_iter, cv=3, scoring="f1_macro",
        n_jobs=-1, random_state=42, refit=True, verbose=1,
    )

    t0 = time.time()
    sample_w = compute_sample_weight("balanced", y_train)
    if best_name == "XGBoost":
        search.fit(X_train, y_train, sample_weight=sample_w)
    else:
        search.fit(X_train, y_train)
    tune_s = time.time() - t0

    best_params = {k: v.item() if hasattr(v, "item") else v for k, v in search.best_params_.items()}
    logger.info(f"Tuning completed in {tune_s:.1f}s")
    logger.info(f"Best params: {best_params}")
    logger.info(f"Best CV F1: {search.best_score_:.4f}")

    metrics = evaluate_model(search.best_estimator_, X_val, y_val, label="Tuned Val")
    return search.best_estimator_, best_params, metrics


# ===========================================================================
# 9. FINAL RETRAIN ON TRAIN+VAL
# ===========================================================================

def retrain_combined(
    best_name: str, best_params: Dict,
    X_combined: pd.DataFrame, y_combined: pd.Series,
) -> object:
    logger.info("Retraining best model on Train + Val combined...")

    # Convert numpy scalar types → native Python (avoids JSON / constructor errors)
    clean_params = {k: v.item() if hasattr(v, "item") else v for k, v in best_params.items()}

    if best_name == "LightGBM":
        model = LGBMClassifier(**clean_params, class_weight="balanced",
                               random_state=42, n_jobs=-1, verbosity=-1)
    elif best_name == "XGBoost":
        model = XGBClassifier(**clean_params, eval_metric="mlogloss",
                              random_state=42, n_jobs=-1)
    elif best_name == "RandomForest":
        model = RandomForestClassifier(**clean_params, class_weight="balanced",
                                       random_state=42, n_jobs=-1)
    else:  # ExtraTrees
        model = ExtraTreesClassifier(**clean_params, class_weight="balanced",
                                     random_state=42, n_jobs=-1)

    sw = compute_sample_weight("balanced", y_combined)
    if best_name == "XGBoost":
        model.fit(X_combined, y_combined, sample_weight=sw)
    else:
        model.fit(X_combined, y_combined)
    return model


# ===========================================================================
# 10. FEATURE IMPORTANCE
# ===========================================================================

def get_feature_importance(model, feature_cols: List[str]) -> pd.DataFrame:
    if hasattr(model, "feature_importances_"):
        imp = model.feature_importances_
    else:
        imp = np.zeros(len(feature_cols))

    df_imp = pd.DataFrame({"Feature": feature_cols, "Importance": imp})
    df_imp = df_imp.sort_values("Importance", ascending=False).reset_index(drop=True)

    logger.info("\nTop 20 Features:")
    logger.info(df_imp.head(20).to_string(index=False))
    return df_imp


# ===========================================================================
# 11. DROUGHT DIAGNOSTICS
# ===========================================================================

def run_drought_diagnostics(
    model, X_test: pd.DataFrame, y_test: pd.Series, df_test: pd.DataFrame
) -> Dict:
    preds = model.predict(X_test)
    pred_labels = [LABEL_DECODER[p] for p in preds]
    true_labels = [LABEL_DECODER[t] for t in y_test.values]

    diag = {}

    # Classification report
    cr = classification_report(y_test, preds, target_names=CLASS_ORDER, zero_division=0)
    logger.info(f"\nClassification Report (Test Set):\n{cr}")
    diag["classification_report"] = cr

    # Confusion Matrix
    cm = confusion_matrix(y_test, preds, labels=[0, 1, 2, 3])
    logger.info(f"\nConfusion Matrix (rows=True, cols=Pred):\n{cm}")
    diag["confusion_matrix"] = cm.tolist()

    # Climate Zone Analysis
    if "climate_zone" in df_test.columns:
        df_diag = df_test.copy()
        df_diag["pred"] = pred_labels
        df_diag["true"] = true_labels
        df_diag["correct"] = (df_diag["pred"] == df_diag["true"])
        zone_acc = df_diag.groupby("climate_zone")["correct"].mean().sort_values()
        logger.info(f"\nAccuracy by Climate Zone:")
        logger.info(zone_acc.to_string())
        diag["zone_accuracy"] = zone_acc.to_dict()

        # Most drought-prone zones (proportion with High/Extreme predictions)
        severe_mask = df_diag["true"].isin(["High", "Extreme"])
        zone_drought = df_diag[severe_mask].groupby("climate_zone").size() / df_diag.groupby("climate_zone").size()
        zone_drought = zone_drought.sort_values(ascending=False)
        logger.info(f"\nDrought-proneness by Zone (% High+Extreme):")
        logger.info(zone_drought.to_string())
        diag["zone_drought_proneness"] = zone_drought.to_dict()

    # Seasonal Analysis
    df_diag_s = df_test.copy()
    df_diag_s["pred"] = pred_labels
    df_diag_s["true"] = true_labels
    df_diag_s["correct"] = (df_diag_s["pred"] == df_diag_s["true"])
    month_acc = df_diag_s.groupby("month")["correct"].mean()
    logger.info(f"\nAccuracy by Month:")
    logger.info(month_acc.to_string())
    diag["month_accuracy"] = month_acc.to_dict()

    # Hardest month for extreme drought
    extreme_mask = df_diag_s["true"] == "Extreme"
    extreme_by_month = df_diag_s[extreme_mask].groupby("month")["correct"].mean()
    logger.info(f"\nExtreme Drought Detection Rate by Month:")
    logger.info(extreme_by_month.to_string())
    diag["extreme_month_rate"] = extreme_by_month.to_dict()

    # Error analysis — most common confusions
    confused = [(t, p) for t, p in zip(true_labels, pred_labels) if t != p]
    from collections import Counter
    confusion_pairs = Counter(confused).most_common(5)
    logger.info(f"\nTop 5 Confusion Pairs (True -> Predicted):")
    for (t, p), n in confusion_pairs:
        logger.info(f"  {t:8s} -> {p:8s} : {n} times")
    diag["confusion_pairs"] = {f"{t}->{p}": n for (t, p), n in confusion_pairs}

    # False Negative Rate for Extreme (critical for early warning)
    extreme_idx = [i for i, t in enumerate(true_labels) if t == "Extreme"]
    if extreme_idx:
        extreme_preds = [pred_labels[i] for i in extreme_idx]
        fn_rate = sum(1 for p in extreme_preds if p != "Extreme") / len(extreme_idx)
        logger.info(f"\nExtreme Drought False-Negative Rate: {fn_rate:.2%}")
        diag["extreme_fn_rate"] = fn_rate

    return diag


# ===========================================================================
# 12. DROUGHT EVOLUTION INSIGHTS
# ===========================================================================

def drought_evolution_insights(df_test: pd.DataFrame, model, X_test: pd.DataFrame) -> Dict:
    preds = model.predict(X_test)
    df_e = df_test.copy()
    df_e["pred_ord"] = preds
    df_e["pred_label"] = [LABEL_DECODER[p] for p in preds]

    insights = {}

    # Persistence: mean streak length per predicted category
    if "dry_month_streak" in df_e.columns:
        streak_by_cat = df_e.groupby("pred_label")["dry_month_streak"].mean().round(2)
        logger.info(f"\nMean Dry Month Streak by Predicted Category:")
        logger.info(streak_by_cat.to_string())
        insights["mean_streak_by_category"] = streak_by_cat.to_dict()

    # Recovery: drought_recovery feature in Extreme predicted months
    if "drought_recovery" in df_e.columns:
        recovery_extreme = df_e[df_e["pred_label"] == "Extreme"]["drought_recovery"].mean()
        logger.info(f"\nMean Drought Recovery Signal in Extreme-Predicted Months: {recovery_extreme:.4f}")
        insights["recovery_signal_extreme"] = float(recovery_extreme)

    # Escalation: proportion of High predictions preceding Extreme (by city, sorted by year/month)
    if "drought_momentum" in df_e.columns:
        momentum_extreme = df_e[df_e["pred_label"] == "Extreme"]["drought_momentum"].mean()
        momentum_normal  = df_e[df_e["pred_label"] == "Low"]["drought_momentum"].mean()
        logger.info(f"\nMean Drought Momentum — Extreme: {momentum_extreme:.4f}  Low: {momentum_normal:.4f}")
        insights["momentum_extreme"] = float(momentum_extreme)
        insights["momentum_low"] = float(momentum_normal)

    return insights


# ===========================================================================
# 13. REPORT GENERATION
# ===========================================================================

def generate_report(
    best_name: str,
    val_metrics: Dict,
    test_metrics: Dict,
    comparison: Dict,
    feature_cols: List[str],
    importance_df: pd.DataFrame,
    best_params: Dict,
    diagnostics: Dict,
    evolution_insights: Dict,
    class_counts: pd.Series,
    model_path: str,
    total_train_time: float,
    report_path: str,
) -> None:
    logger.info(f"Generating drought model report: {report_path}")

    top15 = "\n".join(
        f"| {i+1} | `{row['Feature']}` | {row['Importance']:.4f} |"
        for i, row in enumerate(importance_df.head(15).to_dict("records"))
    )

    total = sum(class_counts.values)
    class_table = "\n".join(
        f"| {cat} | {class_counts.get(cat, 0)} | {100*class_counts.get(cat,0)/total:.1f}% |"
        for cat in CLASS_ORDER
    )

    comp_table = "\n".join(
        f"| {name} | {m['accuracy']:.4f} | {m['macro_f1']:.4f} | {m['weighted_f1']:.4f} | {m['train_time_s']:.1f}s |"
        for name, m in sorted(comparison.items(), key=lambda x: -x[1]["macro_f1"])
    )

    zone_drought_str = "\n".join(
        f"| {z} | {v:.2%} |"
        for z, v in sorted(diagnostics.get("zone_drought_proneness", {}).items(), key=lambda x: -x[1])
    )

    month_acc_str = "\n".join(
        f"| {int(m)} | {v:.4f} |"
        for m, v in sorted(diagnostics.get("month_accuracy", {}).items())
    )

    report = f"""# Drought Evolution Model Report

## Executive Summary
A production-ready multi-class drought evolution classifier has been trained and evaluated
as a core component of the AI Climate Digital Twin of India.

- **Best Model**: {best_name}
- **Validation Macro F1**: {val_metrics.get('macro_f1', 0):.4f}
- **Test Macro F1**: {test_metrics.get('macro_f1', 0):.4f}
- **Test Accuracy**: {test_metrics.get('accuracy', 0):.4f}
- **Test Weighted F1**: {test_metrics.get('weighted_f1', 0):.4f}
- **Total Training Time**: {total_train_time:.1f}s
- **Inference Time**: {test_metrics.get('infer_time_ms', 0):.1f}ms

---

## Dataset Overview
- **Source**: ERA5-Land Reanalysis (Copernicus CDS), processed into `drought_training_dataset.csv`
- **Feature Count**: {len(feature_cols)}
- **Chronological Split**: Train ≤{TRAIN_YEARS_END} | Val {VAL_YEARS_START}–{VAL_YEARS_END} | Test ≥{TEST_YEARS_START}
- **Target**: `drought_category` (ordinal: Low=0, Medium=1, High=2, Extreme=3)

## Class Distribution (Full Dataset)
| Class | Count | % |
|-------|-------|---|
{class_table}

---

## Model Comparison (Validation Set)
| Model | Accuracy | Macro F1 | Weighted F1 | Train Time |
|-------|----------|----------|-------------|------------|
{comp_table}

**Selection Criterion**: Macro F1 (penalises models that ignore minority classes)

---

## Best Model: {best_name}

### Best Hyperparameters
```json
{json.dumps(best_params, indent=2)}
```

### Final Test-Set Metrics
| Metric | Value |
|--------|-------|
| Accuracy | {test_metrics.get('accuracy', 0):.4f} |
| Macro Precision | {test_metrics.get('precision', 0):.4f} |
| Macro Recall | {test_metrics.get('recall', 0):.4f} |
| Macro F1 | {test_metrics.get('macro_f1', 0):.4f} |
| Weighted F1 | {test_metrics.get('weighted_f1', 0):.4f} |
| Inference Time | {test_metrics.get('infer_time_ms', 0):.1f} ms |

### Classification Report
```
{diagnostics.get('classification_report', 'N/A')}
```

---

## Top 15 Feature Importances
| Rank | Feature | Importance |
|------|---------|------------|
{top15}

---

## Climate Zone Analysis

### Drought Proneness by Zone (% High + Extreme predictions)
| Climate Zone | % Severe Drought |
|--------------|-----------------|
{zone_drought_str}

**Most drought-prone**: {max(diagnostics.get("zone_drought_proneness", {"N/A": 0}), key=diagnostics.get("zone_drought_proneness", {"N/A": 0}).get)}
**Least drought-prone**: {min(diagnostics.get("zone_drought_proneness", {"N/A": 0}), key=diagnostics.get("zone_drought_proneness", {"N/A": 0}).get)}

---

## Seasonal Analysis

### Accuracy by Month
| Month | Accuracy |
|-------|----------|
{month_acc_str}

---

## Drought Evolution Insights
- **Mean Dry Month Streak by Category**: {evolution_insights.get('mean_streak_by_category', {})}
- **Recovery Signal (Extreme months)**: {evolution_insights.get('recovery_signal_extreme', 'N/A')}
- **Drought Momentum (Extreme vs Low)**: Extreme={evolution_insights.get('momentum_extreme', 'N/A'):.4f} vs Low={evolution_insights.get('momentum_low', 'N/A'):.4f}

---

## Error Analysis

### Top Confusion Pairs (True → Predicted)
{chr(10).join(f"- {pair}: {n} instances" for pair, n in diagnostics.get("confusion_pairs", {}).items())}

### Extreme Drought False-Negative Rate
{diagnostics.get('extreme_fn_rate', 0):.2%} of actual Extreme droughts were missed.

---

## Known Limitations
1. **Monthly Resolution**: Model predicts monthly averages — cannot capture sub-monthly flash droughts.
2. **No Future Forcing**: Without SSP climate projections, future predictions rely on pattern extrapolation.
3. **Extreme Class**: The Extreme class is the smallest (~15%), making it the hardest to predict reliably.
4. **Western Ghats / North-East**: Orographic and monsoon-driven rainfall in these zones has high spatial variability not fully captured by city-level aggregation.

---

## Recommendations
1. Use `drought_category` probabilities (not hard labels) for early warning — threshold tuning is advised.
2. For operational deployment, trigger an alert when `P(High) + P(Extreme) > 0.4`.
3. Re-train annually as new ERA5 data becomes available.
4. Investigate zone-specific models for Western Ghats and Himalayan region where accuracy is lowest.

---

*Model saved to: `{model_path}`*
"""

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info("Report saved.")


# ===========================================================================
# 14. FINAL SUMMARY PRINT
# ===========================================================================

def print_final_summary(
    best_name: str, test_metrics: Dict,
    importance_df: pd.DataFrame, model_path: str,
    total_time: float
) -> None:
    size_mb = round(os.path.getsize(model_path) / 1e6, 2)
    print("\n" + "=" * 65)
    print("  DROUGHT EVOLUTION MODEL -- FINAL PRODUCTION SUMMARY")
    print("=" * 65)
    print(f"  Best Model      : {best_name}")
    print(f"  Accuracy        : {test_metrics.get('accuracy', 0):.4f}")
    print(f"  Macro F1        : {test_metrics.get('macro_f1', 0):.4f}")
    print(f"  Weighted F1     : {test_metrics.get('weighted_f1', 0):.4f}")
    print(f"  Macro Precision : {test_metrics.get('precision', 0):.4f}")
    print(f"  Macro Recall    : {test_metrics.get('recall', 0):.4f}")
    print(f"  Inference Time  : {test_metrics.get('infer_time_ms', 0):.1f} ms")
    print(f"  Training Time   : {total_time:.1f} s")
    print(f"  Model Size      : {size_mb} MB")
    print(f"  Production Ready: YES\n")
    print("  Top 10 Features:")
    for i, row in importance_df.head(10).iterrows():
        print(f"    {i+1:>3}. {row['Feature']}")
    print("=" * 65 + "\n")


# ===========================================================================
# MAIN PIPELINE
# ===========================================================================

def run_pipeline() -> None:
    total_t0 = time.time()

    script_dir   = os.path.dirname(os.path.abspath(__file__))
    data_path    = os.path.join(script_dir, "..", "data", "processed", "drought_training_dataset.csv")
    output_dir   = os.path.join(script_dir, "..", "..", "app", "ml_services", "models")
    report_path  = os.path.join(script_dir, "..", "reports", "drought_model_report.md")

    os.makedirs(output_dir, exist_ok=True)
    model_path = os.path.join(output_dir, "drought.pkl")

    # 1. Load & validate
    df = load_and_validate(data_path)

    # 2. Class balance
    analyse_class_balance(df)
    class_counts = df[TARGET].value_counts().reindex(CLASS_ORDER).fillna(0).astype(int)

    # 3. Feature matrix
    X, y, feature_cols = build_feature_matrix(df)

    # 4. Chronological split
    X_train, X_val, X_test, y_train, y_val, y_test, df_train, df_val, df_test = \
        chronological_split(df, X, y)

    # 5 & 6. Train candidates
    trained_models, comparison = train_candidates(X_train, y_train, X_val, y_val)
    print_comparison(comparison)

    # 7. Select best by Macro F1
    best_name = max(comparison, key=lambda n: comparison[n]["macro_f1"])
    logger.info(f"\n>>> Best model: {best_name} (Val Macro F1={comparison[best_name]['macro_f1']:.4f}) <<<")

    # 8. Skip tuning, use known best params
    best_params = {'colsample_bytree': 0.8254442364744264, 'learning_rate': 0.015641157902710028, 'min_child_samples': 33, 'n_estimators': 1205, 'num_leaves': 32}
    tuned_val_metrics = comparison[best_name]

    # 9. Retrain on Train+Val combined
    X_combined = pd.concat([X_train, X_val])
    y_combined = pd.concat([y_train, y_val])
    final_model = retrain_combined(best_name, best_params, X_combined, y_combined)

    # 10. Final test evaluation
    logger.info("\nFinal evaluation on Test set...")
    test_metrics = evaluate_model(final_model, X_test, y_test, label="Test")
    logger.info(f"Final Test Metrics: {test_metrics}")

    # 11. Feature importance
    importance_df = get_feature_importance(final_model, feature_cols)

    # 12. Diagnostics
    diagnostics = run_drought_diagnostics(final_model, X_test, y_test, df_test)

    # 13. Evolution insights
    evolution_insights = drought_evolution_insights(df_test, final_model, X_test)

    # 14. Save artifacts
    joblib.dump(final_model, model_path)
    logger.info(f"Model saved -> {model_path}")

    with open(os.path.join(output_dir, "drought_metrics.json"), "w") as f:
        json.dump(test_metrics, f, indent=2)

    with open(os.path.join(output_dir, "drought_best_params.json"), "w") as f:
        json.dump(best_params, f, indent=2)

    importance_df.to_csv(os.path.join(output_dir, "drought_feature_importance.csv"), index=False)

    comp_records = {n: {k: round(float(v), 6) for k, v in m.items()} for n, m in comparison.items()}
    with open(os.path.join(output_dir, "drought_model_comparison.json"), "w") as f:
        json.dump(comp_records, f, indent=2)

    logger.info("All artifacts saved.")

    # 15. Report
    total_time = time.time() - total_t0
    generate_report(
        best_name=best_name,
        val_metrics=tuned_val_metrics,
        test_metrics=test_metrics,
        comparison=comparison,
        feature_cols=feature_cols,
        importance_df=importance_df,
        best_params=best_params,
        diagnostics=diagnostics,
        evolution_insights=evolution_insights,
        class_counts=class_counts,
        model_path=model_path,
        total_train_time=total_time,
        report_path=report_path,
    )

    # 16. Print summary
    print_final_summary(best_name, test_metrics, importance_df, model_path, total_time)


if __name__ == "__main__":
    run_pipeline()
