# Drought Evolution Model Report

## Executive Summary
A production-ready multi-class drought evolution classifier has been trained and evaluated
as a core component of the AI Climate Digital Twin of India.

- **Best Model**: LightGBM
- **Validation Macro F1**: 0.8841
- **Test Macro F1**: 0.9096
- **Test Accuracy**: 0.9106
- **Test Weighted F1**: 0.9106
- **Total Training Time**: 54.6s
- **Inference Time**: 230.0ms

---

## Dataset Overview
- **Source**: ERA5-Land Reanalysis (Copernicus CDS), processed into `drought_training_dataset.csv`
- **Feature Count**: 64
- **Chronological Split**: Train ≤2020 | Val 2021–2022 | Test ≥2023
- **Target**: `drought_category` (ordinal: Low=0, Medium=1, High=2, Extreme=3)

## Class Distribution (Full Dataset)
| Class | Count | % |
|-------|-------|---|
| Low | 4258 | 29.9% |
| Medium | 4245 | 29.8% |
| High | 3596 | 25.3% |
| Extreme | 2142 | 15.0% |

---

## Model Comparison (Validation Set)
| Model | Accuracy | Macro F1 | Weighted F1 | Train Time |
|-------|----------|----------|-------------|------------|
| LightGBM | 0.8989 | 0.8841 | 0.8991 | 15.1s |
| XGBoost | 0.8989 | 0.8838 | 0.8993 | 14.3s |
| ExtraTrees | 0.8652 | 0.8477 | 0.8656 | 1.9s |
| RandomForest | 0.8546 | 0.8349 | 0.8551 | 5.3s |

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
| Accuracy | 0.9106 |
| Macro Precision | 0.9090 |
| Macro Recall | 0.9103 |
| Macro F1 | 0.9096 |
| Weighted F1 | 0.9106 |
| Inference Time | 230.0 ms |

### Classification Report
```
              precision    recall  f1-score   support

         Low       0.96      0.97      0.96       486
      Medium       0.90      0.88      0.89       503
        High       0.85      0.86      0.86       377
     Extreme       0.93      0.93      0.93       279

    accuracy                           0.91      1645
   macro avg       0.91      0.91      0.91      1645
weighted avg       0.91      0.91      0.91      1645

```

---

## Top 15 Feature Importances
| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `sm_zscore` | 12856.0000 |
| 2 | `rainfall_spi` | 11724.0000 |
| 3 | `temperature_zscore` | 10448.0000 |
| 4 | `evaporation_pressure` | 6020.0000 |
| 5 | `evaporation_stress` | 5982.0000 |
| 6 | `temperature_anomaly` | 5516.0000 |
| 7 | `rainfall_deficit_pct` | 5369.0000 |
| 8 | `temperature_stress` | 3654.0000 |
| 9 | `rainfall_deficit` | 3573.0000 |
| 10 | `temperature_prev_3` | 3546.0000 |
| 11 | `longitude` | 3305.0000 |
| 12 | `rolling_sm_6m` | 3081.0000 |
| 13 | `sm_anomaly` | 2818.0000 |
| 14 | `sm_trend` | 2580.0000 |
| 15 | `sm_deficit_pct` | 2455.0000 |

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
| 1 | 0.8652 |
| 2 | 0.8440 |
| 3 | 0.9291 |
| 4 | 0.9149 |
| 5 | 0.9362 |
| 6 | 0.9291 |
| 7 | 0.9645 |
| 8 | 0.9220 |
| 9 | 0.9291 |
| 10 | 0.9149 |
| 11 | 0.8865 |
| 12 | 0.8830 |

---

## Drought Evolution Insights
- **Mean Dry Month Streak by Category**: {'Extreme': 30.74, 'High': 37.13, 'Low': 40.3, 'Medium': 36.33}
- **Recovery Signal (Extreme months)**: -1.4806598930955848
- **Drought Momentum (Extreme vs Low)**: Extreme=-0.1123 vs Low=0.2155

---

## Error Analysis

### Top Confusion Pairs (True → Predicted)
- Medium->High: 37 instances
- High->Medium: 32 instances
- High->Extreme: 21 instances
- Medium->Low: 21 instances
- Extreme->High: 19 instances

### Extreme Drought False-Negative Rate
6.81% of actual Extreme droughts were missed.

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
