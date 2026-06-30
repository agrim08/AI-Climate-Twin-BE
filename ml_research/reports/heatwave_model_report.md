# Heatwave Model Report
## AI Climate Digital Twin of India

## Executive Summary
This report summarizes the training, evaluation, and selection of the final production-ready model for predicting **heatwaves** across 47 Indian cities.

- **Classifier Selected**: `LightGBM`
- **Validation Macro F1**: `0.8839`
- **Test Macro F1**: `0.8868`
- **Test Accuracy**: `0.8913`
- **Test Weighted F1**: `0.8918`
- **Inference Time (batch)**: `370.8 ms`
- **Total Pipeline Execution**: `438.38s`

---

## Dataset Overview & Target Class Distribution
- **Dataset Size**: 61,776 rows (chronologically split)
- **Feature Set size**: 40 variables (fully isolated to prevent leakage)
- **Target Variable**: `heatwave_category`

### Class Frequencies
| Category | Row Count | Percentage |
|---|---|---|
| Low | 30,898 | 50.02% |
| Medium | 15,436 | 24.99% |
| High | 9,106 | 14.74% |
| Extreme | 6,336 | 10.26% |

---

## Model Comparison (Validation Set)
Candidate models were evaluated using chronological splitting (train $\le$ 2020, validation 2021-2022). The primary ranking metric is **Macro F1** to ensure strong predictive performance on rare extreme events.

| Model | Accuracy | Macro F1 | Weighted F1 | Training Time |
|---|---|---|---|---|
| LightGBM | 0.8822 | 0.8776 | 0.8836 | 44.21s |
| XGBoost | 0.8672 | 0.8636 | 0.8684 | 10.30s |
| RandomForest | 0.8439 | 0.8417 | 0.8461 | 8.25s |
| ExtraTrees | 0.7508 | 0.7440 | 0.7533 | 1.95s |

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
| **Accuracy** | 89.13% |
| **Macro Precision** | 0.8863 |
| **Macro Recall** | 0.8879 |
| **Macro F1** | 0.8868 |
| **Weighted F1** | 0.8918 |

### Classification Report
```
              precision    recall  f1-score   support

         Low       0.95      0.92      0.93      2687
      Medium       0.81      0.86      0.83      1741
        High       0.86      0.84      0.85      1379
     Extreme       0.93      0.94      0.93      1321

    accuracy                           0.89      7128
   macro avg       0.89      0.89      0.89      7128
weighted avg       0.89      0.89      0.89      7128

```

---

## Top 15 Feature Importances
Global Gini/Gain feature importance values for the chosen model.

| Rank | Feature | Importance |
|---|---|---|
| 1 | `hw_rainfall_heat_interaction` | 6616.00000 |
| 2 | `hw_heat_stress` | 6042.00000 |
| 3 | `soil_moisture` | 5365.00000 |
| 4 | `rainfall_mm` | 4861.00000 |
| 5 | `sro` | 4705.00000 |
| 6 | `hw_temperature_anomaly` | 4259.00000 |
| 7 | `hw_compound_heat_drought` | 3909.00000 |
| 8 | `latitude` | 3409.00000 |
| 9 | `hw_rolling_temp_trend_3m` | 3389.00000 |
| 10 | `longitude` | 3274.00000 |
| 11 | `hw_soil_heat_interaction` | 3136.00000 |
| 12 | `hw_temperature_zscore` | 2946.00000 |
| 13 | `hw_heatwave_intensity` | 2899.00000 |
| 14 | `hw_heat_acceleration` | 2842.00000 |
| 15 | `soil_moisture_prev_1` | 2782.00000 |

---

## Error Analysis & Key Diagnostics
A deep dive into the model failures on the holdout Test set.

### 1. Extreme Class Performance
* **Extreme Recall Rate**: 94.10% (True detection rate for Extreme category events)
* **Extreme Miss Rate (False-Negative Rate)**: 5.90% (Unpredicted Extreme events)

### 2. Common Confusion Pairs (True $ightarrow$ Predicted)
These represent the most common category transitions predicted incorrectly:
- **Low->Medium**: 223 occurrences
- **Medium->Low**: 142 occurrences
- **High->Medium**: 130 occurrences
- **Medium->High**: 107 occurrences
- **High->Extreme**: 95 occurrences

