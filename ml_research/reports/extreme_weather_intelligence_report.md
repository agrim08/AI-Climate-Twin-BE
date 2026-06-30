# Extreme Weather Intelligence Report
## AI Climate Digital Twin of India

---

## 1. Dataset Overview

- **Total Rows**: 61,776
- **Total Columns**: 83
- **Cities**: 198
- **Climate Zones**: 9
- **Year Range**: 2000 – 2025
- **Heatwave Features Engineered**: 20
- **Extreme Rainfall Features Engineered**: 25
- **Missing Values**: 990

### Heatwave Category Distribution
| Category | Count | % |
|----------|-------|---|
| Low | 30,898 | 50.0% |
| Medium | 15,436 | 25.0% |
| High | 9,106 | 14.7% |
| Extreme | 6,336 | 10.3% |

### Extreme Rainfall Category Distribution
| Category | Count | % |
|----------|-------|---|
| Low | 30,888 | 50.0% |
| Medium | 15,444 | 25.0% |
| High | 9,108 | 14.7% |
| Extreme | 6,336 | 10.3% |

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
| Thar Desert Region | 0.1920 | 10.3% |
| Western Coastal Region | 0.1669 | 10.3% |
| Southern Peninsular Region | 0.1558 | 10.3% |
| Central Plateau Region | 0.1549 | 10.3% |
| Eastern Coastal Region | 0.1534 | 10.3% |
| Indo-Gangetic Plains | 0.1472 | 10.3% |
| North-East Region | 0.1285 | 10.3% |
| Western Ghats Region | 0.1262 | 10.3% |
| Himalayan Region | 0.1225 | 10.3% |

### Extreme Rainfall Risk by Climate Zone
| Climate Zone | Mean ER Score | Extreme ER % |
|---|---|---|
| Western Ghats Region | 0.2950 | 10.3% |
| Western Coastal Region | 0.2618 | 10.3% |
| North-East Region | 0.2505 | 10.3% |
| Eastern Coastal Region | 0.2258 | 10.3% |
| Himalayan Region | 0.2170 | 10.3% |
| Central Plateau Region | 0.2145 | 10.3% |
| Indo-Gangetic Plains | 0.2082 | 10.3% |
| Southern Peninsular Region | 0.1990 | 10.3% |
| Thar Desert Region | 0.1691 | 10.3% |

### Peak Heatwave Months (India-wide)
| Month | Mean HW Score |
|-------|---------------|
| Apr | 0.1881 |
| Mar | 0.1840 |
| Feb | 0.1720 |
| Oct | 0.1610 |
| Jan | 0.1599 |
| Dec | 0.1541 |
| Nov | 0.1532 |
| May | 0.1418 |
| Sep | 0.1315 |
| Jun | 0.1273 |
| Aug | 0.1238 |
| Jul | 0.1227 |

### Peak Extreme Rainfall Months (India-wide)
| Month | Mean ER Score |
|-------|---------------|
| Jul | 0.3126 |
| Jun | 0.3078 |
| Aug | 0.2809 |
| May | 0.2248 |
| Sep | 0.2111 |
| Dec | 0.2073 |
| Nov | 0.2023 |
| Jan | 0.1896 |
| Feb | 0.1772 |
| Mar | 0.1737 |
| Apr | 0.1724 |
| Oct | 0.1711 |

---

## 7. Strongest Predictors

