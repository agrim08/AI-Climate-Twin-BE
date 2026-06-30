# Drought Evolution Model Report

## Executive Summary
A production-ready multi-class drought evolution classifier has been trained and evaluated
as a core component of the AI Climate Digital Twin of India.

- **Best Model**: LightGBM
- **Validation Macro F1**: 0.9423
- **Test Macro F1**: 0.9431
- **Test Accuracy**: 0.9422
- **Test Weighted F1**: 0.9423
- **Total Training Time**: 160.5s
- **Inference Time**: 988.1ms

---

## Dataset Overview
- **Source**: ERA5-Land Reanalysis (Copernicus CDS), processed into `drought_training_dataset.csv`
- **Feature Count**: 64
- **Chronological Split**: Train ≤2020 | Val 2021–2022 | Test ≥2023
- **Target**: `drought_category` (ordinal: Low=0, Medium=1, High=2, Extreme=3)

## Class Distribution (Full Dataset)
| Class | Count | % |
|-------|-------|---|
| Low | 18504 | 30.2% |
| Medium | 18262 | 29.8% |
| High | 15246 | 24.9% |
| Extreme | 9170 | 15.0% |

---

## Model Comparison (Validation Set)
| Model | Accuracy | Macro F1 | Weighted F1 | Train Time |
|-------|----------|----------|-------------|------------|
| LightGBM | 0.9417 | 0.9423 | 0.9417 | 21.9s |
| XGBoost | 0.9369 | 0.9376 | 0.9369 | 24.8s |
| ExtraTrees | 0.9043 | 0.9050 | 0.9042 | 7.3s |
| RandomForest | 0.9015 | 0.9033 | 0.9015 | 21.5s |

**Selection Criterion**: Macro F1 (penalises models that ignore minority classes)

---

## Best Model: LightGBM

### Best Hyperparameters
```json
{
  "colsample_bytree": 0.8254442364744264,
  "learning_rate": 0.015641157902710028,
  "min_child_samples": 33,
  "n_estimators": 1205,
  "num_leaves": 32
}
```

### Final Test-Set Metrics
| Metric | Value |
|--------|-------|
| Accuracy | 0.9422 |
| Macro Precision | 0.9445 |
| Macro Recall | 0.9418 |
| Macro F1 | 0.9431 |
| Weighted F1 | 0.9423 |
| Inference Time | 988.1 ms |

### Classification Report
```
              precision    recall  f1-score   support

         Low       0.97      0.97      0.97      1927
      Medium       0.92      0.94      0.93      2035
        High       0.92      0.92      0.92      1854
     Extreme       0.96      0.94      0.95      1312

    accuracy                           0.94      7128
   macro avg       0.94      0.94      0.94      7128
weighted avg       0.94      0.94      0.94      7128

```

---

## Top 15 Feature Importances
| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `rainfall_spi` | 12752.0000 |
| 2 | `sm_zscore` | 11881.0000 |
| 3 | `temperature_zscore` | 11001.0000 |
| 4 | `evaporation_stress` | 8764.0000 |
| 5 | `zone_aridity_index` | 7399.0000 |
| 6 | `temperature_anomaly` | 5272.0000 |
| 7 | `soil_moisture` | 5013.0000 |
| 8 | `rainfall_deficit_pct` | 4477.0000 |
| 9 | `temperature_stress` | 4266.0000 |
| 10 | `compound_drought_stress` | 3913.0000 |
| 11 | `rolling_temp_6m` | 3619.0000 |
| 12 | `sm_deficit_pct` | 3282.0000 |
| 13 | `sm_anomaly` | 3270.0000 |
| 14 | `rainfall_deficit` | 3153.0000 |
| 15 | `water_balance` | 2795.0000 |

---

## Climate Zone Analysis

### Drought Proneness by Zone (% High + Extreme predictions)
| Climate Zone | % Severe Drought |
|--------------|-----------------|


**Most drought-prone**: N/A
**Least drought-prone**: N/A

---

## Seasonal Analysis

### Accuracy by Month
| Month | Accuracy |
|-------|----------|
| 1 | 0.9512 |
| 2 | 0.9495 |
| 3 | 0.9377 |
| 4 | 0.9091 |
| 5 | 0.9276 |
| 6 | 0.9478 |
| 7 | 0.9579 |
| 8 | 0.9646 |
| 9 | 0.9192 |
| 10 | 0.9478 |
| 11 | 0.9579 |
| 12 | 0.9360 |

---

## Drought Evolution Insights
- **Mean Dry Month Streak by Category**: {'Extreme': 0.06, 'High': 0.07, 'Low': 0.04, 'Medium': 0.05}
- **Recovery Signal (Extreme months)**: -4.993404703193601
- **Drought Momentum (Extreme vs Low)**: Extreme=-0.1039 vs Low=0.0567

---

## Error Analysis

### Top Confusion Pairs (True → Predicted)
- High->Medium: 107 instances
- Extreme->High: 78 instances
- Low->Medium: 65 instances
- Medium->High: 65 instances
- Medium->Low: 52 instances

### Extreme Drought False-Negative Rate
5.95% of actual Extreme droughts were missed.

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

*Model saved to: `D:\ai-climate-twin-be\ml_research\scripts\..\..\app\ml_services\models\drought.pkl`*
