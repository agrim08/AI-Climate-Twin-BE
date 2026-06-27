# Extreme Rainfall Model Report
## AI Climate Digital Twin of India

## Executive Summary
This report summarizes the training, evaluation, and selection of the final production-ready model for predicting **extreme rainfall events** across 47 Indian cities.

- **Classifier Selected**: `LightGBM`
- **Validation Macro F1**: `0.9295`
- **Test Macro F1**: `0.9451`
- **Test Accuracy**: `0.9579`
- **Test Weighted F1**: `0.9581`
- **Inference Time (batch)**: `339.2 ms`
- **Total Pipeline Execution**: `854.01s`

---

## Dataset Overview & Target Class Distribution
- **Dataset Size**: 61,776 rows (chronologically split)
- **Feature Set size**: 45 variables (fully isolated to prevent leakage)
- **Target Variable**: `extreme_rainfall_category`

### Class Frequencies
| Category | Row Count | Percentage |
|---|---|---|
| Low | 30,888 | 50.00% |
| Medium | 15,444 | 25.00% |
| High | 9,108 | 14.74% |
| Extreme | 6,336 | 10.26% |

---

## Model Comparison (Validation Set)
Candidate models were evaluated using chronological splitting (train $\le$ 2020, validation 2021-2022). The primary ranking metric is **Macro F1** to ensure strong predictive performance on rare extreme events.

| Model | Accuracy | Macro F1 | Weighted F1 | Training Time |
|---|---|---|---|---|
| LightGBM | 0.9476 | 0.9311 | 0.9479 | 9.83s |
| XGBoost | 0.9352 | 0.9156 | 0.9357 | 8.24s |
| RandomForest | 0.9297 | 0.9138 | 0.9301 | 8.34s |
| ExtraTrees | 0.8935 | 0.8775 | 0.8939 | 2.28s |

### Best Hyperparameters (`LightGBM`)
```json
{
  "colsample_bytree": 0.6557975442608167,
  "learning_rate": 0.043371571882817456,
  "n_estimators": 420,
  "num_leaves": 61,
  "subsample": 0.8473544037332349
}
```

---

## Final Performance (Test Set: $\ge$ 2023)
The optimized model was retrained on the combined Train + Validation dataset and evaluated on the holdout 2023–2025 Test dataset.

| Metric | Holdout Test Score |
|---|---|
| **Accuracy** | 95.79% |
| **Macro Precision** | 0.9447 |
| **Macro Recall** | 0.9457 |
| **Macro F1** | 0.9451 |
| **Weighted F1** | 0.9581 |

### Classification Report
```
              precision    recall  f1-score   support

         Low       0.99      0.98      0.98      3578
      Medium       0.93      0.95      0.94      1738
        High       0.91      0.92      0.92      1059
     Extreme       0.95      0.93      0.94       753

    accuracy                           0.96      7128
   macro avg       0.94      0.95      0.95      7128
weighted avg       0.96      0.96      0.96      7128

```

---

## Top 15 Feature Importances
Global Gini/Gain feature importance values for the chosen model.

| Rank | Feature | Importance |
|---|---|---|
| 1 | `er_rainfall_anomaly` | 6419.00000 |
| 2 | `er_flood_potential_proxy` | 5665.00000 |
| 3 | `er_runoff_pressure` | 4985.00000 |
| 4 | `er_compound_rainfall_saturation` | 3794.00000 |
| 5 | `longitude` | 3624.00000 |
| 6 | `soil_moisture` | 3610.00000 |
| 7 | `er_rainfall_acceleration` | 3443.00000 |
| 8 | `latitude` | 3257.00000 |
| 9 | `er_seasonal_rainfall_deviation` | 3071.00000 |
| 10 | `er_rainfall_variability_6m` | 2924.00000 |
| 11 | `er_rainfall_surge` | 2835.00000 |
| 12 | `er_zone_rainfall_anomaly` | 2772.00000 |
| 13 | `er_rainfall_zscore` | 2757.00000 |
| 14 | `er_rainfall_momentum` | 2721.00000 |
| 15 | `temperature_prev_3` | 2698.00000 |

---

## Error Analysis & Key Diagnostics
A deep dive into the model failures on the holdout Test set.

### 1. Extreme Class Performance
* **Extreme Recall Rate**: 93.36% (True detection rate for Extreme category events)
* **Extreme Miss Rate (False-Negative Rate)**: 6.64% (Unpredicted Extreme events)

