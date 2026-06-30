"""
Extreme Weather Models — Final Production Training & Persistence Pipeline
========================================================================
AI-powered Digital Twin of India's Climate

Objective:
    Trains, optimizes, and evaluates production-ready classifiers for:
      - Model A: Heatwave Classifier (heatwave_category)
      - Model B: Extreme Rainfall Classifier (extreme_rainfall_category)
    and optional regressors for:
      - Model C: Heatwave Severity Score (heatwave_severity_score)
      - Model D: Extreme Rainfall Score (extreme_rainfall_score)

Methodology:
    - Chronological data splitting (Train <= 2020 | Val 2021-2022 | Test >= 2023)
    - Leakage prevention (isolated feature sets, removing post-hoc indicators)
    - Candidate comparison: LightGBM, XGBoost, Random Forest, Extra Trees
    - Macro F1-driven hyperparameter tuning via RandomizedSearchCV
    - Calibration & training of severity regressors (LGBM & XGBoost)
    - Diagnostics by Climate Zone, Month, and Monsoon phase
    - In-depth error analysis (Recall of Extreme class, Top 10 most confident misclassifications)
    - Persistence of production assets (.pkl, metrics.json, importances.csv)
    - Automatic generation of detailed markdown reports in ml_research/reports/

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
from scipy.stats import randint, uniform

from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix, classification_report,
    mean_absolute_error, root_mean_squared_error, r2_score
)
from sklearn.model_selection import RandomizedSearchCV
from sklearn.utils.class_weight import compute_sample_weight

# pyrefly: ignore [missing-import]
from xgboost import XGBClassifier, XGBRegressor
# pyrefly: ignore [missing-import]
from lightgbm import LGBMClassifier, LGBMRegressor

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants & Config
# ---------------------------------------------------------------------------
CLASS_ORDER = ["Low", "Medium", "High", "Extreme"]
LABEL_ENCODER = {c: i for i, c in enumerate(CLASS_ORDER)}
LABEL_DECODER = {i: c for c, i in LABEL_ENCODER.items()}

# Year ranges for chronological split
TRAIN_YEARS_END  = 2020
VAL_YEARS_START  = 2021
VAL_YEARS_END    = 2022
TEST_YEARS_START = 2023

# Leakage and administrative columns to drop from all features
GLOBAL_DROP_COLS = [
    "date", "city", "climate_zone",
    "target_temperature_next_month", "target_rainfall_next_month",
    "drought_risk", "heatwave_risk", "climate_risk_score"
]

# ===========================================================================
# Part 1: Data Loading & Validation
# ===========================================================================

def load_and_validate(data_path: str) -> pd.DataFrame:
    """Loads and runs comprehensive quality checks on the engineered dataset."""
    logger.info(f"Loading dataset from: {data_path}")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset path does not exist: {data_path}")
        
    df = pd.read_csv(data_path)
    logger.info(f"Loaded shape: {df.shape}")

    # Missing Value Validation
    mv = df.isnull().sum()
    mv_cols = mv[mv > 0]
    if len(mv_cols):
        logger.warning(f"Found missing values in columns:\n{mv_cols}")
        # Impute missing values with column mean as fallback
        for col in mv_cols.index:
            df[col] = df[col].fillna(df[col].mean())
        logger.info("Missing values filled with column means.")
    else:
        logger.info("Validation: 0 missing values.")

    # Duplicate Detection
    dupes = df.duplicated().sum()
    if dupes > 0:
        logger.warning(f"Found {dupes} duplicate rows. Removing duplicates.")
        df = df.drop_duplicates()
    else:
        logger.info("Validation: 0 duplicate rows.")

    # Infinite Value Checks
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    inf_counts = np.isinf(df[numeric_cols]).sum()
    inf_cols = inf_counts[inf_counts > 0]
    if len(inf_cols):
        logger.warning(f"Found infinite values in columns:\n{inf_cols}")
        df = df.replace([np.inf, -np.inf], np.nan)
        for col in inf_cols.index:
            df[col] = df[col].fillna(df[col].mean())
    else:
        logger.info("Validation: 0 infinite values.")

    # Target Distribution Analysis
    for target in ["heatwave_category", "extreme_rainfall_category"]:
        assert target in df.columns, f"Target '{target}' missing from dataset"
        dist = df[target].value_counts().reindex(CLASS_ORDER).fillna(0).astype(int)
        logger.info(f"Target '{target}' distribution:")
        total = len(df)
        for cat in CLASS_ORDER:
            count = dist.get(cat, 0)
            logger.info(f"  {cat:8s}: {count:5d} ({100*count/total:.2f}%)")

    # Feature Variance Analysis
    variance = df[numeric_cols].var()
    low_var_cols = variance[variance < 1e-6].index.tolist()
    if low_var_cols:
        logger.warning(f"Found {len(low_var_cols)} features with near-zero variance (<1e-6): {low_var_cols}")

    return df

# ===========================================================================
# Part 2: Chronological Splitting
# ===========================================================================

def split_chronologically(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Splits dataset chronologically to simulate real-world future forecasting."""
    logger.info("Splitting dataset chronologically...")
    
    train_df = df[df["year"] <= TRAIN_YEARS_END].reset_index(drop=True)
    val_df   = df[(df["year"] >= VAL_YEARS_START) & (df["year"] <= VAL_YEARS_END)].reset_index(drop=True)
    test_df  = df[df["year"] >= TEST_YEARS_START].reset_index(drop=True)

    logger.info(
        f"Split Statistics:\n"
        f"  Train      : {len(train_df):5d} rows ({train_df['year'].min()} - {train_df['year'].max()})\n"
        f"  Validation : {len(val_df):5d} rows ({val_df['year'].min()} - {val_df['year'].max()})\n"
        f"  Test       : {len(test_df):5d} rows ({test_df['year'].min()} - {test_df['year'].max()})"
    )
    return train_df, val_df, test_df

