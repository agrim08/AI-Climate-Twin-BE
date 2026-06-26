# Extreme Rainfall Model Report
## AI Climate Digital Twin of India

## Executive Summary
This report summarizes the training, evaluation, and selection of the final production-ready model for predicting **extreme rainfall events** across 47 Indian cities.

- **Classifier Selected**: `LightGBM`
- **Validation Macro F1**: `0.8690`
- **Test Macro F1**: `0.8778`
- **Test Accuracy**: `0.8936`
- **Test Weighted F1**: `0.8948`
- **Inference Time (batch)**: `72.1 ms`
- **Total Pipeline Execution**: `414.64s`

---

## Dataset Overview & Target Class Distribution
- **Dataset Size**: 14,382 rows (chronologically split)
- **Feature Set size**: 45 variables (fully isolated to prevent leakage)
- **Target Variable**: `extreme_rainfall_category`

### Class Frequencies
| Category | Row Count | Percentage |
|---|---|---|
| Low | 7,191 | 50.00% |
| Medium | 3,572 | 24.84% |
| High | 2,162 | 15.03% |
| Extreme | 1,457 | 10.13% |

---

## Model Comparison (Validation Set)
Candidate models were evaluated using chronological splitting (train $\le$ 2020, validation 2021-2022). The primary ranking metric is **Macro F1** to ensure strong predictive performance on rare extreme events.

| Model | Accuracy | Macro F1 | Weighted F1 | Training Time |
|---|---|---|---|---|
| LightGBM | 0.8945 | 0.8730 | 0.8942 | 5.98s |
| XGBoost | 0.8741 | 0.8562 | 0.8737 | 4.99s |
| RandomForest | 0.8528 | 0.8440 | 0.8519 | 1.96s |
| ExtraTrees | 0.8351 | 0.8308 | 0.8342 | 0.74s |

### Best Hyperparameters (`LightGBM`)
```json
{
  "colsample_bytree": 0.7564242430292963,
  "learning_rate": 0.034578887023044985,
  "n_estimators": 537,
  "num_leaves": 16,
  "subsample": 0.7700623497964979
}
```

---

## Final Performance (Test Set: $\ge$ 2023)
The optimized model was retrained on the combined Train + Validation dataset and evaluated on the holdout 2023–2025 Test dataset.

| Metric | Holdout Test Score |
|---|---|
| **Accuracy** | 89.36% |
| **Macro Precision** | 0.8793 |
| **Macro Recall** | 0.8770 |
| **Macro F1** | 0.8778 |
| **Weighted F1** | 0.8948 |

### Classification Report
```
              precision    recall  f1-score   support

         Low       0.96      0.94      0.95       832
      Medium       0.79      0.84      0.81       398
        High       0.80      0.82      0.81       242
     Extreme       0.96      0.91      0.94       173

    accuracy                           0.89      1645
   macro avg       0.88      0.88      0.88      1645
weighted avg       0.90      0.89      0.89      1645

```

---

## Top 15 Feature Importances
Global Gini/Gain feature importance values for the chosen model.

| Rank | Feature | Importance |
|---|---|---|
| 1 | `er_rainfall_anomaly` | 2230.00000 |
| 2 | `longitude` | 2009.00000 |
| 3 | `latitude` | 1457.00000 |
| 4 | `soil_moisture` | 1343.00000 |
| 5 | `er_rainfall_momentum` | 1318.00000 |
| 6 | `temperature_prev_3` | 1274.00000 |
| 7 | `er_rainfall_acceleration` | 1260.00000 |
| 8 | `er_flood_potential_proxy` | 1115.00000 |
| 9 | `rainfall_mm` | 935.00000 |
| 10 | `er_soil_saturation` | 908.00000 |
| 11 | `rolling_temp_6m` | 877.00000 |
| 12 | `er_rainfall_zscore` | 869.00000 |
| 13 | `er_evaporation_demand_ratio` | 866.00000 |
| 14 | `sro` | 854.00000 |
| 15 | `er_zone_rainfall_anomaly` | 830.00000 |

---

## Error Analysis & Key Diagnostics
A deep dive into the model failures on the holdout Test set.

### 1. Extreme Class Performance
* **Extreme Recall Rate**: 91.33% (True detection rate for Extreme category events)
* **Extreme Miss Rate (False-Negative Rate)**: 8.67% (Unpredicted Extreme events)

### 2. Common Confusion Pairs (True $ightarrow$ Predicted)
These represent the most common category transitions predicted incorrectly:
- **Low->Medium**: 50 occurrences
- **High->Medium**: 37 occurrences
- **Medium->High**: 33 occurrences
- **Medium->Low**: 31 occurrences
- **Extreme->High**: 14 occurrences