### 2. Common Confusion Pairs (True $ightarrow$ Predicted)
These represent the most common category transitions predicted incorrectly:
- **Low->Medium**: 76 occurrences
- **Medium->High**: 50 occurrences
- **Extreme->High**: 50 occurrences
- **High->Medium**: 46 occurrences
- **Medium->Low**: 43 occurrences

### 3. Top 10 Most Confident Misclassifications
These are the cases where the model incorrectly predicted a category with high probability:
| Rank | City | Date | True | Predicted | Prob (Pred) | Prob (True) | Temp (°C) | Rain (mm) |
|---|---|---|---|---|---|---|---|---|
| 1 | Aligarh | 2025-07-01 | **Extreme** | **High** | 99.93% | 0.07% | 37.0°C | 170.6mm |
| 2 | Gulbarga | 2025-07-01 | **Medium** | **High** | 99.28% | 0.72% | 37.8°C | 170.0mm |
| 3 | Jamshedpur | 2025-06-01 | **Medium** | **High** | 99.21% | 0.77% | 41.0°C | 205.1mm |
| 4 | Churu | 2025-04-01 | **Extreme** | **High** | 99.03% | 0.86% | 43.4°C | 23.6mm |
| 5 | Ratnagiri | 2024-06-01 | **High** | **Extreme** | 99.03% | 0.97% | 36.5°C | 460.0mm |
| 6 | Tumakuru | 2024-07-01 | **Extreme** | **High** | 98.82% | 1.17% | 39.1°C | 265.0mm |
| 7 | Hubballi | 2024-06-01 | **Extreme** | **High** | 98.60% | 1.31% | 43.4°C | 209.4mm |
| 8 | Gurugram | 2024-06-01 | **High** | **Extreme** | 98.62% | 1.38% | 35.3°C | 180.9mm |
| 9 | Shillong | 2024-06-01 | **Extreme** | **High** | 98.11% | 1.87% | 28.7°C | 340.0mm |
| 10 | Puri | 2024-06-01 | **Extreme** | **High** | 98.01% | 1.96% | 39.1°C | 245.0mm |

---

## Climate Zone & Seasonal Diagnostics

### 1. Prediction Accuracy by Climate Zone (Lowest to Highest)
| Climate Zone | Accuracy |
|---|---|
| Thar Desert Region | 93.98% |
| Central Plateau Region | 94.91% |
| Indo-Gangetic Plains | 95.48% |
| Eastern Coastal Region | 95.49% |
| Himalayan Region | 95.56% |
| Western Coastal Region | 95.83% |
| North-East Region | 96.03% |
| Western Ghats Region | 96.76% |
| Southern Peninsular Region | 96.99% |

### 2. Event Proneness by Climate Zone (% High + Extreme)
| Climate Zone | % Severe Events |
|---|---|
| Southern Peninsular Region | 26.95% |
| Himalayan Region | 26.67% |
| Western Coastal Region | 26.04% |
| Central Plateau Region | 25.31% |
| Western Ghats Region | 24.77% |
| Indo-Gangetic Plains | 24.68% |
| North-East Region | 24.40% |
| Eastern Coastal Region | 23.96% |
| Thar Desert Region | 23.84% |

### 3. Prediction Accuracy by Month
| Month | Accuracy |
|---|---|
| Month 1 | 96.30% |
| Month 2 | 97.31% |
| Month 3 | 97.14% |
| Month 4 | 97.14% |
| Month 5 | 95.29% |
| Month 6 | 91.75% |
| Month 7 | 95.45% |
| Month 8 | 94.78% |
| Month 9 | 93.60% |
| Month 10 | 98.48% |
| Month 11 | 97.31% |
| Month 12 | 94.95% |

---

## Severity Regression Model (`LightGBM`)
A continuous estimator was trained on the continuous score `extreme_rainfall_score` in range `[0, 1]`.

- **Best Regressor**: `LightGBMRegressor`
- **Mean Absolute Error (MAE)**: `0.00194`
- **Root Mean Squared Error (RMSE)**: `0.00312`
- **$R^2$ Score**: `0.9984`

---

## Recommendations & Deployment Guidance
1. **Probability Thresholds**: When deploying for early warnings, utilize probability thresholds instead of hard argmax categories. For instance, trigger alarms if $P(\text{High}) + P(\text{Extreme}) > 0.35$.
2. **Climate Zone Adjustments**: Review prediction margins closely in regions with high topographical variances (e.g. Himalayan and North-East regions) which exhibit lower accuracy.
3. **Data Refresh**: Re-evaluate and retrain features annually as newer climatology baselines become available.

*Model Saved to: `D:\ai-climate-twin-be\ml_research\scripts\..\..\app\ml_services\models\extreme_rainfall.pkl`*