### Heatwave — Top 15 Features by Correlation with Severity Score
| Rank | Feature | |Corr with Score| |
|------|---------|----------------|
| 1 | hw_heatwave_intensity | 0.7724 |
| 2 | hw_rainfall_heat_interaction | 0.6952 |
| 3 | hw_temperature_anomaly | 0.6677 |
| 4 | hw_heat_stress | 0.6621 |
| 5 | hw_temperature_zscore | 0.6615 |
| 6 | hw_climate_zone_heat_anomaly | 0.6568 |
| 7 | hw_zone_temp_zscore | 0.6566 |
| 8 | hw_apparent_temp_anomaly | 0.5334 |
| 9 | hw_soil_heat_interaction | 0.5308 |
| 10 | hw_compound_heat_drought | 0.4693 |
| 11 | hw_seasonal_heat_deviation | 0.3232 |
| 12 | hw_dry_heat_indicator | 0.1501 |
| 13 | hw_apparent_temperature | 0.1239 |
| 14 | hw_heat_excess | 0.1219 |
| 15 | hw_rolling_heat_6m | 0.1169 |

### Extreme Rainfall — Top 15 Features by Correlation with Severity Score
| Rank | Feature | |Corr with Score| |
|------|---------|----------------|
| 1 | er_flood_potential_proxy | 0.8749 |
| 2 | er_rainfall_intensity | 0.8053 |
| 3 | er_soil_saturation | 0.7783 |
| 4 | er_evaporation_demand_ratio | 0.7183 |
| 5 | er_compound_rainfall_saturation | 0.6530 |
| 6 | er_rainfall_momentum | 0.6030 |
| 7 | er_monsoon_phase_factor | 0.6022 |
| 8 | er_extreme_precipitation_index | 0.5564 |
| 9 | er_zone_rainfall_anomaly | 0.5556 |
| 10 | er_zone_rainfall_zscore | 0.5550 |
| 11 | er_rainfall_anomaly | 0.5536 |
| 12 | er_rainfall_zscore | 0.5428 |
| 13 | er_is_monsoon | 0.5300 |
| 14 | er_antecedent_soil_moisture | 0.5260 |
| 15 | er_seasonal_rainfall_deviation | 0.5183 |


---

## 8. Feature Classification

### Heatwave Features
**Mandatory** (|corr| ≥ 0.40):
- `hw_heatwave_intensity`
- `hw_rainfall_heat_interaction`
- `hw_temperature_anomaly`
- `hw_heat_stress`
- `hw_temperature_zscore`
- `hw_climate_zone_heat_anomaly`
- `hw_zone_temp_zscore`
- `hw_apparent_temp_anomaly`
- `hw_soil_heat_interaction`
- `hw_compound_heat_drought`

**Useful** (0.20 ≤ |corr| < 0.40):
- `hw_seasonal_heat_deviation`

**Experimental** (|corr| < 0.20):
- `hw_dry_heat_indicator`
- `hw_apparent_temperature`
- `hw_heat_excess`
- `hw_rolling_heat_6m`
- `hw_rolling_heat_3m`
- `hw_rolling_temp_trend_3m`
- `hw_consecutive_hot_months`
- `hw_evaporation_heat_ratio`
- `hw_heat_acceleration`

### Extreme Rainfall Features
**Mandatory** (|corr| ≥ 0.40):
- `er_flood_potential_proxy`
- `er_rainfall_intensity`
- `er_soil_saturation`
- `er_evaporation_demand_ratio`
- `er_compound_rainfall_saturation`
- `er_rainfall_momentum`
- `er_monsoon_phase_factor`
- `er_extreme_precipitation_index`
- `er_zone_rainfall_anomaly`
- `er_zone_rainfall_zscore`
- `er_rainfall_anomaly`
- `er_rainfall_zscore`
- `er_is_monsoon`
- `er_antecedent_soil_moisture`
- `er_seasonal_rainfall_deviation`
- `er_rainfall_surge`
- `er_runoff_response`

**Useful** (0.20 ≤ |corr| < 0.40):
- `er_rainfall_variability_3m`
- `er_cumulative_rain_3m`
- `er_rainfall_variability_6m`
- `er_consecutive_wet_months`

**Experimental** (|corr| < 0.20):
- `er_cumulative_rain_6m`
- `er_water_surplus`
- `er_runoff_pressure`
- `er_rainfall_acceleration`


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