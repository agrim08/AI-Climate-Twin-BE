# Extreme Weather Intelligence Report
## AI Climate Digital Twin of India

---

## 1. Dataset Overview

- **Total Rows**: 14,382
- **Total Columns**: 83
- **Cities**: 47
- **Climate Zones**: 9
- **Year Range**: 2000 – 2025
- **Heatwave Features Engineered**: 20
- **Extreme Rainfall Features Engineered**: 25
- **Missing Values**: 235

### Heatwave Category Distribution
| Category | Count | % |
|----------|-------|---|
| Low | 7,191 | 50.0% |
| Medium | 3,572 | 24.8% |
| High | 2,162 | 15.0% |
| Extreme | 1,457 | 10.1% |

### Extreme Rainfall Category Distribution
| Category | Count | % |
|----------|-------|---|
| Low | 7,191 | 50.0% |
| Medium | 3,572 | 24.8% |
| High | 2,162 | 15.0% |
| Extreme | 1,457 | 10.1% |

---

## 2. Feature Engineering Methodology

### Climatology Baselines
All anomaly and z-score features are computed relative to **city × month** climatology baselines,
computed from the full historical record (2000–2025).
This ensures:
- Seasonal cycles are correctly removed
- Zone-relative extremes are captured (40°C in desert ≠ 40°C in northeast)
- No future leakage (baselines are pre-computed from full history)

---

## 3. Heatwave Severity Score Formula

```
heatwave_severity_score = (
    0.35 × norm(temperature_anomaly, positive only)  # Primary heat signal
  + 0.25 × norm(heat_stress)                         # Anomaly × rainfall absence
  + 0.15 × norm(soil_moisture_deficit)               # Dryness amplifier
  + 0.15 × norm(rainfall_deficit)                    # Co-occurring drought
  + 0.10 × norm(evaporation_pressure)                # Atmospheric demand
)
```
Each component is individually min-max normalized over the full dataset before weighting,
ensuring no single variable dominates by scale.

---

## 4. Extreme Rainfall Severity Score Formula

```
extreme_rainfall_score = (
    0.35 × norm(rainfall_anomaly, positive only)     # Primary rain signal
  + 0.25 × norm(rainfall_intensity)                  # Daily rate pressure
  + 0.20 × norm(runoff_pressure)                     # Flood potential
  + 0.10 × norm(soil_saturation)                     # Saturation amplifier
  + 0.10 × norm(rainfall_acceleration, positive)     # Rapid onset
)
```

---

## 5. Category Labeling Methodology

**Both heatwave and extreme rainfall categories use city-level percentile thresholds.**
City-level percentiles ensure climate-zone fairness:
| Category | Severity Score Percentile | Description |
|----------|--------------------------|-------------|
| Low      | 0 – 50th                 | Routine conditions |
| Medium   | 50th – 75th              | Notable event |
| High     | 75th – 90th              | Significant event |
| Extreme  | 90th – 100th             | Exceptional event |

---

## 6. Climate Zone Observations

### Heatwave Risk by Climate Zone
| Climate Zone | Mean HW Score | Extreme HW % |
|---|---|---|
| Indo-Gangetic Plains | 0.0965 | 10.1% |
| Central Plateau Region | 0.0946 | 10.1% |
| Southern Peninsular Region | 0.0851 | 10.1% |
| Eastern Coastal Region | 0.0848 | 10.1% |
| Himalayan Region | 0.0799 | 10.1% |
| Western Coastal Region | 0.0724 | 10.1% |
| North-East Region | 0.0716 | 10.1% |
| Thar Desert Region | 0.0703 | 10.1% |
| Western Ghats Region | 0.0655 | 10.1% |

### Extreme Rainfall Risk by Climate Zone
| Climate Zone | Mean ER Score | Extreme ER % |
|---|---|---|
| North-East Region | 0.1374 | 10.1% |
| Western Ghats Region | 0.1313 | 10.1% |
| Himalayan Region | 0.1190 | 10.1% |
| Western Coastal Region | 0.1076 | 10.1% |
| Central Plateau Region | 0.0938 | 10.1% |
| Eastern Coastal Region | 0.0875 | 10.1% |
| Southern Peninsular Region | 0.0782 | 10.1% |
| Indo-Gangetic Plains | 0.0719 | 10.1% |
| Thar Desert Region | 0.0328 | 10.1% |

### Peak Heatwave Months (India-wide)
| Month | Mean HW Score |
|-------|---------------|
| Feb | 0.1003 |
| Nov | 0.1002 |
| Mar | 0.0954 |
| Jan | 0.0908 |
| Oct | 0.0907 |
| Dec | 0.0891 |
| Apr | 0.0853 |
| May | 0.0757 |
| Jun | 0.0749 |
| Sep | 0.0678 |
| Jul | 0.0579 |
| Aug | 0.0525 |

### Peak Extreme Rainfall Months (India-wide)
| Month | Mean ER Score |
|-------|---------------|
| Jul | 0.1602 |
| Aug | 0.1493 |
| Sep | 0.1255 |
| Jun | 0.1245 |
| Oct | 0.0950 |
| May | 0.0827 |
| Nov | 0.0750 |
| Dec | 0.0685 |
| Apr | 0.0643 |
| Jan | 0.0628 |
| Feb | 0.0590 |
| Mar | 0.0579 |

---

## 7. Strongest Predictors