### 3. Top 10 Most Confident Misclassifications
These are the cases where the model incorrectly predicted a category with high probability:
| Rank | City | Date | True | Predicted | Prob (Pred) | Prob (True) | Temp (°C) | Rain (mm) |
|---|---|---|---|---|---|---|---|---|
| 1 | Jaipur | 2025-01-01 | **High** | **Medium** | 99.15% | 0.27% | 14.6°C | 0.5mm |
| 2 | Kozhikode | 2024-12-01 | **Medium** | **High** | 98.93% | 0.55% | 25.9°C | 4.1mm |
| 3 | Munnar | 2024-10-01 | **High** | **Medium** | 98.09% | 0.20% | 18.5°C | 8.4mm |
| 4 | Mangalore | 2024-12-01 | **Medium** | **High** | 98.32% | 0.44% | 26.5°C | 4.0mm |
| 5 | Munnar | 2025-10-01 | **High** | **Medium** | 98.01% | 1.51% | 18.2°C | 9.4mm |
| 6 | Gangtok | 2023-06-01 | **Low** | **Medium** | 97.84% | 1.92% | 20.3°C | 12.3mm |
| 7 | Leh | 2025-05-01 | **High** | **Extreme** | 96.39% | 1.46% | 0.7°C | 1.2mm |
| 8 | Mysore | 2024-10-01 | **Extreme** | **High** | 96.20% | 1.92% | 23.0°C | 6.7mm |
| 9 | Shillong | 2023-08-01 | **Low** | **Medium** | 96.84% | 2.96% | 22.0°C | 10.6mm |
| 10 | Leh | 2024-04-01 | **High** | **Extreme** | 93.53% | 1.53% | -10.2°C | 0.7mm |

---

## Climate Zone & Seasonal Diagnostics

### 1. Prediction Accuracy by Climate Zone (Lowest to Highest)
| Climate Zone | Accuracy |
|---|---|
| Western Coastal Region | 85.71% |
| Himalayan Region | 86.29% |
| Western Ghats Region | 86.43% |
| Thar Desert Region | 88.00% |
| Central Plateau Region | 89.80% |
| Southern Peninsular Region | 90.48% |
| North-East Region | 91.43% |
| Indo-Gangetic Plains | 91.43% |
| Eastern Coastal Region | 93.33% |

### 2. Event Proneness by Climate Zone (% High + Extreme)
| Climate Zone | % Severe Events |
|---|---|
| Southern Peninsular Region | 29.05% |
| Central Plateau Region | 28.57% |
| Himalayan Region | 28.00% |
| Thar Desert Region | 28.00% |
| Western Coastal Region | 24.29% |
| Western Ghats Region | 24.29% |
| Indo-Gangetic Plains | 22.04% |
| Eastern Coastal Region | 21.90% |
| North-East Region | 19.52% |

### 3. Prediction Accuracy by Month
| Month | Accuracy |
|---|---|
| Month 1 | 95.74% |
| Month 2 | 95.74% |
| Month 3 | 95.04% |
| Month 4 | 97.87% |
| Month 5 | 90.07% |
| Month 6 | 87.94% |
| Month 7 | 87.23% |
| Month 8 | 83.69% |
| Month 9 | 84.40% |
| Month 10 | 84.40% |
| Month 11 | 86.52% |
| Month 12 | 80.85% |

---

## Severity Regression Model (`XGBoost`)
A continuous estimator was trained on the continuous score `extreme_rainfall_score` in range `[0, 1]`.

- **Best Regressor**: `XGBoostRegressor`
- **Mean Absolute Error (MAE)**: `0.00194`
- **Root Mean Squared Error (RMSE)**: `0.00457`
- **$R^2$ Score**: `0.9962`

---

## Recommendations & Deployment Guidance
1. **Probability Thresholds**: When deploying for early warnings, utilize probability thresholds instead of hard argmax categories. For instance, trigger alarms if $P(\text{High}) + P(\text{Extreme}) > 0.35$.
2. **Climate Zone Adjustments**: Review prediction margins closely in regions with high topographical variances (e.g. Himalayan and North-East regions) which exhibit lower accuracy.
3. **Data Refresh**: Re-evaluate and retrain features annually as newer climatology baselines become available.

*Model Saved to: `D:\ai-climate-twin-be\ml_research\scripts\..\..\app\ml_services\models\extreme_rainfall.pkl`*
