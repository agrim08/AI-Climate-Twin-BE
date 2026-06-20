# Heatwave Model Report
## AI Climate Digital Twin of India

## Executive Summary
This report summarizes the training, evaluation, and selection of the final production-ready model for predicting **heatwaves** across 47 Indian cities.

- **Classifier Selected**: `XGBoost`
- **Validation Macro F1**: `0.8636`
- **Test Macro F1**: `0.8604`
- **Test Accuracy**: `0.8772`
- **Test Weighted F1**: `0.8788`
- **Inference Time (batch)**: `24.7 ms`
- **Total Pipeline Execution**: `94.94s`

---

## Dataset Overview & Target Class Distribution
- **Dataset Size**: 14,382 rows (chronologically split)
- **Feature Set size**: 40 variables (fully isolated to prevent leakage)
- **Target Variable**: `heatwave_category`

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
| XGBoost | 0.8892 | 0.8607 | 0.8888 | 4.06s |
| LightGBM | 0.8927 | 0.8603 | 0.8920 | 3.90s |
| RandomForest | 0.8785 | 0.8512 | 0.8778 | 2.31s |
| ExtraTrees | 0.8457 | 0.8246 | 0.8449 | 0.72s |

### Best Hyperparameters (`XGBoost`)
```json
{
  "colsample_bytree": 0.7246844304357644,
  "learning_rate": 0.06160544169422487,
  "max_depth": 4,
  "n_estimators": 409,
  "subsample": 0.6739417822102108
}
```

---

## Final Performance (Test Set: $\ge$ 2023)
The optimized model was retrained on the combined Train + Validation dataset and evaluated on the holdout 2023–2025 Test dataset.

| Metric | Holdout Test Score |
|---|---|
| **Accuracy** | 87.72% |
| **Macro Precision** | 0.8586 |
| **Macro Recall** | 0.8634 |
| **Macro F1** | 0.8604 |
| **Weighted F1** | 0.8788 |

### Classification Report
```
              precision    recall  f1-score   support

         Low       0.95      0.92      0.94       760
      Medium       0.78      0.82      0.80       379
        High       0.77      0.83      0.80       256
     Extreme       0.93      0.88      0.90       250

    accuracy                           0.88      1645
   macro avg       0.86      0.86      0.86      1645
weighted avg       0.88      0.88      0.88      1645

```

---

## Top 15 Feature Importances
Global Gini/Gain feature importance values for the chosen model.

| Rank | Feature | Importance |
|---|---|---|
| 1 | `hw_heat_stress` | 0.11608 |
| 2 | `hw_rainfall_heat_interaction` | 0.08734 |
| 3 | `hw_compound_heat_drought` | 0.07918 |
| 4 | `hw_temperature_zscore` | 0.07519 |
| 5 | `hw_soil_heat_interaction` | 0.04341 |
| 6 | `evabs` | 0.03929 |
| 7 | `rainfall_mm` | 0.03860 |
| 8 | `hw_temperature_anomaly` | 0.03379 |
| 9 | `hw_evaporation_heat_ratio` | 0.03188 |
| 10 | `sro` | 0.02876 |
| 11 | `month_cos` | 0.02856 |
| 12 | `rainfall_prev_3` | 0.02544 |
| 13 | `rolling_rainfall_6m` | 0.02520 |
| 14 | `hw_apparent_temp_anomaly` | 0.02280 |
| 15 | `latitude` | 0.02069 |

---

## Error Analysis & Key Diagnostics
A deep dive into the model failures on the holdout Test set.

### 1. Extreme Class Performance
* **Extreme Recall Rate**: 88.00% (True detection rate for Extreme category events)
* **Extreme Miss Rate (False-Negative Rate)**: 12.00% (Unpredicted Extreme events)

### 2. Common Confusion Pairs (True $ightarrow$ Predicted)
These represent the most common category transitions predicted incorrectly:
- **Low->Medium**: 62 occurrences
- **Medium->High**: 34 occurrences
- **Medium->Low**: 32 occurrences
- **Extreme->High**: 28 occurrences
- **High->Medium**: 25 occurrences

