# Rainfall Feature Engineering Report

## Pipeline Summary
- **Total Records**: 14,288
- **Total Features Engineered**: 62
- **Target Variable**: `target_rainfall_next_month`
- **Leakage Prevention**: Future labels (`drought_risk`, `target_temperature_next_month`) removed.

---

## Feature Classification

### Mandatory Features (Correlation ≥ 0.30 with target)
- `rainfall_climatology`
- `rainfall_mm`
- `zone_rainfall_climatology`
- `month_cos`
- `sro`
- `rolling_rainfall_3m`
- `rainfall_acceleration`
- `monsoon_phase_cos`
- `soil_moisture`
- `is_monsoon`
- `rainfall_trend`
- `rainfall_momentum`
- `rainfall_prev_1`
- `soil_moisture_trend`
- `zone_rainfall_anomaly`
- `temp_trend_3m`

### Useful Features (0.10 ≤ Correlation < 0.30)
- `is_winter_dry`
- `rainfall_growth_rate`
- `monsoon_phase_sin`
- `soil_moisture_prev_1`
- `post_monsoon`
- `rolling_rainfall_6m`
- `sro_trend`
- `zone_rainfall_zscore`
- `longitude`
- `rolling_rainfall_std_3m`
- `climate_zone_Thar Desert Region`
- `climate_zone_Western Ghats Region`
- `soil_moisture_zone_anomaly`
- `climate_zone_North-East Region`
- `zone_rainfall_anomaly_pct`
- `rolling_rainfall_median_3m`
- `temperature_prev_1`
- `dry_months_streak`
- `climate_zone_Indo-Gangetic Plains`
- `climate_zone_Western Coastal Region`
- `rolling_temp_3m`

### Experimental Features (Correlation < 0.10)
- `temperature_c`
- `temperature_climatology`
- `month_sin`
- `climate_zone_Himalayan Region`
- `latitude`
- `climate_zone_Southern Peninsular Region`
- `climate_zone_Central Plateau Region`
- `rainfall_prev_3`
- `rainfall_anomaly`
- `rolling_rainfall_cv_3m`
- `monsoon_phase`
- `wet_months_streak`
- `rolling_rainfall_median_6m`
- `month`
- `rolling_rainfall_std_6m`
- `rainfall_seasonal_deviation`
- `pre_monsoon`
- `rolling_temp_6m`
- `year`
- `temperature_prev_3`

---

## Top 20 Features by Correlation with Next-Month Rainfall

| Rank | Feature | |Correlation| |
|------|---------|------------|
| 1 | rainfall_climatology | 0.7345 |
| 2 | rainfall_mm | 0.6782 |
| 3 | zone_rainfall_climatology | 0.6210 |
| 4 | month_cos | 0.5358 |
| 5 | sro | 0.4869 |
| 6 | rolling_rainfall_3m | 0.4600 |
| 7 | rainfall_acceleration | 0.4507 |
| 8 | monsoon_phase_cos | 0.4368 |
| 9 | soil_moisture | 0.4341 |
| 10 | is_monsoon | 0.4168 |
| 11 | rainfall_trend | 0.3979 |
| 12 | rainfall_momentum | 0.3898 |
| 13 | rainfall_prev_1 | 0.3832 |
| 14 | soil_moisture_trend | 0.3301 |
| 15 | zone_rainfall_anomaly | 0.3207 |
| 16 | temp_trend_3m | 0.3039 |
| 17 | is_winter_dry | 0.2930 |
| 18 | rainfall_growth_rate | 0.2841 |
| 19 | monsoon_phase_sin | 0.2653 |
| 20 | soil_moisture_prev_1 | 0.2333 |

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
