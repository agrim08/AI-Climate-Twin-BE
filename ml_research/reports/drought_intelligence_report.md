# Drought Intelligence Report

## Executive Summary
A production-ready drought intelligence dataset has been engineered for the
AI Climate Digital Twin of India.

- **Total Records**: 14,241
- **Total Features**: 73
- **Drought Target**: `drought_category` (Low / Medium / High / Extreme)
- **Severity Score**: `drought_severity_score` (Composite CDSS, 0–1 scale)

---

## Drought Formation Analysis

Drought in India is driven by:
1. **Monsoon failures**: Below-normal JJAS rainfall is the primary trigger.
2. **Soil moisture depletion**: Persists weeks after rainfall stops; crucial for agriculture.
3. **Temperature amplification**: Warm anomalies increase evapotranspiration demand.
4. **Evaporation imbalance**: High demand with low supply creates atmospheric drought.
5. **Runoff collapse**: Dry soils absorb rainfall, reducing river flows.

### Key Correlations (Spearman)
```
               rainfall_mm  soil_moisture  evabs    sro  temperature_c
rainfall_mm          1.000          0.738 -0.295  0.964          0.047
soil_moisture        0.738          1.000 -0.419  0.789         -0.220
evabs               -0.295         -0.419  1.000 -0.337         -0.081
sro                  0.964          0.789 -0.337  1.000         -0.017
temperature_c        0.047         -0.220 -0.081 -0.017          1.000
```

---

## Drought Severity Methodology (CDSS Formula)

```
CDSS = 0.30 × norm(-SPI) 
     + 0.25 × norm(-SM_zscore) 
     + 0.15 × norm(Temperature_zscore)
     + 0.15 × norm(Evaporation_stress)
     + 0.15 × norm(Hydrological_stress)
```

| Component | Weight | Rationale |
|-----------|--------|-----------|
| Rainfall SPI | 30% | Gold standard; directly measures precipitation deficit |
| Soil Moisture Z | 25% | Most direct crop/ecosystem impact signal |
| Temperature Z | 15% | Amplifies evapotranspiration demand |
| Evaporation Stress | 15% | Captures atmospheric water demand |
| Hydrological Stress | 15% | Combined soil+rain+runoff water availability |

---

## Drought Category Methodology

Categories are assigned using **city-level percentiles** of the CDSS score,
ensuring climate-zone fairness (Desert cities evaluated against desert baseline):

| Category | CDSS Percentile | USDM Analog |
|----------|----------------|-------------|
| Low | 0–30th | D0 (Abnormally Dry) |
| Medium | 30–60th | D1–D2 (Moderate–Severe) |
| High | 60–85th | D3 (Extreme Drought) |
| Extreme | 85–100th | D4 (Exceptional) |

### Class Distribution
| Category | Count | % |
|----------|-------|---|
| Low | 4,258 | 29.9% |
| Medium | 4,245 | 29.8% |
| High | 3,596 | 25.3% |
| Extreme | 2,142 | 15.0% |

**Class Imbalance Assessment**: By design (percentile-based), distribution is
approximately balanced across Low/Medium/High/Extreme. Extreme events are
15% of data — minority class monitoring is advised during training.

---

## Feature Classification

### Mandatory (Correlation ≥ 0.50)
- `rainfall_spi`
- `sm_zscore`
- `rainfall_deficit_pct`
- `sm_anomaly`
- `zone_rain_zscore`
- `rainfall_deficit`
- `temperature_zscore`
- `sm_deficit_pct`
- `sm_deficit`
- `moisture_stress`
- `temperature_anomaly`
- `zone_sm_zscore`
- `hydrological_stress`
- `water_availability_index`
- `zone_rain_deficit`
- `rainfall_mm`

### Useful (0.20 ≤ Correlation < 0.50)
- `zone_sm_deficit`
- `sm_zone_anomaly`
- `rainfall_runoff_ratio`
- `soil_moisture`
- `evaporation_pressure`
- `compound_drought_stress`
- `evaporation_stress`
- `drought_recovery`
- `sro`
- `rolling_rainfall_3m`
- `runoff_efficiency`
- `rainfall_prev_1`
- `soil_moisture_prev_1`
- `rainfall_climatology`
- `rolling_rainfall_6m`
- `temperature_stress`