### Heatwave — Top 15 Features by Correlation with Severity Score
| Rank | Feature | |Corr with Score| |
|------|---------|----------------|
| 1 | hw_rainfall_heat_interaction | 0.8373 |
| 2 | hw_heat_stress | 0.7877 |
| 3 | hw_heatwave_intensity | 0.7495 |
| 4 | hw_temperature_anomaly | 0.7483 |
| 5 | hw_soil_heat_interaction | 0.7361 |
| 6 | hw_temperature_zscore | 0.7065 |
| 7 | hw_compound_heat_drought | 0.7041 |
| 8 | hw_apparent_temp_anomaly | 0.4290 |
| 9 | hw_zone_temp_zscore | 0.3712 |
| 10 | hw_climate_zone_heat_anomaly | 0.1908 |
| 11 | hw_seasonal_heat_deviation | 0.1587 |
| 12 | hw_rolling_heat_3m | 0.1495 |
| 13 | hw_rolling_heat_6m | 0.1125 |
| 14 | hw_heat_acceleration | 0.0986 |
| 15 | hw_heat_excess | 0.0945 |

### Extreme Rainfall — Top 15 Features by Correlation with Severity Score
| Rank | Feature | |Corr with Score| |
|------|---------|----------------|
| 1 | er_rainfall_intensity | 0.9052 |
| 2 | er_seasonal_rainfall_deviation | 0.7809 |
| 3 | er_soil_saturation | 0.7579 |
| 4 | er_runoff_response | 0.7217 |
| 5 | er_flood_potential_proxy | 0.7112 |
| 6 | er_zone_rainfall_anomaly | 0.6383 |
| 7 | er_evaporation_demand_ratio | 0.6382 |
| 8 | er_compound_rainfall_saturation | 0.6266 |
| 9 | er_rainfall_momentum | 0.6264 |
| 10 | er_rainfall_anomaly | 0.5753 |
| 11 | er_zone_rainfall_zscore | 0.5660 |
| 12 | er_antecedent_soil_moisture | 0.5642 |
| 13 | er_rainfall_surge | 0.4907 |
| 14 | er_rainfall_zscore | 0.4692 |
| 15 | er_extreme_precipitation_index | 0.4647 |


---

## 8. Feature Classification

### Heatwave Features
**Mandatory** (|corr| ≥ 0.40):
- `hw_rainfall_heat_interaction`
- `hw_heat_stress`
- `hw_heatwave_intensity`
- `hw_temperature_anomaly`
- `hw_soil_heat_interaction`
- `hw_temperature_zscore`
- `hw_compound_heat_drought`
- `hw_apparent_temp_anomaly`

**Useful** (0.20 ≤ |corr| < 0.40):
- `hw_zone_temp_zscore`

**Experimental** (|corr| < 0.20):
- `hw_climate_zone_heat_anomaly`
- `hw_seasonal_heat_deviation`
- `hw_rolling_heat_3m`
- `hw_rolling_heat_6m`
- `hw_heat_acceleration`
- `hw_heat_excess`
- `hw_dry_heat_indicator`
- `hw_consecutive_hot_months`
- `hw_apparent_temperature`
- `hw_evaporation_heat_ratio`
- `hw_rolling_temp_trend_3m`

### Extreme Rainfall Features
**Mandatory** (|corr| ≥ 0.40):
- `er_rainfall_intensity`
- `er_seasonal_rainfall_deviation`
- `er_soil_saturation`
- `er_runoff_response`
- `er_flood_potential_proxy`
- `er_zone_rainfall_anomaly`
- `er_evaporation_demand_ratio`
- `er_compound_rainfall_saturation`
- `er_rainfall_momentum`
- `er_rainfall_anomaly`
- `er_zone_rainfall_zscore`
- `er_antecedent_soil_moisture`
- `er_rainfall_surge`
- `er_rainfall_zscore`
- `er_extreme_precipitation_index`
- `er_cumulative_rain_3m`
- `er_is_monsoon`
- `er_monsoon_phase_factor`

**Useful** (0.20 ≤ |corr| < 0.40):
- `er_runoff_pressure`
- `er_cumulative_rain_6m`

**Experimental** (|corr| < 0.20):
- `er_rainfall_variability_3m`
- `er_rainfall_variability_6m`
- `er_rainfall_acceleration`
- `er_water_surplus`
- `er_consecutive_wet_months`


---

## 9. Leakage Prevention Report

The following columns were identified as future-information or post-hoc labels and **removed**:
- `target_temperature_next_month`
- `target_rainfall_next_month`
- `drought_risk`
- `heatwave_risk`
- `climate_risk_score`

**Verification**: No `target_`, `next_month`, or post-hoc label columns remain in the final dataset.

---

## 10. Recommendations for Phase 2 Model Training

1. **Primary Task**: Multi-class classification for `heatwave_category` and `extreme_rainfall_category`.
2. **Secondary Task**: Regression on `heatwave_severity_score` and `extreme_rainfall_score` for continuous risk output.
3. **Chronological Split**: Train ≤ 2020 | Validation 2021–2022 | Test ≥ 2023 (avoids temporal leakage).
4. **Algorithm**: LightGBM or XGBoost (proven on prior temperature, rainfall, drought models).
5. **Class Weighting**: Apply `class_weight='balanced'` for the Extreme class (10% minority).
6. **Evaluation Metrics**: F1-Macro, Confusion Matrix by climate zone, ROC-AUC for Extreme class.
7. **Feature Selection**: Begin with Mandatory + Useful features; conduct SHAP analysis post-training.
8. **Compound Events**: Consider multi-label joint prediction for simultaneous heatwave + extreme rainfall.