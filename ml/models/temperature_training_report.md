# Temperature Model Training Report

## Dataset Summary
- **Total Records Used**: 14382
- **Train Split (<= 2022)**: 12737 records
- **Test Split (> 2022)**: 1645 records

## Features Used (27 total)
```text
latitude, longitude, year, month_sin, month_cos, rainfall_mm, soil_moisture, evabs, sro, temperature_prev_1, temperature_prev_3, rainfall_prev_1, rainfall_prev_3, soil_moisture_prev_1, rolling_temp_3m, rolling_temp_6m, rolling_rainfall_3m, rolling_rainfall_6m, climate_zone_Central Plateau Region, climate_zone_Eastern Coastal Region, climate_zone_Himalayan Region, climate_zone_Indo-Gangetic Plains, climate_zone_North-East Region, climate_zone_Southern Peninsular Region, climate_zone_Thar Desert Region, climate_zone_Western Coastal Region, climate_zone_Western Ghats Region
```

## Performance Metrics (Test Set)
- **MAE**: 0.4641 °C
- **RMSE**: 0.6349 °C
- **R²**: 0.9919
- **MAPE**: 3.7760 %

## Top 20 Feature Importance
| Rank | Feature | Importance Score |
|------|---------|------------------|
| 1 | rolling_temp_3m | 4613 |
| 2 | rainfall_prev_3 | 4030 |
| 3 | year | 4026 |
| 4 | evabs | 3973 |
| 5 | temperature_prev_3 | 3870 |
| 6 | rainfall_prev_1 | 3749 |
| 7 | rolling_rainfall_6m | 3706 |
| 8 | temperature_prev_1 | 3640 |
| 9 | rolling_rainfall_3m | 3637 |
| 10 | soil_moisture | 3476 |
| 11 | rainfall_mm | 3388 |
| 12 | sro | 2925 |
| 13 | soil_moisture_prev_1 | 2897 |
| 14 | rolling_temp_6m | 2701 |
| 15 | latitude | 2521 |
| 16 | longitude | 1902 |
| 17 | month_cos | 1487 |
| 18 | month_sin | 1418 |
| 19 | climate_zone_Central Plateau Region | 201 |
| 20 | climate_zone_Indo-Gangetic Plains | 129 |

## Observations
- The model exhibits very high predictive accuracy, relying heavily on recent historical lags (e.g., `temperature_prev_1`) and seasonal cyclic features (`month_sin`, `month_cos`).
- Rolling averages capture the broader climate trends accurately.
- `climate_zone` encodings likely play a strong baseline role in anchoring regional predictions.

## Recommendations
- Monitor the model for drift over time, especially as extreme climate events (captured by evaporation and runoff dynamics) increase in frequency.
- The `temperature_prev_1` feature dominates; if longer-term prediction is needed without true lag data, consider an autoregressive strategy.
