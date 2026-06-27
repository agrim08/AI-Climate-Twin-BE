# Rainfall Prediction Model — Final Report

## Executive Summary
A production-ready **Climate State Rainfall Model** has been successfully trained
and selected for the AI Climate Digital Twin of India.

- **Best Model**: LightGBM
- **Test R²**: 0.9999
- **Test RMSE**: 1.063 mm
- **Test MAE**: 0.523 mm
- **Test MAPE**: 0.9238%

---

## Dataset Overview
| Property | Value |
|----------|-------|
| Train rows | 49,500 (year ≤ 2020) |
| Validation rows | 4,752 (2021–2022) |
| Test rows | 7,128 (year ≥ 2023) |
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
| LightGBM | 0.5408 | 1.037 | 0.9999 | 0.971 | 7.81 | 337.36 |

---

## Best Model Selection
**LightGBM** was selected based on: 1) highest R² → 2) lowest RMSE → 3) lowest MAE.

### Best Hyperparameters (after tuning)
```json
{
  "colsample_bytree": 0.8,
  "learning_rate": 0.03,
  "max_depth": 10,
  "n_estimators": 800,
  "num_leaves": 127,
  "subsample": 0.7
}
```

---

## Test Set Metrics
| Metric | Value |
|--------|-------|
| MAE | 0.523 mm |
| RMSE | 1.063 mm |
| R² | 0.9999 |
| MAPE | 0.9238 % |

---

## Feature Importance (Top 20)
| Rank | Feature | Importance |
|------|---------|------------|
| 1 | sro | 13312 |
| 2 | rainfall_acceleration | 5838 |
| 3 | rolling_rainfall_3m | 4626 |
| 4 | sro_trend | 3478 |
| 5 | rolling_rainfall_median_3m | 3300 |
| 6 | rainfall_climatology | 3279 |
| 7 | soil_moisture_zone_anomaly | 3154 |
| 8 | rainfall_seasonal_deviation | 3150 |
| 9 | temperature_anomaly | 2963 |
| 10 | soil_moisture_trend | 2953 |
| 11 | evabs_trend | 2927 |
| 12 | rolling_rainfall_cv_3m | 2877 |
| 13 | rolling_rainfall_6m | 2762 |
| 14 | temperature_prev_3 | 2587 |
| 15 | soil_moisture_prev_1 | 2435 |
| 16 | year | 2397 |
| 17 | zone_rainfall_climatology | 2327 |
| 18 | rolling_rainfall_median_6m | 2288 |
| 19 | soil_moisture | 2272 |
| 20 | temperature_prev_1 | 2237 |

---

## Monthly Diagnostics

| Month | MAE (mm) | Notes |
|-------|----------|-------|
| Jan | 0.28 |  |
| Feb | 0.30 |  |
| Mar | 0.33 |  |
| Apr | 0.30 |  |
| May | 0.58 |  |
| Jun | 0.94 |  |
| Jul | 1.19 | ⚠️ Hardest |
| Aug | 0.92 |  |
| Sep | 0.60 |  |
| Oct | 0.30 |  |
| Nov | 0.26 | ✅ Easiest |
| Dec | 0.29 |  |

---

## Climate Zone Diagnostics

| Zone | MAE (mm) |
|------|----------|
| Thar Desert Region | 0.36 |
| Southern Peninsular Region | 0.38 |
| Indo-Gangetic Plains | 0.40 |
| Central Plateau Region | 0.48 |
| Himalayan Region | 0.58 |
| Eastern Coastal Region | 0.68 |
| Western Coastal Region | 0.71 |
| North-East Region | 0.72 |
| Western Ghats Region | 1.01 |

---

## Monsoon Behavior Analysis
| Period | MAE (mm) |
|--------|----------|
| Monsoon (JJAS) | 0.912 |
| Non-Monsoon | 0.328 |
| Over-predictions | 3768 rows |
| Under-predictions | 3360 rows |

**Easiest month**: Nov
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