### 3. Top 10 Most Confident Misclassifications
These are the cases where the model incorrectly predicted a category with high probability:
| Rank | City | Date | True | Predicted | Prob (Pred) | Prob (True) | Temp (°C) | Rain (mm) |
|---|---|---|---|---|---|---|---|---|
| 1 | Barmer | 2025-12-01 | **Low** | **Medium** | 99.86% | 0.01% | 12.1°C | 9.8mm |
| 2 | Hubballi | 2023-11-01 | **High** | **Extreme** | 99.47% | 0.53% | 16.2°C | 17.2mm |
| 3 | Jalandhar | 2024-01-01 | **Medium** | **High** | 99.05% | 0.84% | 16.0°C | 20.0mm |
| 4 | Gokarna | 2025-06-01 | **High** | **Extreme** | 98.98% | 0.96% | 39.5°C | 469.4mm |
| 5 | Jalandhar | 2024-03-01 | **High** | **Extreme** | 98.92% | 1.08% | 31.7°C | 24.0mm |
| 6 | Bokaro | 2025-01-01 | **High** | **Extreme** | 98.90% | 1.10% | 22.9°C | 20.0mm |
| 7 | Dharamshala | 2025-08-01 | **Extreme** | **High** | 98.84% | 1.07% | 16.5°C | 162.5mm |
| 8 | Allahabad | 2025-02-01 | **High** | **Extreme** | 98.79% | 1.21% | 23.4°C | 20.0mm |
| 9 | Barmer | 2023-01-01 | **High** | **Extreme** | 98.50% | 1.50% | 18.2°C | 6.6mm |
| 10 | Gulmarg | 2025-10-01 | **High** | **Extreme** | 98.46% | 1.54% | 8.1°C | 50.0mm |

---

## Climate Zone & Seasonal Diagnostics

### 1. Prediction Accuracy by Climate Zone (Lowest to Highest)
| Climate Zone | Accuracy |
|---|---|
| Thar Desert Region | 83.80% |
| Himalayan Region | 86.11% |
| Western Ghats Region | 88.66% |
| North-East Region | 89.48% |
| Indo-Gangetic Plains | 89.52% |
| Central Plateau Region | 89.74% |
| Southern Peninsular Region | 89.78% |
| Western Coastal Region | 89.93% |
| Eastern Coastal Region | 90.10% |

### 2. Event Proneness by Climate Zone (% High + Extreme)
| Climate Zone | % Severe Events |
|---|---|
| Himalayan Region | 41.67% |
| North-East Region | 40.87% |
| Thar Desert Region | 40.51% |
| Western Ghats Region | 40.28% |
| Eastern Coastal Region | 38.54% |
| Western Coastal Region | 38.19% |
| Indo-Gangetic Plains | 37.86% |
| Southern Peninsular Region | 37.47% |
| Central Plateau Region | 34.10% |

### 3. Prediction Accuracy by Month
| Month | Accuracy |
|---|---|
| Month 1 | 85.86% |
| Month 2 | 86.20% |
| Month 3 | 88.55% |
| Month 4 | 89.56% |
| Month 5 | 89.56% |
| Month 6 | 92.42% |
| Month 7 | 91.08% |
| Month 8 | 91.25% |
| Month 9 | 87.54% |
| Month 10 | 88.72% |
| Month 11 | 88.89% |
| Month 12 | 89.90% |

---

## Severity Regression Model (`LightGBM`)
A continuous estimator was trained on the continuous score `heatwave_severity_score` in range `[0, 1]`.

- **Best Regressor**: `LightGBMRegressor`
- **Mean Absolute Error (MAE)**: `0.01113`
- **Root Mean Squared Error (RMSE)**: `0.01555`
- **$R^2$ Score**: `0.9820`

---

## Recommendations & Deployment Guidance
1. **Probability Thresholds**: When deploying for early warnings, utilize probability thresholds instead of hard argmax categories. For instance, trigger alarms if $P(\text{High}) + P(\text{Extreme}) > 0.35$.
2. **Climate Zone Adjustments**: Review prediction margins closely in regions with high topographical variances (e.g. Himalayan and North-East regions) which exhibit lower accuracy.
3. **Data Refresh**: Re-evaluate and retrain features annually as newer climatology baselines become available.

*Model Saved to: `D:\ai-climate-twin-be\ml_research\scripts\..\..\app\ml_services\models\heatwave.pkl`*
