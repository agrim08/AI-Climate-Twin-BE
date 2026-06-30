# Rainfall Feature Engineering Report

## Pipeline Summary
- **Total Records**: 61,380
- **Total Features Engineered**: 62
- **Target Variable**: `target_rainfall_next_month`
- **Leakage Prevention**: Future labels (`drought_risk`, `target_temperature_next_month`) removed.

---

## Feature Classification

### Mandatory Features (Correlation ≥ 0.30 with target)
- `zone_rainfall_climatology`
- `rainfall_climatology`
- `rainfall_mm`
- `sro`
- `soil_moisture`
- `rainfall_momentum`
- `rainfall_acceleration`
- `month_cos`
- `rainfall_growth_rate`
- `sro_trend`
- `rainfall_trend`
- `soil_moisture_trend`
- `temp_trend_3m`
- `temperature_climatology`
- `temperature_c`
- `evabs`
- `temperature_prev_1`
- `rolling_temp_3m`
- `monsoon_phase_sin`
- `monsoon_phase_cos`
- `rolling_rainfall_3m`
- `is_monsoon`
- `rainfall_prev_1`
- `is_winter_dry`
- `soil_moisture_prev_1`

### Useful Features (0.10 ≤ Correlation < 0.30)
- `climate_zone_Western Ghats Region`
- `rolling_rainfall_median_6m`
- `post_monsoon`
- `evabs_trend`
- `rainfall_prev_3`
- `rolling_rainfall_std_3m`
- `rolling_rainfall_cv_3m`
- `rolling_temp_6m`
- `climate_zone_Western Coastal Region`
- `climate_zone_Thar Desert Region`
- `climate_zone_Southern Peninsular Region`
- `latitude`
- `rolling_rainfall_std_6m`
- `climate_zone_North-East Region`
- `pre_monsoon`

### Experimental Features (Correlation < 0.10)
- `temperature_prev_3`
- `month`
- `rolling_rainfall_6m`
- `climate_zone_Indo-Gangetic Plains`
- `climate_zone_Central Plateau Region`
- `longitude`
- `rolling_rainfall_median_3m`
- `monsoon_phase`
- `climate_zone_Eastern Coastal Region`
- `year`
- `climate_zone_Himalayan Region`
- `month_sin`
- `temperature_anomaly`
- `wet_months_streak`
- `rainfall_seasonal_deviation`
- `rainfall_anomaly_pct`
- `rainfall_anomaly`
- `zone_rainfall_anomaly_pct`
- `zone_rainfall_anomaly`
- `zone_rainfall_zscore`

---

## Top 20 Features by Correlation with Next-Month Rainfall

| Rank | Feature | |Correlation| |
|------|---------|------------|
| 1 | zone_rainfall_climatology | 0.7865 |
| 2 | rainfall_climatology | 0.7864 |
| 3 | rainfall_mm | 0.7845 |
| 4 | sro | 0.7845 |
| 5 | soil_moisture | 0.7456 |
| 6 | rainfall_momentum | 0.6985 |
| 7 | rainfall_acceleration | 0.6609 |
| 8 | month_cos | 0.6558 |
| 9 | rainfall_growth_rate | 0.5880 |
| 10 | sro_trend | 0.5872 |
| 11 | rainfall_trend | 0.4837 |
| 12 | soil_moisture_trend | 0.4833 |
| 13 | temp_trend_3m | 0.4652 |
| 14 | temperature_climatology | 0.4436 |
| 15 | temperature_c | 0.4372 |
| 16 | evabs | 0.4369 |
| 17 | temperature_prev_1 | 0.4365 |
| 18 | rolling_temp_3m | 0.4298 |
| 19 | monsoon_phase_sin | 0.4197 |
| 20 | monsoon_phase_cos | 0.4088 |

---

## Feature Explanations