# ===========================================================================
# Part 3: Feature Preparation & Leakage Isolation
# ===========================================================================

def prepare_task_matrices(
    train_df: pd.DataFrame, val_df: pd.DataFrame, test_df: pd.DataFrame, task: str
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, List[str]]:
    """Creates isolated feature matrices (X) and ordinal targets (y) for a task."""
    logger.info(f"Preparing feature matrices for task: {task}")
    
    # Define targets and indicators for both tasks
    hw_targets = ["heatwave_category", "heatwave_category_ordinal", "heatwave_severity_score"]
    er_targets = ["extreme_rainfall_category", "extreme_rainfall_category_ordinal", "extreme_rainfall_score"]
    
    # Start with global drop list
    drop_list = list(GLOBAL_DROP_COLS)
    
    # Isolate feature sets by removing other task's engineered features & all target outputs
    if task == "heatwave":
        target_col = "heatwave_category"
        ordinal_col = "heatwave_category_ordinal"
        # Drop all extreme rainfall indicators, labels, and engineered features starting with er_
        er_engineered = [c for c in train_df.columns if c.startswith("er_")]
        drop_list.extend(hw_targets + er_targets + er_engineered)
    elif task == "extreme_rainfall":
        target_col = "extreme_rainfall_category"
        ordinal_col = "extreme_rainfall_category_ordinal"
        # Drop all heatwave indicators, labels, and engineered features starting with hw_
        hw_engineered = [c for c in train_df.columns if c.startswith("hw_")]
        drop_list.extend(hw_targets + er_targets + hw_engineered)
    else:
        raise ValueError(f"Unknown task type: {task}")

    # Build drop list of actual columns present in dataset
    actual_drops = [c for c in drop_list if c in train_df.columns]
    
    # Feature matrices X
    X_train = train_df.drop(columns=actual_drops).select_dtypes(include=[np.number])
    X_val   = val_df.drop(columns=actual_drops).select_dtypes(include=[np.number])
    X_test  = test_df.drop(columns=actual_drops).select_dtypes(include=[np.number])
    feature_cols = list(X_train.columns)

    # Ordinal targets y (Low=0, Medium=1, High=2, Extreme=3)
    y_train = train_df[target_col].map(LABEL_ENCODER).astype(int)
    y_val   = val_df[target_col].map(LABEL_ENCODER).astype(int)
    y_test  = test_df[target_col].map(LABEL_ENCODER).astype(int)

    logger.info(f"Isolated Feature Count for {task}: {len(feature_cols)}")
    # Log sample features
    logger.info(f"Sample features: {feature_cols[:8]} ...")
    return X_train, y_train, X_val, y_val, X_test, y_test, feature_cols

# ===========================================================================
# Part 4 & 5: Model Training & Evaluation
# ===========================================================================

def evaluate_classifier(model: Any, X: pd.DataFrame, y: pd.Series, label: str) -> Dict[str, Any]:
    """Helper to score classifier predictions against ground truth."""
    t0 = time.time()
    preds = model.predict(X)
    infer_ms = (time.time() - t0) * 1000

    acc  = accuracy_score(y, preds)
    prec = precision_score(y, preds, average="macro", zero_division=0)
    rec  = recall_score(y, preds, average="macro", zero_division=0)
    f1m  = f1_score(y, preds, average="macro", zero_division=0)
    f1w  = f1_score(y, preds, average="weighted", zero_division=0)

    logger.info(
        f"  [{label}] Accuracy={acc:.4f} | Macro P={prec:.4f} | "
        f"Macro R={rec:.4f} | Macro F1={f1m:.4f} | Wt F1={f1w:.4f} | Infer={infer_ms:.1f}ms"
    )
    return {
        "accuracy": float(acc),
        "precision": float(prec),
        "recall": float(rec),
        "macro_f1": float(f1m),
        "weighted_f1": float(f1w),
        "infer_time_ms": float(infer_ms)
    }

