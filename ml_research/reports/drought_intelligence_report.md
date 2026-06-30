# Drought Intelligence Report

## Executive Summary
A production-ready drought intelligence dataset has been engineered for the
AI Climate Digital Twin of India.

- **Total Records**: 61,182
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
rainfall_mm          1.000          0.786 -0.386  0.998          0.386
soil_moisture        0.786          1.000 -0.355  0.785          0.355
evabs               -0.386         -0.355  1.000 -0.386         -0.999
sro                  0.998          0.785 -0.386  1.000          0.386
temperature_c        0.386          0.355 -0.999  0.386          1.000
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
| Low | 18,504 | 30.2% |
| Medium | 18,262 | 29.8% |
| High | 15,246 | 24.9% |
| Extreme | 9,170 | 15.0% |

**Class Imbalance Assessment**: By design (percentile-based), distribution is
approximately balanced across Low/Medium/High/Extreme. Extreme events are
15% of data — minority class monitoring is advised during training.

---

## Feature Classification

### Mandatory (Correlation ≥ 0.50)
- `evaporation_stress`
- `rainfall_spi`
- `rainfall_deficit`
- `zone_rain_zscore`
- `zone_rain_deficit`
- `soil_moisture`
- `evaporation_pressure`
- `hydrological_stress`
- `water_availability_index`
- `rainfall_deficit_pct`
- `rainfall_mm`
- `sro`
- `sm_deficit_pct`
- `rainfall_climatology`

### Useful (0.20 ≤ Correlation < 0.50)
- `sm_zscore`
- `sm_anomaly`
- `zone_sm_zscore`
- `zone_sm_deficit`
- `sm_zone_anomaly`
- `rainfall_evap_ratio`
- `rolling_rainfall_3m`
- `drought_recovery`
- `compound_drought_stress`
- `rainfall_prev_1`
- `moisture_stress`
- `soil_moisture_prev_1`
- `sm_deficit`
- `month_sin`
- `rolling_rainfall_6m`
- `month_cos`
- `sm_trend`
- `rolling_sm_3m`
- `zone_aridity_index`
- `water_balance`
- `temperature_zscore`
- `temperature_anomaly`
- `temperature_prev_3`

### Experimental (Correlation < 0.20)
- `temperature_prev_1`
- `rolling_temp_6m`
- `rolling_temp_3m`
- `low_sm_streak`
- `month`
- `rolling_sm_6m`
- `longitude`
- `dry_month_streak`
- `temperature_stress`
- `year`
- `rainfall_prev_3`
- `heat_excess`
- `temperature_c`
- `evabs`
- `rainfall_runoff_ratio`
- `cumulative_deficit_6m`
- `cumulative_sm_deficit_3m`
- `deficit_volatility_3m`
- `latitude`
- `drought_trend`

---

## Top 20 Drought Predictors

| Rank | Feature | |Corr with CDSS| |
|------|---------|----------------|
| 1 | evaporation_stress | 0.7470 |
| 2 | rainfall_spi | 0.6745 |
| 3 | rainfall_deficit | 0.6671 |
| 4 | zone_rain_zscore | 0.6599 |
| 5 | zone_rain_deficit | 0.6591 |
| 6 | soil_moisture | 0.6457 |
| 7 | evaporation_pressure | 0.6360 |
| 8 | hydrological_stress | 0.6028 |
| 9 | water_availability_index | 0.6028 |
| 10 | rainfall_deficit_pct | 0.5663 |
| 11 | rainfall_mm | 0.5612 |
| 12 | sro | 0.5612 |
| 13 | sm_deficit_pct | 0.5177 |
| 14 | rainfall_climatology | 0.5160 |
| 15 | sm_zscore | 0.4982 |
| 16 | sm_anomaly | 0.4975 |
| 17 | zone_sm_zscore | 0.4915 |
| 18 | zone_sm_deficit | 0.4914 |
| 19 | sm_zone_anomaly | 0.4914 |
| 20 | rainfall_evap_ratio | 0.4875 |

---

## Climate Zone Observations

### Zone-level Mean Rainfall & Soil Moisture
                            rainfall_mm  soil_moisture
climate_zone                                          
Central Plateau Region           83.479          0.205
Eastern Coastal Region          101.107          0.225
Himalayan Region                 93.616          0.216
Indo-Gangetic Plains             76.061          0.195
North-East Region               145.929          0.282
Southern Peninsular Region       63.642          0.180
Thar Desert Region               21.018          0.126
Western Coastal Region          166.040          0.308
Western Ghats Region            230.957          0.383

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