### 3. Top 10 Most Confident Misclassifications
These are the cases where the model incorrectly predicted a category with high probability:
| Rank | City | Date | True | Predicted | Prob (Pred) | Prob (True) | Temp (°C) | Rain (mm) |
|---|---|---|---|---|---|---|---|---|
| 1 | Bhopal | 2024-06-01 | **Low** | **Medium** | 97.13% | 2.53% | 31.1°C | 4.8mm |
| 2 | Amritsar | 2024-01-01 | **Medium** | **Low** | 97.30% | 2.69% | 9.7°C | 0.2mm |
| 3 | Jodhpur | 2023-08-01 | **High** | **Medium** | 93.57% | 0.57% | 28.1°C | 0.4mm |
| 4 | Shimla | 2024-12-01 | **Medium** | **Low** | 96.38% | 3.57% | 6.2°C | 1.7mm |
| 5 | Thiruvananthapuram | 2025-02-01 | **Extreme** | **High** | 93.24% | 2.34% | 26.4°C | 0.2mm |
| 6 | Chandigarh | 2024-01-01 | **Medium** | **Low** | 95.27% | 4.72% | 11.2°C | 0.1mm |
| 7 | Thiruvananthapuram | 2023-03-01 | **Extreme** | **High** | 90.96% | 3.78% | 27.1°C | 0.8mm |
| 8 | Guwahati | 2023-08-01 | **High** | **Medium** | 91.08% | 4.32% | 27.4°C | 10.6mm |
| 9 | Gangtok | 2023-05-01 | **Medium** | **Low** | 93.15% | 6.48% | 17.9°C | 6.7mm |
| 10 | Jabalpur | 2024-01-01 | **Low** | **Medium** | 91.11% | 6.21% | 17.9°C | 0.1mm |

---

## Climate Zone & Seasonal Diagnostics

### 1. Prediction Accuracy by Climate Zone (Lowest to Highest)
| Climate Zone | Accuracy |
|---|---|
| Himalayan Region | 81.14% |
| Western Ghats Region | 83.57% |
| North-East Region | 86.19% |
| Western Coastal Region | 87.14% |
| Indo-Gangetic Plains | 87.76% |
| Central Plateau Region | 89.39% |
| Eastern Coastal Region | 90.48% |
| Southern Peninsular Region | 90.95% |
| Thar Desert Region | 92.00% |

### 2. Event Proneness by Climate Zone (% High + Extreme)
| Climate Zone | % Severe Events |
|---|---|
| North-East Region | 47.14% |
| Western Coastal Region | 38.57% |
| Himalayan Region | 36.57% |
| Eastern Coastal Region | 34.29% |
| Western Ghats Region | 33.57% |
| Thar Desert Region | 26.29% |
| Indo-Gangetic Plains | 25.31% |
| Southern Peninsular Region | 25.24% |
| Central Plateau Region | 18.37% |

### 3. Prediction Accuracy by Month
| Month | Accuracy |
|---|---|
| Month 1 | 86.52% |
| Month 2 | 87.94% |
| Month 3 | 88.65% |
| Month 4 | 87.23% |
| Month 5 | 95.04% |
| Month 6 | 88.65% |
| Month 7 | 85.11% |
| Month 8 | 90.78% |
| Month 9 | 81.56% |
| Month 10 | 87.94% |
| Month 11 | 87.94% |
| Month 12 | 84.04% |

---

## Severity Regression Model (`LightGBM`)
A continuous estimator was trained on the continuous score `heatwave_severity_score` in range `[0, 1]`.

- **Best Regressor**: `LightGBMRegressor`
- **Mean Absolute Error (MAE)**: `0.00641`
- **Root Mean Squared Error (RMSE)**: `0.01030`
- **$R^2$ Score**: `0.9848`

---

## Recommendations & Deployment Guidance
1. **Probability Thresholds**: When deploying for early warnings, utilize probability thresholds instead of hard argmax categories. For instance, trigger alarms if $P(\text{High}) + P(\text{Extreme}) > 0.35$.
2. **Climate Zone Adjustments**: Review prediction margins closely in regions with high topographical variances (e.g. Himalayan and North-East regions) which exhibit lower accuracy.
3. **Data Refresh**: Re-evaluate and retrain features annually as newer climatology baselines become available.

*Model Saved to: `D:\ai-climate-twin-be\ml_research\scripts\..\..\app\ml_services\models\heatwave.pkl`*