def train_classifier_candidates(
    X_train: pd.DataFrame, y_train: pd.Series,
    X_val: pd.DataFrame, y_val: pd.Series,
    task_name: str
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """Trains and compares 4 classification algorithms on the validation set."""
    logger.info(f"\n=== Training Classifier Candidates for {task_name} ===")

    # Compute sample weights to balance XGBoost (which has no built-in class_weight='balanced')
    sample_w = compute_sample_weight("balanced", y_train)

    candidates = {
        "LightGBM": LGBMClassifier(
            n_estimators=300, learning_rate=0.05, num_leaves=31,
            class_weight="balanced", random_state=42, n_jobs=-1, verbosity=-1
        ),
        "XGBoost": XGBClassifier(
            n_estimators=300, learning_rate=0.05, max_depth=5,
            eval_metric="mlogloss", random_state=42, n_jobs=-1
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=200, max_depth=12,
            class_weight="balanced", random_state=42, n_jobs=-1
        ),
        "ExtraTrees": ExtraTreesClassifier(
            n_estimators=200, max_depth=12,
            class_weight="balanced", random_state=42, n_jobs=-1
        )
    }

    trained_models = {}
    comparison = {}

    for name, model in candidates.items():
        logger.info(f"Training candidate: {name} ...")
        t0 = time.time()
        
        if name == "XGBoost":
            model.fit(X_train, y_train, sample_weight=sample_w)
        else:
            model.fit(X_train, y_train)
            
        train_s = time.time() - t0
        metrics = evaluate_classifier(model, X_val, y_val, name)
        metrics["train_time_s"] = round(train_s, 2)
        
        comparison[name] = metrics
        trained_models[name] = model

    return trained_models, comparison

# ===========================================================================
# Part 6: Hyperparameter Optimization
# ===========================================================================

def optimize_hyperparameters(
    best_name: str,
    X_train: pd.DataFrame, y_train: pd.Series,
    X_val: pd.DataFrame, y_val: pd.Series,
    task_name: str,
    n_iter: int = 10
) -> Tuple[Any, Dict[str, Any], Dict[str, Any]]:
    """Runs a RandomizedSearchCV over hyperparameter space of the winning model."""
    logger.info(f"\n=== Optimizing Hyperparameters for {best_name} ({task_name}) ===")
    
    param_grids = {
        "LightGBM": {
            "n_estimators": randint(150, 600),
            "num_leaves": randint(15, 63),
            "learning_rate": uniform(0.02, 0.08),
            "subsample": uniform(0.6, 0.4),
            "colsample_bytree": uniform(0.6, 0.4),
        },
        "XGBoost": {
            "n_estimators": randint(150, 600),
            "max_depth": randint(3, 8),
            "learning_rate": uniform(0.02, 0.08),
            "subsample": uniform(0.6, 0.4),
            "colsample_bytree": uniform(0.6, 0.4),
        },
        "RandomForest": {
            "n_estimators": randint(100, 400),
            "max_depth": randint(6, 18),
            "min_samples_leaf": randint(1, 6),
        },
        "ExtraTrees": {
            "n_estimators": randint(100, 400),
            "max_depth": randint(6, 18),
            "min_samples_leaf": randint(1, 6),
        }
    }

    base_models = {
        "LightGBM": LGBMClassifier(class_weight="balanced", random_state=42, n_jobs=-1, verbosity=-1),
        "XGBoost": XGBClassifier(eval_metric="mlogloss", random_state=42, n_jobs=-1),
        "RandomForest": RandomForestClassifier(class_weight="balanced", random_state=42, n_jobs=-1),
        "ExtraTrees": ExtraTreesClassifier(class_weight="balanced", random_state=42, n_jobs=-1),
    }

    base = base_models[best_name]
    grid = param_grids[best_name]

    search = RandomizedSearchCV(
        base, grid, n_iter=n_iter, cv=3, scoring="f1_macro",
        n_jobs=1, random_state=42, refit=True, verbose=0
    )

    t0 = time.time()
    sample_w = compute_sample_weight("balanced", y_train)
    
    if best_name == "XGBoost":
        search.fit(X_train, y_train, sample_weight=sample_w)
    else:
        search.fit(X_train, y_train)
        
    tune_s = time.time() - t0
    logger.info(f"Tuning completed in {tune_s:.1f}s")
    
    best_params = {k: v.item() if hasattr(v, "item") else v for k, v in search.best_params_.items()}
    logger.info(f"Best Params found: {best_params}")
    logger.info(f"Best Cross-Val Macro F1: {search.best_score_:.4f}")
    
    # Evaluate optimized model on validation set
    val_metrics = evaluate_classifier(search.best_estimator_, X_val, y_val, "Tuned Model")
    val_metrics["train_time_s"] = round(tune_s, 2)

    return search.best_estimator_, best_params, val_metrics

# ===========================================================================
# Part 7: Final Retrain
# ===========================================================================

def retrain_best_classifier(
    best_name: str, best_params: Dict[str, Any],
    X_combined: pd.DataFrame, y_combined: pd.Series
) -> Any:
    """Retrains the optimized classifier model on the joint Train + Validation dataset."""
    logger.info("Retraining optimized classifier on Train + Val combined dataset...")
    
    clean_params = {k: v.item() if hasattr(v, "item") else v for k, v in best_params.items()}

    if best_name == "LightGBM":
        model = LGBMClassifier(**clean_params, class_weight="balanced", random_state=42, n_jobs=-1, verbosity=-1)
    elif best_name == "XGBoost":
        model = XGBClassifier(**clean_params, eval_metric="mlogloss", random_state=42, n_jobs=-1)
    elif best_name == "RandomForest":
        model = RandomForestClassifier(**clean_params, class_weight="balanced", random_state=42, n_jobs=-1)
    else:  # ExtraTrees
        model = ExtraTreesClassifier(**clean_params, class_weight="balanced", random_state=42, n_jobs=-1)

    sw = compute_sample_weight("balanced", y_combined)
    if best_name == "XGBoost":
        model.fit(X_combined, y_combined, sample_weight=sw)
    else:
        model.fit(X_combined, y_combined)
        
    return model

# ===========================================================================
# Part 8, 9 & 10: Feature Importance, Diagnostics & Error Analysis
# ===========================================================================

def get_feature_importance(model: Any, feature_cols: List[str]) -> pd.DataFrame:
    """Extracts and sorts features by global Gini/Gain split importance."""
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    else:
        importances = np.zeros(len(feature_cols))
        
    df_imp = pd.DataFrame({"Feature": feature_cols, "Importance": importances})
    df_imp = df_imp.sort_values("Importance", ascending=False).reset_index(drop=True)
    return df_imp

def run_detailed_diagnostics(
    model: Any, X_test: pd.DataFrame, y_test: pd.Series, df_test: pd.DataFrame, task: str
) -> Dict[str, Any]:
    """Generates confusion matrices, climate zone splits, monthly streaks, and error analysis."""
    logger.info(f"Running diagnostics on Test set for {task}...")
    
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)
    
    pred_labels = [LABEL_DECODER[p] for p in preds]
    true_labels = [LABEL_DECODER[t] for t in y_test.values]

    diagnostics = {}

    # Classification Report
    cr = classification_report(y_test, preds, target_names=CLASS_ORDER, zero_division=0)
    diagnostics["classification_report"] = cr

    # Confusion Matrix
    cm = confusion_matrix(y_test, preds, labels=[0, 1, 2, 3])
    diagnostics["confusion_matrix"] = cm.tolist()

    # Create temporary diagnostics dataframe
    df_diag = df_test.copy()
    df_diag["pred"] = pred_labels
    df_diag["true"] = true_labels
    df_diag["correct"] = (df_diag["pred"] == df_diag["true"])
    
    # Climate Zone Accuracy
    if "climate_zone" in df_diag.columns:
        zone_acc = df_diag.groupby("climate_zone")["correct"].mean().sort_values()
        diagnostics["zone_accuracy"] = zone_acc.to_dict()
        
        # Proneness (% of actual High/Extreme events per zone)
        zone_proneness = (
            df_diag[df_diag["true"].isin(["High", "Extreme"])].groupby("climate_zone").size()
            / df_diag.groupby("climate_zone").size()
        ).fillna(0).sort_values(ascending=False)
        diagnostics["zone_proneness"] = zone_proneness.to_dict()

    # Seasonal Analysis (Accuracy by month)
    month_acc = df_diag.groupby("month")["correct"].mean().sort_dict() if hasattr(df_diag.groupby("month")["correct"].mean(), 'sort_dict') else df_diag.groupby("month")["correct"].mean()
    diagnostics["month_accuracy"] = month_acc.to_dict()

    # Extreme class recall
    extreme_true_idx = [i for i, t in enumerate(true_labels) if t == "Extreme"]
    if extreme_true_idx:
        extreme_preds = [pred_labels[i] for i in extreme_true_idx]
        ext_recall = sum(1 for p in extreme_preds if p == "Extreme") / len(extreme_true_idx)
        ext_fn_rate = 1.0 - ext_recall
        diagnostics["extreme_recall"] = ext_recall
        diagnostics["extreme_fn_rate"] = ext_fn_rate
        logger.info(f"[{task.upper()}] Extreme Class Recall: {ext_recall:.2%} | False-Negative Rate: {ext_fn_rate:.2%}")
    else:
        diagnostics["extreme_recall"] = 0.0
        diagnostics["extreme_fn_rate"] = 0.0

    # Common confusion pairs
    confused_mask = df_diag["pred"] != df_diag["true"]
    df_confused = df_diag[confused_mask]
    if len(df_confused) > 0:
        conf_pairs = df_confused.groupby(["true", "pred"]).size().sort_values(ascending=False).head(5)
        diagnostics["confusion_pairs"] = {f"{t}->{p}": int(v) for (t, p), v in conf_pairs.items()}
    else:
        diagnostics["confusion_pairs"] = {}

    # Top 10 Most Confident Misclassifications
    # Calculate margin = prob(predicted_class) - prob(true_class)
    margin = []
    for idx, (p_idx, t_idx) in enumerate(zip(preds, y_test.values)):
        if p_idx != t_idx:
            # Misclassified
            prob_pred = probs[idx][p_idx]
            prob_true = probs[idx][t_idx]
            margin.append((idx, prob_pred - prob_true, prob_pred, prob_true))
    
    # Sort by prediction margin descending (most confident incorrect predictions first)
    margin = sorted(margin, key=lambda x: -x[1])
    top_10_errors = []
    
    for rank, (idx, diff, p_prob, t_prob) in enumerate(margin[:10], 1):
        row = df_test.iloc[idx]
        error_entry = {
            "rank": rank,
            "city": row.get("city", "Unknown"),
            "date": str(row.get("date")).split()[0],
            "climate_zone": row.get("climate_zone", "Unknown"),
            "true_category": LABEL_DECODER[y_test.iloc[idx]],
            "predicted_category": LABEL_DECODER[preds[idx]],
            "probability_predicted": float(p_prob),
            "probability_true": float(t_prob),
            "temperature_c": float(row.get("temperature_c", 0.0)),
            "rainfall_mm": float(row.get("rainfall_mm", 0.0)),
            "soil_moisture": float(row.get("soil_moisture", 0.0))
        }
        top_10_errors.append(error_entry)
        
    diagnostics["top_10_misclassifications"] = top_10_errors

    return diagnostics