### Monsoon Intelligence
| Feature | Why It Helps | Risk |
|---------|-------------|------|
| `is_monsoon` | Captures the JJAS window responsible for ~80% of annual rainfall | None |
| `monsoon_phase` | Encodes intra-monsoon progression (onset vs peak vs withdrawal) | Ordinal encoding may overweight linear relationship |
| `monsoon_phase_sin/cos` | Cyclic encoding preserves continuity across phase boundaries | None |
| `pre_monsoon` | Heat buildup in MAM drives convective instability for onset | None |
| `post_monsoon` | NE monsoon active over S. India Oct-Nov; captures different mechanism | None |

### Rainfall Anomaly & Variability
| Feature | Why It Helps | Risk |
|---------|-------------|------|
| `rainfall_anomaly` | Deviations from climatology persist month to month (autocorrelation) | Climatology uses full dataset mean — assume stationarity |
| `rainfall_anomaly_pct` | Normalised deviation more comparable across arid vs humid zones | Division near zero needs clipping |
| `rolling_rainfall_std_3m` | High variability precedes uncertain/extreme rainfall | Requires ≥2 months of history |
| `rolling_rainfall_cv_3m` | Coefficient of variation normalises std by mean | Unstable when mean ≈ 0 |
| `dry_months_streak` | Consecutive dry months predict drought conditions | Threshold (5mm) is heuristic |
| `wet_months_streak` | Consecutive wet months predict monsoon persistence | Threshold (50mm) is heuristic |

### Rainfall Momentum & Trend
| Feature | Why It Helps | Risk |
|---------|-------------|------|
| `rainfall_trend` | Direction of change (increasing/decreasing) from lag-3 to lag-1 | May alias with lag features |
| `rainfall_acceleration` | Rate of change in the trend — catching surges or collapses | Second-order differences are noisy |
| `rainfall_growth_rate` | Percentage change captures magnitude of trend | Clips needed when denominator ≈ 0 |
| `rainfall_momentum` | Lag-1 deviation from climatology | Correlated with `rainfall_anomaly` |
| `rainfall_seasonal_deviation` | Lag-1 vs same-month historical average — anomaly signal | Requires joining prev-month climatology |

### Temperature Anomaly
| Feature | Why It Helps | Risk |
|---------|-------------|------|
| `temperature_anomaly` | Warm anomaly → enhanced evaporation → higher monsoon rainfall potential | Indirect relationship; weak outside monsoon season |
| `temp_trend_3m` | Warming/cooling trajectory drives convection strength | Noise outside monsoon months |

### Land Surface
| Feature | Why It Helps | Risk |
|---------|-------------|------|
| `soil_moisture_trend` | Rising moisture → soil saturation → next-month runoff/flooding | Lag introduces 1-month delay correctly |
| `sro_trend` | Increasing runoff signals peak saturation state | Highly correlated with `soil_moisture_trend` |
| `soil_moisture_zone_anomaly` | How wet a city is relative to its climate zone peers | Uses full-dataset groupby (static, not future) |

### Zone-Relative Features
| Feature | Why It Helps | Risk |
|---------|-------------|------|
| `zone_rainfall_anomaly` | 50mm in Thar Desert is extreme; 50mm in NE is dry. Zone context is critical | Groupby is static — safe |
| `zone_rainfall_zscore` | Standardised anomaly, dimensionless — comparable across all zones | Assumes zone std is stable |

---

## Leakage Prevention Summary

The following columns were **deliberately excluded** to prevent data leakage:

| Column | Reason |
|--------|--------|
| `target_temperature_next_month` | Future temperature (cannot know at prediction time) |
| `drought_risk` | Derived post-hoc from rainfall patterns — circular dependency |
| `heatwave_risk` | Derived post-hoc from temperature labels |
| `climate_risk_score` | Composite of multiple derived labels |
| `date` | Encoded as `year`, `month`, `month_sin/cos` |
| `city` | Encoded via `latitude`, `longitude`, and OHE climate zones |

---

## Recommendations for Model Training

1. Use **time-based split**: Train on ≤ 2022, test on > 2022.
2. Consider `log1p` transformation of `target_rainfall_next_month` — rainfall is right-skewed.
3. Monitor feature importance at training time to confirm experimental features add value.
4. Evaluate `zone_rainfall_zscore` as an alternate to raw `rainfall_mm` for generalisation.