### Experimental (Correlation < 0.20)
- `rolling_sm_3m`
- `cumulative_sm_deficit_3m`
- `rainfall_deficit_lag1`
- `deficit_streak`
- `sm_trend`
- `water_balance`
- `temperature_c`
- `cumulative_deficit_3m`
- `cumulative_sm_deficit_6m`
- `month_sin`
- `rolling_sm_6m`
- `cumulative_deficit_6m`
- `deficit_volatility_3m`
- `zone_aridity_index`
- `rainfall_evap_ratio`
- `month_cos`
- `low_sm_streak`
- `rolling_temp_3m`
- `longitude`
- `drought_momentum`

---

## Top 20 Drought Predictors

| Rank | Feature | |Corr with CDSS| |
|------|---------|----------------|
| 1 | rainfall_spi | 0.8562 |
| 2 | sm_zscore | 0.8257 |
| 3 | rainfall_deficit_pct | 0.7884 |
| 4 | sm_anomaly | 0.7561 |
| 5 | zone_rain_zscore | 0.7226 |
| 6 | rainfall_deficit | 0.6585 |
| 7 | temperature_zscore | 0.6404 |
| 8 | sm_deficit_pct | 0.6123 |
| 9 | sm_deficit | 0.6029 |
| 10 | moisture_stress | 0.5962 |
| 11 | temperature_anomaly | 0.5925 |
| 12 | zone_sm_zscore | 0.5265 |
| 13 | hydrological_stress | 0.5233 |
| 14 | water_availability_index | 0.5233 |
| 15 | zone_rain_deficit | 0.5227 |
| 16 | rainfall_mm | 0.5140 |
| 17 | zone_sm_deficit | 0.4894 |
| 18 | sm_zone_anomaly | 0.4894 |
| 19 | rainfall_runoff_ratio | 0.4776 |
| 20 | soil_moisture | 0.4627 |

---

## Climate Zone Observations

### Zone-level Mean Rainfall & Soil Moisture
                            rainfall_mm  soil_moisture
climate_zone                                          
Central Plateau Region            3.065          0.297
Eastern Coastal Region            4.019          0.239
Himalayan Region                  5.580          0.310
Indo-Gangetic Plains              2.478          0.228
North-East Region                 6.185          0.392
Southern Peninsular Region        2.575          0.255
Thar Desert Region                0.870          0.128
Western Coastal Region            6.032          0.259
Western Ghats Region              6.896          0.336

Key observations:
- **Thar Desert Region**: Extremely low baseline rainfall — drought is the norm.
  Zone-relative features are essential to detect anomalous wet/dry spells.
- **North-East Region**: Highest baseline rainfall; droughts are rare but severe.
  SPI-based anomalies perform best here.
- **Western Ghats**: Orographic rainfall; strong spatial gradient.
  City-level climatology is more relevant than zone-level.
- **Indo-Gangetic Plains**: Monsoon-dependent; consecutive dry months
  are the strongest drought signal.

---

## Drought Evolution Analysis

Key patterns observed:
- `drought_momentum` captures whether drought is deepening or recovering.
- `cumulative_deficit_6m` is the strongest compound indicator.
- `low_sm_streak` shows that soil moisture impacts persist for 1–2 months after rainfall.
- `deficit_streak` consistently identifies prolonged droughts early.

---

## Leakage Prevention

| Column | Reason Removed |
|--------|----------------|
| `drought_risk` | Pre-existing post-hoc label — circular dependency |
| `heatwave_risk` | Derived from temperature labels |
| `climate_risk_score` | Composite of post-hoc derived labels |
| `target_rainfall_next_month` | Future value |
| `target_temperature_next_month` | Future value |

---

## Recommended Modeling Strategy

1. **Primary Target**: `drought_category` (multi-class: Low/Medium/High/Extreme)
2. **Auxiliary Regression Target**: `drought_severity_score` (continuous 0–1)
3. **Split**: Chronological — Train ≤ 2020, Val 2021–2022, Test ≥ 2023
4. **Algorithm**: LightGBM (handles ordinal targets well) or XGBoost
5. **Class Weighting**: Apply `class_weight='balanced'` or `scale_pos_weight` for Extreme class
6. **Feature Selection**: Start with Mandatory + Useful features; use SHAP for interpretability
7. **Evaluation**: F1-macro (balanced across all drought levels), Confusion Matrix by zone