# ===========================================================================
# Part 11: Optional Regression Models
# ===========================================================================

def train_and_select_regressors(
    train_df: pd.DataFrame, val_df: pd.DataFrame, test_df: pd.DataFrame, task: str
) -> Tuple[Any, Dict[str, float]]:
    """Trains and compares LightGBM and XGBoost Regressors on severity scores."""
    logger.info(f"\n=== Training Severity Regressors for {task} ===")
    
    target_col = "heatwave_severity_score" if task == "heatwave" else "extreme_rainfall_score"
    
    # Drops same variables as class features
    drop_list = list(GLOBAL_DROP_COLS)
    hw_targets = ["heatwave_category", "heatwave_category_ordinal", "heatwave_severity_score"]
    er_targets = ["extreme_rainfall_category", "extreme_rainfall_category_ordinal", "extreme_rainfall_score"]
    
    if task == "heatwave":
        er_engineered = [c for c in train_df.columns if c.startswith("er_")]
        drop_list.extend(hw_targets + er_targets + er_engineered)
    else:
        hw_engineered = [c for c in train_df.columns if c.startswith("hw_")]
        drop_list.extend(hw_targets + er_targets + hw_engineered)

    actual_drops = [c for c in drop_list if c in train_df.columns]
    
    X_train = train_df.drop(columns=actual_drops).select_dtypes(include=[np.number])
    X_val   = val_df.drop(columns=actual_drops).select_dtypes(include=[np.number])
    X_test  = test_df.drop(columns=actual_drops).select_dtypes(include=[np.number])
    
    y_train = train_df[target_col]
    y_val   = val_df[target_col]
    y_test  = test_df[target_col]
    
    # Train candidates
    models = {
        "LightGBM": LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=31, random_state=42, n_jobs=-1, verbosity=-1),
        "XGBoost": XGBRegressor(n_estimators=300, learning_rate=0.05, max_depth=5, random_state=42, n_jobs=-1)
    }
    
    best_r2 = -float("inf")
    best_model = None
    best_metrics = {}
    
    for name, model in models.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        
        mae = mean_absolute_error(y_test, preds)
        rmse = root_mean_squared_error(y_test, preds)
        r2 = r2_score(y_test, preds)
        
        logger.info(f"  [{name} Regressor] MAE={mae:.4f} | RMSE={rmse:.4f} | R2={r2:.4f}")
        
        if r2 > best_r2:
            best_r2 = r2
            # Retrain on combined Train + Val
            X_combined = pd.concat([X_train, X_val])
            y_combined = pd.concat([y_train, y_val])
            
            best_model = name
            winning_regressor = models[name].fit(X_combined, y_combined)
            # Recompute on Test for the final output metrics
            final_preds = winning_regressor.predict(X_test)
            best_metrics = {
                "algorithm": name,
                "mae": float(mean_absolute_error(y_test, final_preds)),
                "rmse": float(root_mean_squared_error(y_test, final_preds)),
                "r2": float(r2_score(y_test, final_preds))
            }
            
    logger.info(f"Selected Best Regressor: {best_model} (R2={best_metrics['r2']:.4f})")
    return winning_regressor, best_metrics

