# Heatwave Model Report
## AI Climate Digital Twin of India

## Executive Summary
This report summarizes the training, evaluation, and selection of the final production-ready model for predicting **heatwaves** across 47 Indian cities.

- **Classifier Selected**: `XGBoost`
- **Validation Macro F1**: `0.8639`
- **Test Macro F1**: `0.8597`
- **Test Accuracy**: `0.8766`
- **Test Weighted F1**: `0.8783`
- **Inference Time (batch)**: `12.3 ms`
- **Total Pipeline Execution**: `108.63s`

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
| XGBoost | 0.8883 | 0.8604 | 0.8877 | 2.32s |
| LightGBM | 0.8892 | 0.8582 | 0.8879 | 1.85s |
| RandomForest | 0.8741 | 0.8487 | 0.8745 | 0.97s |
| ExtraTrees | 0.8449 | 0.8232 | 0.8446 | 0.42s |

### Best Hyperparameters (`XGBoost`)
```json
{
  "colsample_bytree": 0.9768807022739411,
  "learning_rate": 0.06506305742764315,
  "max_depth": 4,
  "n_estimators": 414,
  "subsample": 0.6063865008880857
}
```

---

## Final Performance (Test Set: $\ge$ 2023)
The optimized model was retrained on the combined Train + Validation dataset and evaluated on the holdout 2023–2025 Test dataset.

| Metric | Holdout Test Score |
|---|---|
| **Accuracy** | 87.66% |
| **Macro Precision** | 0.8590 |
| **Macro Recall** | 0.8621 |
| **Macro F1** | 0.8597 |
| **Weighted F1** | 0.8783 |

### Classification Report
```
              precision    recall  f1-score   support

         Low       0.95      0.92      0.94       760
      Medium       0.77      0.82      0.80       379
        High       0.77      0.83      0.80       256
     Extreme       0.94      0.88      0.91       250

    accuracy                           0.88      1645
   macro avg       0.86      0.86      0.86      1645
weighted avg       0.88      0.88      0.88      1645

```

---

## Top 15 Feature Importances
Global Gini/Gain feature importance values for the chosen model.

| Rank | Feature | Importance |
|---|---|---|
| 1 | `hw_heat_stress` | 0.13119 |
| 2 | `hw_compound_heat_drought` | 0.09030 |
| 3 | `hw_temperature_zscore` | 0.07993 |
| 4 | `hw_rainfall_heat_interaction` | 0.05651 |
| 5 | `rainfall_mm` | 0.04243 |
| 6 | `evabs` | 0.04036 |
| 7 | `hw_evaporation_heat_ratio` | 0.03694 |
| 8 | `hw_soil_heat_interaction` | 0.03614 |
| 9 | `hw_temperature_anomaly` | 0.02842 |
| 10 | `month_cos` | 0.02753 |
| 11 | `hw_apparent_temp_anomaly` | 0.02520 |
| 12 | `sro` | 0.02355 |
| 13 | `rolling_rainfall_6m` | 0.02337 |
| 14 | `rainfall_prev_3` | 0.02335 |
| 15 | `latitude` | 0.02120 |

---

## Error Analysis & Key Diagnostics
A deep dive into the model failures on the holdout Test set.

### 1. Extreme Class Performance
* **Extreme Recall Rate**: 87.60% (True detection rate for Extreme category events)
* **Extreme Miss Rate (False-Negative Rate)**: 12.40% (Unpredicted Extreme events)

### 2. Common Confusion Pairs (True $ightarrow$ Predicted)
These represent the most common category transitions predicted incorrectly:
- **Low->Medium**: 61 occurrences
- **Medium->High**: 35 occurrences
- **Medium->Low**: 33 occurrences
- **Extreme->High**: 29 occurrences
- **High->Medium**: 28 occurrences

### 3. Top 10 Most Confident Misclassifications
These are the cases where the model incorrectly predicted a category with high probability:
| Rank | City | Date | True | Predicted | Prob (Pred) | Prob (True) | Temp (°C) | Rain (mm) |
|---|---|---|---|---|---|---|---|---|
| 1 | Shimla | 2024-12-01 | **Medium** | **Low** | 97.70% | 2.26% | 6.2°C | 1.7mm |
| 2 | Bhopal | 2024-06-01 | **Low** | **Medium** | 97.33% | 2.40% | 31.1°C | 4.8mm |
| 3 | Amritsar | 2024-01-01 | **Medium** | **Low** | 97.33% | 2.66% | 9.7°C | 0.2mm |
| 4 | Jodhpur | 2023-08-01 | **High** | **Medium** | 93.91% | 0.75% | 28.1°C | 0.4mm |
| 5 | Thiruvananthapuram | 2025-02-01 | **Extreme** | **High** | 93.89% | 2.97% | 26.4°C | 0.2mm |
| 6 | Thiruvananthapuram | 2023-03-01 | **Extreme** | **High** | 92.67% | 3.30% | 27.1°C | 0.8mm |
| 7 | Chandigarh | 2024-01-01 | **Medium** | **Low** | 93.68% | 6.32% | 11.2°C | 0.1mm |
| 8 | Jabalpur | 2024-01-01 | **Low** | **Medium** | 92.11% | 5.38% | 17.9°C | 0.1mm |
| 9 | Aizawl | 2024-06-01 | **Medium** | **High** | 91.36% | 5.07% | 25.4°C | 7.4mm |
| 10 | Bhopal | 2023-10-01 | **High** | **Medium** | 92.89% | 6.82% | 24.9°C | 0.0mm |

---

## Climate Zone & Seasonal Diagnostics

### 1. Prediction Accuracy by Climate Zone (Lowest to Highest)
| Climate Zone | Accuracy |
|---|---|
| Himalayan Region | 81.71% |
| Western Ghats Region | 84.29% |
| North-East Region | 85.24% |
| Western Coastal Region | 86.43% |
| Eastern Coastal Region | 88.57% |
| Central Plateau Region | 88.57% |
| Indo-Gangetic Plains | 89.80% |
| Southern Peninsular Region | 90.48% |
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
| Month 1 | 82.98% |
| Month 2 | 83.69% |
| Month 3 | 88.65% |
| Month 4 | 88.65% |
| Month 5 | 94.33% |
| Month 6 | 88.65% |
| Month 7 | 87.23% |
| Month 8 | 90.78% |
| Month 9 | 84.40% |
| Month 10 | 89.36% |
| Month 11 | 88.65% |
| Month 12 | 82.98% |

---

## Severity Regression Model (`LightGBM`)
A continuous estimator was trained on the continuous score `heatwave_severity_score` in range `[0, 1]`.

- **Best Regressor**: `LightGBMRegressor`
- **Mean Absolute Error (MAE)**: `0.00640`
- **Root Mean Squared Error (RMSE)**: `0.01026`
- **$R^2$ Score**: `0.9850`

---

## Recommendations & Deployment Guidance
1. **Probability Thresholds**: When deploying for early warnings, utilize probability thresholds instead of hard argmax categories. For instance, trigger alarms if $P(\text{High}) + P(\text{Extreme}) > 0.35$.
2. **Climate Zone Adjustments**: Review prediction margins closely in regions with high topographical variances (e.g. Himalayan and North-East regions) which exhibit lower accuracy.
3. **Data Refresh**: Re-evaluate and retrain features annually as newer climatology baselines become available.

*Model Saved to: `C:\Users\archi\Downloads\Desktop\Hackathon\Backend\AI-Climate-Twin-BE\ml_research\scripts\..\..\app\ml_services\models\heatwave.pkl`*
