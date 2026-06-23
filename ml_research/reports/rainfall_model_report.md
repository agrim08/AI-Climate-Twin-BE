# Rainfall Prediction Model — Final Report

## Executive Summary
A production-ready **Climate State Rainfall Model** has been successfully trained
and selected for the AI Climate Digital Twin of India.

- **Best Model**: LightGBM
- **Test R²**: 0.9697
- **Test RMSE**: 0.9756 mm
- **Test MAE**: 0.502 mm
- **Test MAPE**: 154.2833%

---

## Dataset Overview
| Property | Value |
|----------|-------|
| Train rows | 11,515 (year ≤ 2020) |
| Validation rows | 1,128 (2021–2022) |
| Test rows | 1,645 (year ≥ 2023) |
| Features used | 56 |
| Target | `rainfall_mm` |

---

## Features Used
```
latitude, longitude, year, month, temperature_c, soil_moisture, evabs, sro, month_sin, month_cos, temperature_prev_1, temperature_prev_3, rainfall_prev_1, rainfall_prev_3, soil_moisture_prev_1, rolling_temp_3m, rolling_rainfall_3m, rolling_temp_6m, rolling_rainfall_6m, is_monsoon, pre_monsoon, post_monsoon, is_winter_dry, monsoon_phase, monsoon_phase_sin, monsoon_phase_cos, rainfall_climatology, rolling_rainfall_std_3m, rolling_rainfall_std_6m, rolling_rainfall_cv_3m, rolling_rainfall_median_3m, rolling_rainfall_median_6m, dry_months_streak, wet_months_streak, rainfall_trend, rainfall_acceleration, rainfall_growth_rate, rainfall_momentum, rainfall_seasonal_deviation, temperature_climatology, temperature_anomaly, temp_trend_3m, soil_moisture_trend, evabs_trend, sro_trend, soil_moisture_zone_anomaly, zone_rainfall_climatology, climate_zone_Central Plateau Region, climate_zone_Eastern Coastal Region, climate_zone_Himalayan Region, climate_zone_Indo-Gangetic Plains, climate_zone_North-East Region, climate_zone_Southern Peninsular Region, climate_zone_Thar Desert Region, climate_zone_Western Coastal Region, climate_zone_Western Ghats Region
```

---

## Model Comparison (Validation Set)

| Model | MAE | RMSE | R² | MAPE | Train(s) | Infer(ms) |
|-------|-----|------|-----|------|----------|-----------|
| LightGBM | 0.4984 | 1.0495 | 0.9671 | 138.0566 | 3.32 | 72.24 |

---

## Best Model Selection
**LightGBM** was selected based on: 1) highest R² → 2) lowest RMSE → 3) lowest MAE.

### Best Hyperparameters (after tuning)
```json
{
  "colsample_bytree": 0.7,
  "learning_rate": 0.03,
  "max_depth": -1,
  "n_estimators": 1500,
  "num_leaves": 63,
  "subsample": 1.0
}
```

---

## Test Set Metrics
| Metric | Value |
|--------|-------|
| MAE | 0.502 mm |
| RMSE | 0.9756 mm |
| R² | 0.9697 |
| MAPE | 154.2833 % |

---

## Feature Importance (Top 20)
| Rank | Feature | Importance |
|------|---------|------------|
| 1 | sro | 7388 |
| 2 | rainfall_acceleration | 5002 |
| 3 | rolling_rainfall_3m | 4454 |
| 4 | rolling_rainfall_6m | 3899 |
| 5 | rolling_rainfall_median_3m | 3741 |
| 6 | rainfall_climatology | 3575 |
| 7 | evabs | 3565 |
| 8 | sro_trend | 3524 |
| 9 | rainfall_seasonal_deviation | 3411 |
| 10 | temperature_anomaly | 3077 |
| 11 | soil_moisture | 2946 |
| 12 | rolling_rainfall_cv_3m | 2905 |
| 13 | rainfall_momentum | 2841 |
| 14 | evabs_trend | 2592 |
| 15 | soil_moisture_zone_anomaly | 2587 |
| 16 | soil_moisture_trend | 2574 |
| 17 | soil_moisture_prev_1 | 2562 |
| 18 | rolling_rainfall_std_6m | 2174 |
| 19 | temp_trend_3m | 2126 |
| 20 | rolling_rainfall_std_3m | 2115 |

---

## Monthly Diagnostics

| Month | MAE (mm) | Notes |
|-------|----------|-------|
| Jan | 0.11 | ✅ Easiest |
| Feb | 0.14 |  |
| Mar | 0.15 |  |
| Apr | 0.15 |  |
| May | 0.49 |  |
| Jun | 0.69 |  |
| Jul | 1.14 | ⚠️ Hardest |
| Aug | 0.91 |  |
| Sep | 0.94 |  |
| Oct | 0.76 |  |
| Nov | 0.24 |  |
| Dec | 0.21 |  |

---

## Climate Zone Diagnostics

| Zone | MAE (mm) |
|------|----------|
| Thar Desert Region | 0.12 |
| Indo-Gangetic Plains | 0.25 |
| Southern Peninsular Region | 0.37 |
| Central Plateau Region | 0.41 |
| Eastern Coastal Region | 0.53 |
| North-East Region | 0.72 |
| Western Coastal Region | 0.72 |
| Himalayan Region | 0.73 |
| Western Ghats Region | 0.92 |

---

## Monsoon Behavior Analysis
| Period | MAE (mm) |
|--------|----------|
| Monsoon (JJAS) | 0.917 |
| Non-Monsoon | 0.285 |
| Over-predictions | 860 rows |
| Under-predictions | 785 rows |

**Easiest month**: Jan
**Hardest month**: Jul
**Easiest zone**: Thar Desert Region
**Hardest zone**: Western Ghats Region

---

## Known Limitations
1. **Zero-inflation**: ~25% of records have near-zero rainfall (dry months). Errors in MAPE inflate for these.
2. **Extreme events**: Unprecedented rainfall events (cyclones, cloud-bursts) are underrepresented in training data.
3. **Spatial resolution**: ERA5-Land at 0.1° is coarser than district-level impacts.
4. **Future climate drift**: Model trained on 2000–2020; patterns post-2025 may shift.

## Recommendations
- Apply `log1p` target transformation on the next iteration to handle skew.
- Investigate quantile regression for uncertainty estimation during monsoon months.
- Add teleconnection indices (IOD, ENSO, MJO phase) as future features for further improvement.
- Retrain annually as new ERA5 data becomes available.