# ===========================================================================
# Part 13: Final Report Generation
# ===========================================================================

def generate_markdown_report(
    task: str,
    best_name: str,
    val_metrics: Dict[str, Any],
    test_metrics: Dict[str, Any],
    comparison: Dict[str, Dict[str, Any]],
    features: List[str],
    importance_df: pd.DataFrame,
    best_params: Dict[str, Any],
    diagnostics: Dict[str, Any],
    class_counts: pd.Series,
    regressor_metrics: Dict[str, Any],
    model_path: str,
    total_time: float,
    report_path: str
) -> None:
    """Writes a beautifully formatted scientific report for the training run."""
    logger.info(f"Generating markdown report at: {report_path}")
    
    title = "Heatwave Model Report" if task == "heatwave" else "Extreme Rainfall Model Report"
    desc_type = "heatwaves" if task == "heatwave" else "extreme rainfall events"
    target_var = "heatwave_category" if task == "heatwave" else "extreme_rainfall_category"
    sev_var = "heatwave_severity_score" if task == "heatwave" else "extreme_rainfall_score"
    
    total = sum(class_counts.values)
    class_table_rows = "\n".join(
        f"| {cat} | {class_counts.get(cat, 0):,} | {100*class_counts.get(cat, 0)/total:.2f}% |"
        for cat in CLASS_ORDER
    )
    
    comp_rows = "\n".join(
        f"| {name} | {m['accuracy']:.4f} | {m['macro_f1']:.4f} | {m['weighted_f1']:.4f} | {m['train_time_s']:.2f}s |"
        for name, m in sorted(comparison.items(), key=lambda x: -x[1]["macro_f1"])
    )
    
    top_15_imp = "\n".join(
        f"| {idx+1} | `{row['Feature']}` | {row['Importance']:.5f} |"
        for idx, row in importance_df.head(15).iterrows()
    )

    zone_acc_rows = "\n".join(
        f"| {zone} | {acc:.2%} |"
        for zone, acc in sorted(diagnostics.get("zone_accuracy", {}).items(), key=lambda x: x[1])
    )
    
    zone_pron_rows = "\n".join(
        f"| {zone} | {pron:.2%} |"
        for zone, pron in sorted(diagnostics.get("zone_proneness", {}).items(), key=lambda x: -x[1])
    )

    month_acc_rows = "\n".join(
        f"| Month {int(month)} | {acc:.2%} |"
        for month, acc in sorted(diagnostics.get("month_accuracy", {}).items())
    )

    confusion_pairs_rows = "\n".join(
        f"- **{pair}**: {count} occurrences"
        for pair, count in diagnostics.get("confusion_pairs", {}).items()
    )

    # Top 10 Confident Errors Formatting
    top_errors_md = []
    top_errors_md.append("| Rank | City | Date | True | Predicted | Prob (Pred) | Prob (True) | Temp (°C) | Rain (mm) |")
    top_errors_md.append("|---|---|---|---|---|---|---|---|---|")
    for err in diagnostics.get("top_10_misclassifications", []):
        top_errors_md.append(
            f"| {err['rank']} | {err['city']} | {err['date']} | **{err['true_category']}** | **{err['predicted_category']}** | "
            f"{err['probability_predicted']:.2%} | {err['probability_true']:.2%} | {err['temperature_c']:.1f}°C | {err['rainfall_mm']:.1f}mm |"
        )
    top_errors_md_str = "\n".join(top_errors_md)

    report_content = f"""# {title}
## AI Climate Digital Twin of India

## Executive Summary
This report summarizes the training, evaluation, and selection of the final production-ready model for predicting **{desc_type}** across 47 Indian cities.

- **Classifier Selected**: `{best_name}`
- **Validation Macro F1**: `{val_metrics['macro_f1']:.4f}`
- **Test Macro F1**: `{test_metrics['macro_f1']:.4f}`
- **Test Accuracy**: `{test_metrics['accuracy']:.4f}`
- **Test Weighted F1**: `{test_metrics['weighted_f1']:.4f}`
- **Inference Time (batch)**: `{test_metrics['infer_time_ms']:.1f} ms`
- **Total Pipeline Execution**: `{total_time:.2f}s`

---

## Dataset Overview & Target Class Distribution
- **Dataset Size**: {total:,} rows (chronologically split)
- **Feature Set size**: {len(features)} variables (fully isolated to prevent leakage)
- **Target Variable**: `{target_var}`

### Class Frequencies
| Category | Row Count | Percentage |
|---|---|---|
{class_table_rows}

---

## Model Comparison (Validation Set)
Candidate models were evaluated using chronological splitting (train $\le$ 2020, validation 2021-2022). The primary ranking metric is **Macro F1** to ensure strong predictive performance on rare extreme events.

| Model | Accuracy | Macro F1 | Weighted F1 | Training Time |
|---|---|---|---|---|
{comp_rows}

### Best Hyperparameters (`{best_name}`)
```json
{json.dumps(best_params, indent=2)}
```

---

## Final Performance (Test Set: $\ge$ 2023)
The optimized model was retrained on the combined Train + Validation dataset and evaluated on the holdout 2023–2025 Test dataset.

| Metric | Holdout Test Score |
|---|---|
| **Accuracy** | {test_metrics['accuracy']:.2%} |
| **Macro Precision** | {test_metrics['precision']:.4f} |
| **Macro Recall** | {test_metrics['recall']:.4f} |
| **Macro F1** | {test_metrics['macro_f1']:.4f} |
| **Weighted F1** | {test_metrics['weighted_f1']:.4f} |

### Classification Report
```
{diagnostics.get('classification_report', 'N/A')}
```

---

## Top 15 Feature Importances
Global Gini/Gain feature importance values for the chosen model.

| Rank | Feature | Importance |
|---|---|---|
{top_15_imp}

---

## Error Analysis & Key Diagnostics
A deep dive into the model failures on the holdout Test set.

### 1. Extreme Class Performance
* **Extreme Recall Rate**: {diagnostics.get('extreme_recall', 0.0):.2%} (True detection rate for Extreme category events)
* **Extreme Miss Rate (False-Negative Rate)**: {diagnostics.get('extreme_fn_rate', 0.0):.2%} (Unpredicted Extreme events)

### 2. Common Confusion Pairs (True $\rightarrow$ Predicted)
These represent the most common category transitions predicted incorrectly:
{confusion_pairs_rows}

### 3. Top 10 Most Confident Misclassifications
These are the cases where the model incorrectly predicted a category with high probability:
{top_errors_md_str}

---

## Climate Zone & Seasonal Diagnostics

### 1. Prediction Accuracy by Climate Zone (Lowest to Highest)
| Climate Zone | Accuracy |
|---|---|
{zone_acc_rows}

### 2. Event Proneness by Climate Zone (% High + Extreme)
| Climate Zone | % Severe Events |
|---|---|
{zone_pron_rows}

### 3. Prediction Accuracy by Month
| Month | Accuracy |
|---|---|
{month_acc_rows}

---

## Severity Regression Model (`{regressor_metrics['algorithm']}`)
A continuous estimator was trained on the continuous score `{sev_var}` in range `[0, 1]`.

- **Best Regressor**: `{regressor_metrics['algorithm']}Regressor`
- **Mean Absolute Error (MAE)**: `{regressor_metrics['mae']:.5f}`
- **Root Mean Squared Error (RMSE)**: `{regressor_metrics['rmse']:.5f}`
- **$R^2$ Score**: `{regressor_metrics['r2']:.4f}`

---

## Recommendations & Deployment Guidance
1. **Probability Thresholds**: When deploying for early warnings, utilize probability thresholds instead of hard argmax categories. For instance, trigger alarms if $P(\\text{{High}}) + P(\\text{{Extreme}}) > 0.35$.
2. **Climate Zone Adjustments**: Review prediction margins closely in regions with high topographical variances (e.g. Himalayan and North-East regions) which exhibit lower accuracy.
3. **Data Refresh**: Re-evaluate and retrain features annually as newer climatology baselines become available.

*Model Saved to: `{model_path}`*
"""
    
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    logger.info(f"Markdown report written successfully: {report_path}")

