# Extreme Rainfall Model Report
## AI Climate Digital Twin of India

## Executive Summary
This report summarizes the training, evaluation, and selection of the final production-ready model for predicting **extreme rainfall events** across 47 Indian cities.

- **Classifier Selected**: `LightGBM`
- **Validation Macro F1**: `0.8811`
- **Test Macro F1**: `0.8827`
- **Test Accuracy**: `0.8997`
- **Test Weighted F1**: `0.9002`
- **Inference Time (batch)**: `44.7 ms`
- **Total Pipeline Execution**: `222.01s`

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
| LightGBM | 0.8892 | 0.8686 | 0.8890 | 2.33s |
| XGBoost | 0.8759 | 0.8582 | 0.8756 | 2.43s |
| RandomForest | 0.8617 | 0.8574 | 0.8621 | 1.08s |
| ExtraTrees | 0.8387 | 0.8341 | 0.8377 | 0.50s |

### Best Hyperparameters (`LightGBM`)
```json
{
  "colsample_bytree": 0.6682096494749166,
  "learning_rate": 0.02520412743882236,
  "n_estimators": 537,
  "num_leaves": 39,
  "subsample": 0.9862528132298237
}
```

---

## Final Performance (Test Set: $\ge$ 2023)
The optimized model was retrained on the combined Train + Validation dataset and evaluated on the holdout 2023–2025 Test dataset.

| Metric | Holdout Test Score |
|---|---|
| **Accuracy** | 89.97% |
| **Macro Precision** | 0.8849 |
| **Macro Recall** | 0.8810 |
| **Macro F1** | 0.8827 |
| **Weighted F1** | 0.9002 |

### Classification Report
```
              precision    recall  f1-score   support

         Low       0.96      0.95      0.95       832
      Medium       0.81      0.85      0.83       398
        High       0.83      0.81      0.82       242
     Extreme       0.95      0.92      0.93       173

    accuracy                           0.90      1645
   macro avg       0.88      0.88      0.88      1645
weighted avg       0.90      0.90      0.90      1645

```

---

## Top 15 Feature Importances
Global Gini/Gain feature importance values for the chosen model.

| Rank | Feature | Importance |
|---|---|---|
| 1 | `er_rainfall_anomaly` | 4711.00000 |
| 2 | `longitude` | 4162.00000 |
| 3 | `soil_moisture` | 3316.00000 |
| 4 | `latitude` | 3101.00000 |
| 5 | `er_rainfall_acceleration` | 3034.00000 |
| 6 | `temperature_prev_3` | 3009.00000 |
| 7 | `er_rainfall_momentum` | 2898.00000 |
| 8 | `er_flood_potential_proxy` | 2624.00000 |
| 9 | `er_rainfall_zscore` | 2474.00000 |
| 10 | `er_soil_saturation` | 2266.00000 |
| 11 | `rainfall_mm` | 2214.00000 |
| 12 | `rolling_temp_6m` | 2160.00000 |
| 13 | `er_zone_rainfall_anomaly` | 2153.00000 |
| 14 | `sro` | 2098.00000 |
| 15 | `er_rainfall_surge` | 2082.00000 |

---

## Error Analysis & Key Diagnostics
A deep dive into the model failures on the holdout Test set.

### 1. Extreme Class Performance
* **Extreme Recall Rate**: 91.91% (True detection rate for Extreme category events)
* **Extreme Miss Rate (False-Negative Rate)**: 8.09% (Unpredicted Extreme events)

### 2. Common Confusion Pairs (True $ightarrow$ Predicted)
These represent the most common category transitions predicted incorrectly:
- **Low->Medium**: 43 occurrences
- **High->Medium**: 36 occurrences
- **Medium->Low**: 34 occurrences
- **Medium->High**: 26 occurrences
- **Extreme->High**: 13 occurrences

### 3. Top 10 Most Confident Misclassifications
These are the cases where the model incorrectly predicted a category with high probability:
| Rank | City | Date | True | Predicted | Prob (Pred) | Prob (True) | Temp (°C) | Rain (mm) |
|---|---|---|---|---|---|---|---|---|
| 1 | Jaipur | 2025-01-01 | **High** | **Medium** | 99.70% | 0.09% | 14.6°C | 0.5mm |
| 2 | Munnar | 2024-10-01 | **High** | **Medium** | 99.32% | 0.10% | 18.5°C | 8.4mm |
| 3 | Kozhikode | 2024-12-01 | **Medium** | **High** | 99.41% | 0.30% | 25.9°C | 4.1mm |
| 4 | Mangalore | 2024-12-01 | **Medium** | **High** | 98.88% | 0.17% | 26.5°C | 4.0mm |
| 5 | Mysore | 2024-10-01 | **Extreme** | **High** | 98.92% | 0.21% | 23.0°C | 6.7mm |
| 6 | Leh | 2025-05-01 | **High** | **Extreme** | 98.76% | 0.38% | 0.7°C | 1.2mm |
| 7 | Munnar | 2025-10-01 | **High** | **Medium** | 99.06% | 0.74% | 18.2°C | 9.4mm |
| 8 | Jodhpur | 2025-08-01 | **Extreme** | **High** | 97.89% | 0.74% | 28.6°C | 4.4mm |
| 9 | Gangtok | 2023-06-01 | **Low** | **Medium** | 98.48% | 1.33% | 20.3°C | 12.3mm |
| 10 | Shillong | 2023-08-01 | **Low** | **Medium** | 98.02% | 1.83% | 22.0°C | 10.6mm |

---

## Climate Zone & Seasonal Diagnostics

### 1. Prediction Accuracy by Climate Zone (Lowest to Highest)
| Climate Zone | Accuracy |
|---|---|
| Western Coastal Region | 85.00% |
| Western Ghats Region | 87.86% |
| Thar Desert Region | 88.00% |
| Himalayan Region | 88.00% |
| Central Plateau Region | 90.20% |
| North-East Region | 90.95% |
| Indo-Gangetic Plains | 91.84% |
| Southern Peninsular Region | 92.38% |
| Eastern Coastal Region | 94.29% |

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
| Month 1 | 93.62% |
| Month 2 | 95.74% |
| Month 3 | 96.45% |
| Month 4 | 97.87% |
| Month 5 | 89.36% |
| Month 6 | 88.65% |
| Month 7 | 88.65% |
| Month 8 | 85.11% |
| Month 9 | 88.65% |
| Month 10 | 85.11% |
| Month 11 | 87.23% |
| Month 12 | 79.79% |

---

## Severity Regression Model (`XGBoost`)
A continuous estimator was trained on the continuous score `extreme_rainfall_score` in range `[0, 1]`.

- **Best Regressor**: `XGBoostRegressor`
- **Mean Absolute Error (MAE)**: `0.00198`
- **Root Mean Squared Error (RMSE)**: `0.00466`
- **$R^2$ Score**: `0.9961`

---

## Recommendations & Deployment Guidance
1. **Probability Thresholds**: When deploying for early warnings, utilize probability thresholds instead of hard argmax categories. For instance, trigger alarms if $P(\text{High}) + P(\text{Extreme}) > 0.35$.
2. **Climate Zone Adjustments**: Review prediction margins closely in regions with high topographical variances (e.g. Himalayan and North-East regions) which exhibit lower accuracy.
3. **Data Refresh**: Re-evaluate and retrain features annually as newer climatology baselines become available.

*Model Saved to: `C:\Users\archi\Downloads\Desktop\Hackathon\Backend\AI-Climate-Twin-BE\ml_research\scripts\..\..\app\ml_services\models\extreme_rainfall.pkl`*