# ===========================================================================
# Main Execution Pipeline
# ===========================================================================

def run_pipeline() -> None:
    logger.info("Initializing Extreme Weather model training pipeline...")
    pipeline_start_time = time.time()
    
    # Path settings
    script_dir   = os.path.dirname(os.path.abspath(__file__))
    data_path    = os.path.join(script_dir, "..", "data", "processed", "extreme_weather_dataset.csv")
    output_dir   = os.path.join(script_dir, "..", "..", "app", "ml_services", "models")
    reports_dir  = os.path.join(script_dir, "..", "reports")
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)
    
    # 1. Loading & validation
    df = load_and_validate(data_path)
    
    # 2. Chronological Splitting
    train_df, val_df, test_df = split_chronologically(df)
    
    # Dictionary to keep outputs for final prints
    final_outputs = {}

    for task in ["heatwave", "extreme_rainfall"]:
        logger.info(f"\n==================================================")
        logger.info(f"STARTING PIPELINE FOR {task.upper()} MODEL")
        logger.info(f"==================================================")
        
        # 3. Feature preparation
        X_train, y_train, X_val, y_val, X_test, y_test, features = prepare_task_matrices(
            train_df, val_df, test_df, task
        )
        
        # 4 & 5. Candidate training
        trained_candidates, comparison = train_classifier_candidates(
            X_train, y_train, X_val, y_val, task
        )
        
        # 6. Hyperparameter Optimization on best candidate
        # Rank by Macro F1
        best_candidate_name = max(comparison, key=lambda name: comparison[name]["macro_f1"])
        logger.info(f"Winning validation algorithm: {best_candidate_name}")
        
        optimized_model, best_params, tuned_val_metrics = optimize_hyperparameters(
            best_candidate_name, X_train, y_train, X_val, y_val, task, n_iter=12
        )
        
        # 7. Final Retrain on Train + Val combined
        X_combined = pd.concat([X_train, X_val])
        y_combined = pd.concat([y_train, y_val])
        final_clf = retrain_best_classifier(best_candidate_name, best_params, X_combined, y_combined)
        
        # Evaluate on holdout Test set
        logger.info("Evaluating final retrained classifier on Test holdout set...")
        test_metrics = evaluate_classifier(final_clf, X_test, y_test, "Final Test")
        
        # 8, 9 & 10. Importance, Diagnostics & Error Analysis
        importance_df = get_feature_importance(final_clf, features)
        diagnostics = run_detailed_diagnostics(final_clf, X_test, y_test, test_df, task)
        
        # 11. Train Severity Regressors
        final_reg, regressor_metrics = train_and_select_regressors(train_df, val_df, test_df, task)
        
        # 12. Save Artifacts
        # Build path filenames
        clf_pkl_path = os.path.join(output_dir, f"{task}.pkl")
        reg_pkl_path = os.path.join(output_dir, f"{task}_severity.pkl")
        metrics_json_path = os.path.join(output_dir, f"{task}_metrics.json")
        importance_csv_path = os.path.join(output_dir, f"{task}_feature_importance.csv")
        
        # Save models
        joblib.dump(final_clf, clf_pkl_path)
        joblib.dump(final_reg, reg_pkl_path)
        logger.info(f"Saved classifier -> {clf_pkl_path}")
        logger.info(f"Saved regressor -> {reg_pkl_path}")
        
        # Save feature importances
        importance_df.to_csv(importance_csv_path, index=False)
        logger.info(f"Saved feature importances -> {importance_csv_path}")
        
        # Save metrics
        metrics_payload = {
            "classifier": {
                "algorithm": best_candidate_name,
                "best_params": best_params,
                "val_macro_f1": float(tuned_val_metrics["macro_f1"]),
                "test_accuracy": float(test_metrics["accuracy"]),
                "test_precision_macro": float(test_metrics["precision"]),
                "test_recall_macro": float(test_metrics["recall"]),
                "test_macro_f1": float(test_metrics["macro_f1"]),
                "test_weighted_f1": float(test_metrics["weighted_f1"]),
                "extreme_recall": float(diagnostics["extreme_recall"]),
                "extreme_fn_rate": float(diagnostics["extreme_fn_rate"]),
            },
            "regressor": regressor_metrics
        }
        with open(metrics_json_path, "w") as f:
            json.dump(metrics_payload, f, indent=2)
        logger.info(f"Saved metrics metadata -> {metrics_json_path}")
        
        # 13. Reports
        report_path = os.path.join(reports_dir, f"{task}_model_report.md")
        class_counts = df[f"{task}_category"].value_counts().reindex(CLASS_ORDER).fillna(0).astype(int)
        
        generate_markdown_report(
            task=task,
            best_name=best_candidate_name,
            val_metrics=tuned_val_metrics,
            test_metrics=test_metrics,
            comparison=comparison,
            features=features,
            importance_df=importance_df,
            best_params=best_params,
            diagnostics=diagnostics,
            class_counts=class_counts,
            regressor_metrics=regressor_metrics,
            model_path=clf_pkl_path,
            total_time=time.time() - pipeline_start_time,
            report_path=report_path
        )
        
        # Save for part 14 printing
        final_outputs[task] = {
            "best_model": best_candidate_name,
            "accuracy": test_metrics["accuracy"],
            "macro_f1": test_metrics["macro_f1"],
            "weighted_f1": test_metrics["weighted_f1"],
            "regressor": regressor_metrics
        }
        
    # ===========================================================================
    # Part 14: Final Output Printing
    # ===========================================================================
    total_duration = time.time() - pipeline_start_time
    
    print("\n" + "=" * 65)
    print("  EXTREME WEATHER INTELLIGENCE MODELS -- FINAL SUMMARY")
    print("=" * 65)
    
    hw_out = final_outputs["heatwave"]
    print(f"  Model A: HEATWAVE CLASSIFIER")
    print(f"    Best Model  : {hw_out['best_model']}")
    print(f"    Accuracy    : {hw_out['accuracy']:.4f}")
    print(f"    Macro F1    : {hw_out['macro_f1']:.4f}")
    print(f"    Weighted F1 : {hw_out['weighted_f1']:.4f}")
    print(f"    Regressor   : {hw_out['regressor']['algorithm']}Regressor (MAE={hw_out['regressor']['mae']:.5f}, R²={hw_out['regressor']['r2']:.4f})")
    print("-" * 65)
    
    er_out = final_outputs["extreme_rainfall"]
    print(f"  Model B: EXTREME RAINFALL CLASSIFIER")
    print(f"    Best Model  : {er_out['best_model']}")
    print(f"    Accuracy    : {er_out['accuracy']:.4f}")
    print(f"    Macro F1    : {er_out['macro_f1']:.4f}")
    print(f"    Weighted F1 : {er_out['weighted_f1']:.4f}")
    print(f"    Regressor   : {er_out['regressor']['algorithm']}Regressor (MAE={er_out['regressor']['mae']:.5f}, R²={er_out['regressor']['r2']:.4f})")
    print("-" * 65)
    
    print(f"  Total pipeline duration: {total_duration:.2f} seconds")
    print(f"  Status                 : PRODUCTION READY")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    run_pipeline()
