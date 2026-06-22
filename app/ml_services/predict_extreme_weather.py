import os
import json
import logging
import joblib
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
CLASS_ORDER = ["Low", "Medium", "High", "Extreme"]
LABEL_DECODER = {i: c for i, c in enumerate(CLASS_ORDER)}

MODEL_FEATURES_HW = [
    'latitude', 'longitude', 'year', 'month', 'temperature_c', 'rainfall_mm', 'soil_moisture', 'evabs', 'sro',
    'month_sin', 'month_cos', 'temperature_prev_1', 'temperature_prev_3', 'rainfall_prev_1', 'rainfall_prev_3',
    'soil_moisture_prev_1', 'rolling_temp_3m', 'rolling_rainfall_3m', 'rolling_temp_6m', 'rolling_rainfall_6m',
    'hw_temperature_anomaly', 'hw_temperature_zscore', 'hw_heat_excess', 'hw_heat_stress', 'hw_heatwave_intensity',
    'hw_rolling_heat_3m', 'hw_rolling_heat_6m', 'hw_consecutive_hot_months', 'hw_heat_acceleration',
    'hw_dry_heat_indicator', 'hw_rainfall_heat_interaction', 'hw_soil_heat_interaction', 'hw_evaporation_heat_ratio',
    'hw_climate_zone_heat_anomaly', 'hw_zone_temp_zscore', 'hw_seasonal_heat_deviation', 'hw_rolling_temp_trend_3m',
    'hw_apparent_temperature', 'hw_apparent_temp_anomaly', 'hw_compound_heat_drought'
]

MODEL_FEATURES_ER = [
    'latitude', 'longitude', 'year', 'month', 'temperature_c', 'rainfall_mm', 'soil_moisture', 'evabs', 'sro',
    'month_sin', 'month_cos', 'temperature_prev_1', 'temperature_prev_3', 'rainfall_prev_1', 'rainfall_prev_3',
    'soil_moisture_prev_1', 'rolling_temp_3m', 'rolling_rainfall_3m', 'rolling_temp_6m', 'rolling_rainfall_6m',
    'er_rainfall_anomaly', 'er_rainfall_zscore', 'er_rainfall_intensity', 'er_rainfall_surge', 'er_rainfall_acceleration',
    'er_rainfall_momentum', 'er_rainfall_variability_3m', 'er_rainfall_variability_6m', 'er_extreme_precipitation_index',
    'er_runoff_pressure', 'er_runoff_response', 'er_soil_saturation', 'er_flood_potential_proxy', 'er_antecedent_soil_moisture',
    'er_water_surplus', 'er_zone_rainfall_anomaly', 'er_zone_rainfall_zscore', 'er_seasonal_rainfall_deviation',
    'er_cumulative_rain_3m', 'er_cumulative_rain_6m', 'er_consecutive_wet_months', 'er_is_monsoon', 'er_monsoon_phase_factor',
    'er_evaporation_demand_ratio', 'er_compound_rainfall_saturation'
]

FEATURE_IMPORTANCES_HW = {
    'hw_heat_stress': 0.116, 'hw_rainfall_heat_interaction': 0.087, 'hw_compound_heat_drought': 0.079,
    'hw_temperature_zscore': 0.075, 'hw_soil_heat_interaction': 0.043, 'evabs': 0.039, 'rainfall_mm': 0.038,
    'hw_temperature_anomaly': 0.033, 'hw_evaporation_heat_ratio': 0.031, 'sro': 0.028, 'month_cos': 0.028
}

FEATURE_IMPORTANCES_ER = {
    'er_rainfall_anomaly': 2230, 'longitude': 2009, 'latitude': 1457, 'soil_moisture': 1343,
    'er_rainfall_momentum': 1318, 'er_rainfall_acceleration': 1260, 'er_flood_potential_proxy': 1115,
    'er_soil_saturation': 908, 'er_rainfall_intensity': 201, 'er_runoff_pressure': 737
}

class ExtremeWeatherPredictor:
    """
    Production-ready Extreme Weather Intelligence Layer service.
    Features dual classifiers, severity regressors, chained digital twin controls,
    driver diagnostics, early warning thresholds, and FastAPI endpoints.
    """
    
    def __init__(self, model_dir: str = None):
        if model_dir is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            model_dir = os.path.join(script_dir, "models")
            
        self.model_hw_path = os.path.join(model_dir, "heatwave.pkl")
        self.model_er_path = os.path.join(model_dir, "extreme_rainfall.pkl")
        self.model_hw_reg_path = os.path.join(model_dir, "heatwave_severity.pkl")
        self.model_er_reg_path = os.path.join(model_dir, "extreme_rainfall_severity.pkl")
        
        self.model_hw = None
        self.model_er = None
        self.model_hw_reg = None
        self.model_er_reg = None
        
        # Load core models
        self.load_models()
        
        # Lazy load Temperature and Rainfall predictors for chained Digital Twin simulation workflows
        self.temp_predictor = None
        self.rain_predictor = None
        try:
            from app.ml_services.predict_temperature import TemperaturePredictor
            from app.ml_services.predict_rainfall import RainfallPredictor
            self.temp_predictor = TemperaturePredictor(model_dir)
            self.rain_predictor = RainfallPredictor(model_dir)
            logger.info("Extreme Weather Chained Digital Twin Workflow initialized.")
        except Exception as e:
            logger.warning(
                f"Failed to load Temperature/Rainfall predictors for simulation chaining: {str(e)}. "
                "Digital Twin scenario testing will fallback to direct delta math."
            )

    def load_models(self):
        """Loads serialized XGBoost and LightGBM classifiers and regressors."""
        try:
            logger.info(f"Loading Heatwave model: {self.model_hw_path}")
            self.model_hw = joblib.load(self.model_hw_path)
            
            logger.info(f"Loading Extreme Rainfall model: {self.model_er_path}")
            self.model_er = joblib.load(self.model_er_path)
            
            logger.info(f"Loading Heatwave Severity Regressor: {self.model_hw_reg_path}")
            self.model_hw_reg = joblib.load(self.model_hw_reg_path)
            
            logger.info(f"Loading Extreme Rainfall Severity Regressor: {self.model_er_reg_path}")
            self.model_er_reg = joblib.load(self.model_er_reg_path)
            
            logger.info("All Extreme Weather Models loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load extreme weather models: {str(e)}")
            raise RuntimeError(f"Extreme Weather Models initialization failed: {str(e)}")

    def prepare_heatwave_features(self, req: Dict[str, Any], apply_deltas: bool = True) -> Dict[str, float]:
        """Dynamically prepares the 40 feature matrix inputs for the Heatwave Classifier & Regressor."""
        # Deltas
        t_delta = float(req.get("temperature_delta", 0.0)) if apply_deltas else 0.0
        r_delta = float(req.get("rainfall_delta", 0.0)) if apply_deltas else 0.0
        sm_delta = float(req.get("soil_moisture_delta", 0.0)) if apply_deltas else 0.0
        evap_delta = float(req.get("evaporation_delta", 0.0)) if apply_deltas else 0.0
        ro_delta = float(req.get("runoff_delta", 0.0)) if apply_deltas else 0.0

        # Base variables
        temperature_c = float(req.get("temperature_c", 30.0)) + t_delta
        rainfall_mm = max(0.0, float(req.get("rainfall_mm", 10.0)) * (1.0 + r_delta / 100.0))
        soil_moisture = max(0.0, min(1.0, float(req.get("soil_moisture", 0.2)) * (1.0 + sm_delta / 100.0)))
        evabs = float(req.get("evabs", -0.001)) * (1.0 + evap_delta / 100.0)
        sro = max(0.0, float(req.get("sro", 0.001)) * (1.0 + ro_delta / 100.0))

        # Climatologies
        temp_climo_mean = float(req.get("temp_climo_mean", 28.0))
        temp_climo_std = max(0.1, float(req.get("temp_climo_std", 2.0)))
        rain_climo_mean = float(req.get("rain_climo_mean", 12.0))
        zone_temp_std = max(0.1, float(req.get("zone_temp_std", 2.0)))
        zone_temp_mean = float(req.get("zone_temp_mean", 28.0))
        seasonal_temp_mean = float(req.get("seasonal_temp_mean", 28.0))
        sm_climo_mean = float(req.get("sm_climo_mean", 0.25))

        f = {
            'latitude': float(req.get("latitude", 20.0)),
            'longitude': float(req.get("longitude", 80.0)),
            'year': int(req.get("year", 2024)),
            'month': int(req.get("month", 6)),
            'temperature_c': temperature_c,
            'rainfall_mm': rainfall_mm,
            'soil_moisture': soil_moisture,
            'evabs': evabs,
            'sro': sro,
            'month_sin': float(req.get("month_sin", 0.0)),
            'month_cos': float(req.get("month_cos", 1.0)),
            'temperature_prev_1': float(req.get("temperature_prev_1", 29.0)),
            'temperature_prev_3': float(req.get("temperature_prev_3", 28.0)),
            'rainfall_prev_1': float(req.get("rainfall_prev_1", 5.0)),
            'rainfall_prev_3': float(req.get("rainfall_prev_3", 2.0)),
            'soil_moisture_prev_1': float(req.get("soil_moisture_prev_1", 0.18)),
            'rolling_temp_3m': float(req.get("rolling_temp_3m", 28.5)),
            'rolling_rainfall_3m': float(req.get("rolling_rainfall_3m", 15.0)),
            'rolling_temp_6m': float(req.get("rolling_temp_6m", 25.0)),
            'rolling_rainfall_6m': float(req.get("rolling_rainfall_6m", 30.0))
        }

        # Calculations
        f['hw_temperature_anomaly'] = temperature_c - temp_climo_mean
        f['hw_temperature_zscore'] = np.clip(f['hw_temperature_anomaly'] / temp_climo_std, -5.0, 5.0)
        f['hw_heat_excess'] = max(0.0, temperature_c - 35.0)
        
        rain_norm = np.clip(rainfall_mm / (rain_climo_mean + 1e-6), 0.0, 2.0)
        f['hw_heat_stress'] = f['hw_temperature_anomaly'] * max(0.0, 2.0 - rain_norm)
        f['hw_heatwave_intensity'] = np.clip(max(0.0, f['hw_temperature_anomaly']) / (zone_temp_std + 1e-6), 0.0, 5.0)
        
        f['hw_rolling_heat_3m'] = float(req.get("hw_rolling_heat_3m", 0.0))
        f['hw_rolling_heat_6m'] = float(req.get("hw_rolling_heat_6m", 0.0))
        f['hw_consecutive_hot_months'] = float(req.get("consecutive_hot_months", 0.0))
        f['hw_heat_acceleration'] = f['hw_rolling_heat_3m'] - f['hw_rolling_heat_6m']
        
        sm_norm = np.clip(soil_moisture / 0.5, 0.0, 1.0)
        f['hw_dry_heat_indicator'] = f['hw_heat_excess'] * (1.0 - sm_norm)
        f['hw_rainfall_heat_interaction'] = max(0.0, f['hw_temperature_anomaly']) * max(0.0, 1.0 - rain_norm)
        
        sm_deficit = max(0.0, sm_climo_mean - soil_moisture)
        f['hw_soil_heat_interaction'] = max(0.0, f['hw_temperature_anomaly']) * sm_deficit
        
        evap_mag = abs(evabs) * 30.44 * 1000
        f['hw_evaporation_heat_ratio'] = np.clip(evap_mag / (abs(temperature_c) + 1.0), 0.0, 20.0)
        
        f['hw_climate_zone_heat_anomaly'] = temperature_c - zone_temp_mean
        f['hw_zone_temp_zscore'] = np.clip(f['hw_climate_zone_heat_anomaly'] / (zone_temp_std + 1e-6), -5.0, 5.0)
        f['hw_seasonal_heat_deviation'] = temperature_c - seasonal_temp_mean
        f['hw_rolling_temp_trend_3m'] = float(req.get("hw_rolling_temp_trend_3m", 0.0))

        # Apparent temperature calculation
        humidity_proxy = np.clip(soil_moisture * 100.0, 20.0, 95.0)
        h_frac = humidity_proxy / 100.0
        f['hw_apparent_temperature'] = np.clip(
            -8.78469475556
            + 1.61139411 * temperature_c
            + 2.33854883889 * h_frac
            - 0.14611605 * temperature_c * h_frac
            - 0.012308094 * (temperature_c ** 2)
            - 0.0164248277778 * (h_frac ** 2)
            + 0.002211732 * (temperature_c ** 2) * h_frac
            + 0.00072546 * temperature_c * (h_frac ** 2)
            - 0.000003582 * (temperature_c ** 2) * (h_frac ** 2),
            temperature_c, 55.0
        )
        f['hw_apparent_temp_anomaly'] = f['hw_apparent_temperature'] - temp_climo_mean
        f['hw_compound_heat_drought'] = max(0.0, f['hw_temperature_anomaly']) * sm_deficit * max(0.0, 1.0 - rain_norm)
        
        return f

    def prepare_extreme_rainfall_features(self, req: Dict[str, Any], apply_deltas: bool = True) -> Dict[str, float]:
        """Dynamically prepares the 45 feature matrix inputs for the Extreme Rainfall Classifier & Regressor."""
        # Deltas
        t_delta = float(req.get("temperature_delta", 0.0)) if apply_deltas else 0.0
        r_delta = float(req.get("rainfall_delta", 0.0)) if apply_deltas else 0.0
        sm_delta = float(req.get("soil_moisture_delta", 0.0)) if apply_deltas else 0.0
        evap_delta = float(req.get("evaporation_delta", 0.0)) if apply_deltas else 0.0
        ro_delta = float(req.get("runoff_delta", 0.0)) if apply_deltas else 0.0

        # Base variables
        temperature_c = float(req.get("temperature_c", 30.0)) + t_delta
        rainfall_mm = max(0.0, float(req.get("rainfall_mm", 10.0)) * (1.0 + r_delta / 100.0))
        soil_moisture = max(0.0, min(1.0, float(req.get("soil_moisture", 0.2)) * (1.0 + sm_delta / 100.0)))
        evabs = float(req.get("evabs", -0.001)) * (1.0 + evap_delta / 100.0)
        sro = max(0.0, float(req.get("sro", 0.001)) * (1.0 + ro_delta / 100.0))

        # Climatologies
        rain_climo_mean = float(req.get("rain_climo_mean", 12.0))
        rain_climo_std = max(0.01, float(req.get("rain_climo_std", 5.0)))
        zone_rain_mean = float(req.get("zone_rain_mean", 12.0))
        zone_rain_std = max(0.01, float(req.get("zone_rain_std", 5.0)))
        seasonal_rain_mean = float(req.get("seasonal_rain_mean", 12.0))

        f = {
            'latitude': float(req.get("latitude", 20.0)),
            'longitude': float(req.get("longitude", 80.0)),
            'year': int(req.get("year", 2024)),
            'month': int(req.get("month", 6)),
            'temperature_c': temperature_c,
            'rainfall_mm': rainfall_mm,
            'soil_moisture': soil_moisture,
            'evabs': evabs,
            'sro': sro,
            'month_sin': float(req.get("month_sin", 0.0)),
            'month_cos': float(req.get("month_cos", 1.0)),
            'temperature_prev_1': float(req.get("temperature_prev_1", 29.0)),
            'temperature_prev_3': float(req.get("temperature_prev_3", 28.0)),
            'rainfall_prev_1': float(req.get("rainfall_prev_1", 5.0)),
            'rainfall_prev_3': float(req.get("rainfall_prev_3", 2.0)),
            'soil_moisture_prev_1': float(req.get("soil_moisture_prev_1", 0.18)),
            'rolling_temp_3m': float(req.get("rolling_temp_3m", 28.5)),
            'rolling_rainfall_3m': float(req.get("rolling_rainfall_3m", 15.0)),
            'rolling_temp_6m': float(req.get("rolling_temp_6m", 25.0)),
            'rolling_rainfall_6m': float(req.get("rolling_rainfall_6m", 30.0))
        }

        # Calculations
        f['er_rainfall_anomaly'] = rainfall_mm - rain_climo_mean
        f['er_rainfall_zscore'] = np.clip(f['er_rainfall_anomaly'] / rain_climo_std, -5.0, 5.0)
        f['er_rainfall_intensity'] = rainfall_mm / 30.44
        f['er_rainfall_surge'] = rainfall_mm - f['rolling_rainfall_3m']
        
        # Trends
        short_trend = rainfall_mm - f['rolling_rainfall_3m']
        long_trend = f['rolling_rainfall_3m'] - f['rolling_rainfall_6m']
        f['er_rainfall_acceleration'] = short_trend - long_trend
        f['er_rainfall_momentum'] = rainfall_mm - f['rolling_rainfall_6m']
        
        f['er_rainfall_variability_3m'] = float(req.get("er_rainfall_variability_3m", 0.0))
        f['er_rainfall_variability_6m'] = float(req.get("er_rainfall_variability_6m", 0.0))
        f['er_extreme_precipitation_index'] = max(0.0, f['er_rainfall_zscore'])
        
        sro_mm = sro * 1000.0
        f['er_runoff_pressure'] = np.clip(sro_mm / (rainfall_mm + 1e-6), 0.0, 5.0)
        f['er_runoff_response'] = np.clip(sro_mm, 0.0, 50.0)
        f['er_soil_saturation'] = np.clip(soil_moisture / 0.45, 0.0, 1.0)
        
        f['er_flood_potential_proxy'] = np.clip(
            np.clip(rainfall_mm / (rain_climo_mean + 1e-6), 0.0, 5.0)
            * np.clip(f['er_runoff_pressure'], 0.0, 3.0)
            * f['er_soil_saturation'],
            0.0, 10.0
        )
        f['er_antecedent_soil_moisture'] = float(req.get("er_antecedent_soil_moisture", 0.2))
        
        evap_mm = abs(evabs) * 30.44 * 1000
        f['er_water_surplus'] = max(-500.0, rainfall_mm - evap_mm - sro_mm)
        
        f['er_zone_rainfall_anomaly'] = rainfall_mm - zone_rain_mean
        f['er_zone_rainfall_zscore'] = np.clip(f['er_zone_rainfall_anomaly'] / (zone_rain_std + 1e-6), -5.0, 5.0)
        f['er_seasonal_rainfall_deviation'] = rainfall_mm - seasonal_rain_mean
        f['er_cumulative_rain_3m'] = float(req.get("er_cumulative_rain_3m", 0.0))
        f['er_cumulative_rain_6m'] = float(req.get("er_cumulative_rain_6m", 0.0))
        f['er_consecutive_wet_months'] = float(req.get("consecutive_wet_months", 0.0))
        f['er_is_monsoon'] = 1 if int(req.get("month", 6)) in [6, 7, 8, 9] else 0
        f['er_monsoon_phase_factor'] = max(0.0, np.sin(np.pi * (int(req.get("month", 6)) - 4) / 6))
        f['er_evaporation_demand_ratio'] = np.clip(evap_mm / (rainfall_mm + 1e-6), 0.0, 20.0)
        f['er_compound_rainfall_saturation'] = np.clip(max(0.0, f['er_rainfall_zscore']) * f['er_soil_saturation'], 0.0, 5.0)
        
        return f

    def predict(self, request: Dict[str, Any], apply_deltas: bool = True) -> Dict[str, Any]:
        """Calculates single predictions for both Heatwave & Extreme Rainfall."""
        try:
            # 1. Heatwave Predictions
            hw_feats = self.prepare_heatwave_features(request, apply_deltas=apply_deltas)
            df_hw = pd.DataFrame([hw_feats])[MODEL_FEATURES_HW]
            
            hw_pred_idx = int(self.model_hw.predict(df_hw)[0])
            hw_probs = self.model_hw.predict_proba(df_hw)[0]
            hw_sev_raw = float(self.model_hw_reg.predict(df_hw)[0])
            
            hw_category = LABEL_DECODER[hw_pred_idx]
            hw_severity = round(max(0.0, min(100.0, hw_sev_raw * 100.0)), 1)
            hw_confidence = round(float(hw_probs[hw_pred_idx]), 3)

            # 2. Extreme Rainfall Predictions
            er_feats = self.prepare_extreme_rainfall_features(request, apply_deltas=apply_deltas)
            df_er = pd.DataFrame([er_feats])[MODEL_FEATURES_ER]
            
            er_pred_idx = int(self.model_er.predict(df_er)[0])
            er_probs = self.model_er.predict_proba(df_er)[0]
            er_sev_raw = float(self.model_er_reg.predict(df_er)[0])
            
            er_category = LABEL_DECODER[er_pred_idx]
            er_severity = round(max(0.0, min(100.0, er_sev_raw * 100.0)), 1)
            er_confidence = round(float(er_probs[er_pred_idx]), 3)

            return {
                "heatwave": {
                    "category": hw_category,
                    "severity": hw_severity,
                    "confidence": hw_confidence,
                    "_probabilities": hw_probs,  # Private fields for internal cascading logic
                    "_features": hw_feats
                },
                "extreme_rainfall": {
                    "category": er_category,
                    "severity": er_severity,
                    "confidence": er_confidence,
                    "_probabilities": er_probs,
                    "_features": er_feats
                },
                "source": request.get("source"),
                "confidence_source": request.get("confidence_source"),
                "last_updated": request.get("last_updated")
            }
        except Exception as e:
            logger.error(f"Extreme weather prediction failed: {str(e)}", exc_info=True)
            raise RuntimeError(f"Prediction execution failed: {str(e)}")

    def batch_predict(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Processes multiple prediction payloads in bulk."""
        if not requests:
            return []
        logger.info(f"Processing batch extreme weather prediction for {len(requests)} items.")
        try:
            results = []
            for req in requests:
                res = self.predict(req, apply_deltas=True)
                # Strip out private helper keys before returning to user
                res["heatwave"].pop("_probabilities", None)
                res["heatwave"].pop("_features", None)
                res["extreme_rainfall"].pop("_probabilities", None)
                res["extreme_rainfall"].pop("_features", None)
                results.append(res)
            return results
        except Exception as e:
            logger.error(f"Batch prediction failed: {str(e)}", exc_info=True)
            raise

    def calculate_overall_risk(
        self, hw_out: Dict[str, Any], er_out: Dict[str, Any], hw_probs: np.ndarray, er_probs: np.ndarray
    ) -> Dict[str, Any]:
        """
        Implements a transparent risk aggregation strategy:
        Risk = 80% Max(HW_Sev, ER_Sev) + 20% Mean(HW_Sev, ER_Sev) + 10% Compound Event Penalty.
        """
        hw_sev = hw_out["severity"]
        er_sev = er_out["severity"]
        
        # Core score
        max_sev = max(hw_sev, er_sev)
        mean_sev = (hw_sev + er_sev) / 2.0
        overall_score = 0.8 * max_sev + 0.2 * mean_sev
        
        # Compound event penalty (if both are severe probability-wise)
        # Severe probability = P(High) + P(Extreme)
        p_hw_severe = float(hw_probs[2] + hw_probs[3])
        p_er_severe = float(er_probs[2] + er_probs[3])
        
        if p_hw_severe > 0.35 and p_er_severe > 0.35:
            overall_score += 10.0
            
        overall_score = round(max(0.0, min(100.0, overall_score)), 1)
        
        # Risk levels mapping
        if overall_score < 35.0:
            overall_risk = "Low"
        elif overall_score < 60.0:
            overall_risk = "Medium"
        elif overall_score < 80.0:
            overall_risk = "High"
        else:
            overall_risk = "Extreme"
            
        return {
            "overall_extreme_weather_risk": overall_risk,
            "overall_risk_score": overall_score
        }

    def simulate_scenario(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs baseline scenario vs simulated delta scenario.
        Optionally chains predictions through Temperature and Rainfall services if loaded.
        """
        # --- 1. Compute Baseline Risk ---
        baseline_req = request.copy()
        for k in ["temperature_delta", "rainfall_delta", "soil_moisture_delta", "evaporation_delta", "runoff_delta"]:
            baseline_req[k] = 0.0
            
        b_res = self.predict(baseline_req, apply_deltas=False)
        b_risk = self.calculate_overall_risk(
            b_res["heatwave"], b_res["extreme_rainfall"],
            b_res["heatwave"]["_probabilities"], b_res["extreme_rainfall"]["_probabilities"]
        )

        # --- 2. Compute Scenario Risk ---
        scenario_req = request.copy()
        chained_run = False
        
        # Preferred chained Digital Twin workflow
        if self.temp_predictor is not None and self.rain_predictor is not None:
            try:
                # Step A: Predict temperature with delta
                temp_out = self.temp_predictor.predict(scenario_req)
                t_delta = float(scenario_req.get("temperature_delta", 0.0))
                scenario_req["temperature_c"] = temp_out["predicted_temperature_c"] + t_delta
                
                # Step B: Predict rainfall using updated temperature + rainfall_delta
                rain_out = self.rain_predictor.predict(scenario_req)
                r_delta = float(scenario_req.get("rainfall_delta", 0.0))
                scenario_req["rainfall_mm"] = max(0.0, rain_out["predicted_rainfall_mm"] * (1.0 + r_delta / 100.0))
                
                # Step C: Scale soil moisture, evaporation, and runoff
                sm_d = float(scenario_req.get("soil_moisture_delta", 0.0))
                evap_d = float(scenario_req.get("evaporation_delta", 0.0))
                ro_d = float(scenario_req.get("runoff_delta", 0.0))
                
                scenario_req["soil_moisture"] = max(0.0, float(scenario_req.get("soil_moisture", 0.2)) * (1.0 + sm_d / 100.0))
                scenario_req["evabs"] = float(scenario_req.get("evabs", -0.001)) * (1.0 + evap_d / 100.0)
                scenario_req["sro"] = max(0.0, float(scenario_req.get("sro", 0.001)) * (1.0 + ro_d / 100.0))
                
                # Disable deltas in prepare features since they have been cascaded through the chained models
                s_res = self.predict(scenario_req, apply_deltas=False)
                chained_run = True
                logger.info("Chained scenario simulation completed successfully.")
            except Exception as e:
                logger.warning(f"Chained simulation pipeline failed: {str(e)}. Falling back to direct deltas.")
                
        if not chained_run:
            # Fallback direct math
            s_res = self.predict(scenario_req, apply_deltas=True)
            
        s_risk = self.calculate_overall_risk(
            s_res["heatwave"], s_res["extreme_rainfall"],
            s_res["heatwave"]["_probabilities"], s_res["extreme_rainfall"]["_probabilities"]
        )

        # Risk level change diff
        lvl_map = {"Low": 0, "Medium": 1, "High": 2, "Extreme": 3}
        diff = lvl_map[s_risk["overall_extreme_weather_risk"]] - lvl_map[b_risk["overall_extreme_weather_risk"]]
        
        if diff > 0:
            risk_change = f"+{diff} level{'s' if diff > 1 else ''}"
        elif diff < 0:
            risk_change = f"{diff} level{'s' if abs(diff) > 1 else ''}"
        else:
            risk_change = "No change"

        return {
            "baseline_risk": b_risk["overall_extreme_weather_risk"],
            "baseline_score": b_risk["overall_risk_score"],
            "scenario_risk": s_risk["overall_extreme_weather_risk"],
            "scenario_score": s_risk["overall_risk_score"],
            "risk_change": risk_change
        }

    def get_heatwave_impact(self, severity: float, temp_anomaly: float, probs: np.ndarray) -> Dict[str, Any]:
        """Generates health-oriented heatwave impacts & advisories."""
        p_severe = float(probs[2] + probs[3])
        
        # Health Risk
        if severity > 70.0 or (temp_anomaly > 5.0 and p_severe > 0.75):
            h_risk = "Extreme"
        elif severity > 45.0 or temp_anomaly > 3.0:
            h_risk = "High"
        elif severity > 20.0:
            h_risk = "Medium"
        else:
            h_risk = "Low"

        # Outdoor Exposure Safety Risk
        if temp_anomaly > 4.5 and severity > 50.0:
            oe_risk = "Extreme"
        elif temp_anomaly > 2.5 or severity > 35.0:
            oe_risk = "High"
        elif severity > 15.0:
            oe_risk = "Medium"
        else:
            oe_risk = "Low"

        # Alert level
        alert_map = {"Extreme": "Red", "High": "Orange", "Medium": "Yellow", "Low": "Green"}
        alert = alert_map[h_risk]

        # Actionable advice
        advise = []
        if alert == "Red":
            advise.append("RED ALERT: Extreme hazard. Avoid all outdoor exposures. Keep room ventilation active.")
            advise.append("Monitor high-risk individuals (elderly, children) for signs of heatstroke.")
        elif alert == "Orange":
            advise.append("ORANGE ALERT: High hazard. Drink water regularly, minimize outdoor strenuous labor.")
            advise.append("Avoid direct sun exposures between 11:00 AM and 4:00 PM.")
        elif alert == "Yellow":
            advise.append("YELLOW ALERT: Stay updated on local temperatures. Seek shade and keep hydrated.")
        else:
            advise.append("Normal conditions. Standard hydration recommended.")

        return {
            "health_risk": h_risk,
            "outdoor_exposure_risk": oe_risk,
            "heat_alert_level": alert,
            "recommendations": advise
        }

    def get_extreme_rainfall_impact(
        self, severity: float, runoff_pressure: float, soil_saturation: float, rain_anomaly: float
    ) -> Dict[str, Any]:
        """Generates flood-oriented extreme rainfall impacts & advisories."""
        # Flash Flood Risk
        if severity > 70.0 or (soil_saturation > 0.90 and runoff_pressure > 0.80 and severity > 50.0):
            ff_risk = "Extreme"
        elif severity > 45.0 or (soil_saturation > 0.75 and runoff_pressure > 0.50):
            ff_risk = "High"
        elif severity > 20.0:
            ff_risk = "Medium"
        else:
            ff_risk = "Low"

        # Surface Runoff Risk
        if runoff_pressure > 0.85 and severity > 50.0:
            ro_risk = "Extreme"
        elif runoff_pressure > 0.50 or severity > 35.0:
            ro_risk = "High"
        elif severity > 15.0:
            ro_risk = "Medium"
        else:
            ro_risk = "Low"

        # Drainage Overload
        if severity > 65.0 and rain_anomaly > 100.0:
            dr_risk = "Extreme"
        elif severity > 40.0 or rain_anomaly > 50.0:
            dr_risk = "High"
        elif severity > 15.0:
            dr_risk = "Medium"
        else:
            dr_risk = "Low"

        advise = []
        if ff_risk in ["High", "Extreme"]:
            advise.append("CRITICAL: Extreme flood alert. Evacuate low-lying zones immediately.")
            advise.append("Do NOT attempt to cross flooded roadways or waterlogged bridges.")
        elif ro_risk == "High":
            advise.append("HIGH RUNOFF: Soil is highly saturated. Landslides/surface flows highly probable in sloped regions.")
        elif dr_risk == "Medium":
            advise.append("DRAINAGE ALERT: Expect temporary localized street flooding in urban areas.")
        else:
            advise.append("Normal/sufficient drainage capacity observed.")

        return {
            "flash_flood_risk": ff_risk,
            "surface_runoff_risk": ro_risk,
            "drainage_overload_risk": dr_risk,
            "recommendations": advise
        }

    def analyze_drivers(self, hw_feats: Dict[str, float], er_feats: Dict[str, float]) -> List[str]:
        """Extracts the leading physical drivers by multiplying local anomalies with global feature importance."""
        # 1. Temperature Anomaly Driver
        temp_anom = max(0.0, hw_feats.get('hw_temperature_anomaly', 0.0))
        t_score = temp_anom * FEATURE_IMPORTANCES_HW.get('hw_temperature_anomaly', 0.033)
        
        # 2. Heat Stress Driver
        h_stress = max(0.0, hw_feats.get('hw_heat_stress', 0.0))
        hs_score = h_stress * FEATURE_IMPORTANCES_HW.get('hw_heat_stress', 0.116)
        
        # 3. Soil Moisture Deficit Driver
        sm_climo = hw_feats.get('sm_climo_mean', 0.25)
        sm = hw_feats.get('soil_moisture', 0.20)
        sm_deficit = max(0.0, sm_climo - sm)
        sm_score = sm_deficit * 5.0 * FEATURE_IMPORTANCES_HW.get('hw_soil_heat_interaction', 0.043)
        
        # 4. Rainfall Deficit Driver
        rain_climo = hw_feats.get('rain_climo_mean', 12.0)
        rain = hw_feats.get('rainfall_mm', 10.0)
        r_deficit = max(0.0, rain_climo - rain)
        rd_score = r_deficit * 0.05 * FEATURE_IMPORTANCES_HW.get('hw_rainfall_heat_interaction', 0.087)

        # 5. Rainfall Anomaly Driver (ER)
        er_anom = max(0.0, er_feats.get('er_rainfall_anomaly', 0.0))
        era_score = (er_anom / 50.0) * FEATURE_IMPORTANCES_ER.get('er_rainfall_anomaly', 2230)
        
        # 6. Runoff Pressure Driver
        ro_press = er_feats.get('er_runoff_pressure', 0.0)
        ro_score = ro_press * 5.0 * FEATURE_IMPORTANCES_ER.get('er_runoff_pressure', 737)
        
        # 7. Soil Saturation Driver
        soil_sat = er_feats.get('er_soil_saturation', 0.0)
        sat_score = soil_sat * 2.0 * FEATURE_IMPORTANCES_ER.get('er_soil_saturation', 908)
        
        # 8. Rainfall Intensity Driver
        intensity = er_feats.get('er_rainfall_intensity', 0.0)
        ri_score = intensity * 30.0 * FEATURE_IMPORTANCES_ER.get('er_rainfall_intensity', 201)

        drivers = [
            ("High Temperature Anomaly", t_score),
            ("Extreme Heat Stress", hs_score),
            ("Soil Moisture Deficit", sm_score),
            ("Rainfall Deficit", rd_score),
            ("Rainfall Anomaly Surge", era_score),
            ("Hydrological Runoff Pressure", ro_score),
            ("High Soil Saturation", sat_score),
            ("Intense Daily Precipitation", ri_score)
        ]
        
        # Sort and return positive score items
        drivers.sort(key=lambda x: x[1], reverse=True)
        top = [d[0] for d in drivers[:3] if d[1] > 0.0]
        return top if top else ["Low Climatic Deviations"]

    def generate_early_warning(self, hw_probs: np.ndarray, er_probs: np.ndarray) -> Dict[str, Any]:
        """Triggers emergency alerts if categorical probabilities cross warning limits."""
        # Categorical probabilities
        p_hw_med, p_hw_high, p_hw_ext = float(hw_probs[1]), float(hw_probs[2]), float(hw_probs[3])
        p_er_med, p_er_high, p_er_ext = float(er_probs[1]), float(er_probs[2]), float(er_probs[3])

        # Heatwave alert tier
        if p_hw_ext > 0.20 or (p_hw_high + p_hw_ext) > 0.65:
            hw_warn = "Critical"
        elif p_hw_ext > 0.10 or p_hw_high > 0.35:
            hw_warn = "High"
        elif p_hw_med > 0.50 or p_hw_high > 0.20:
            hw_warn = "Medium"
        else:
            hw_warn = "Low"

        # Rainfall alert tier
        if p_er_ext > 0.20 or (p_er_high + p_er_ext) > 0.65:
            er_warn = "Critical"
        elif p_er_ext > 0.10 or p_er_high > 0.35:
            er_warn = "High"
        elif p_er_med > 0.50 or p_er_high > 0.20:
            er_warn = "Medium"
        else:
            er_warn = "Low"

        # Map tiers
        tier_weight = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        max_tier = "Low"
        
        hw_w = tier_weight[hw_warn]
        er_w = tier_weight[er_warn]
        
        if hw_w > er_w:
            max_tier = hw_warn
            event_type = "Heatwave"
        elif er_w > hw_w:
            max_tier = er_warn
            event_type = "Extreme Rainfall"
        else:
            max_tier = hw_warn
            event_type = "Compound Heat-Rainfall" if hw_w > 1 else "None"

        warning_active = max_tier in ["Medium", "High", "Critical"]
        
        # Message advisory
        msg = "Routine weather conditions. Standard monitoring active."
        if warning_active:
            if event_type == "Heatwave":
                msg = f"Potential extreme heatwave event detected (confidence: {p_hw_high+p_hw_ext:.1%}). Take cooling precautions."
            elif event_type == "Extreme Rainfall":
                msg = f"Potential extreme rainfall flooding hazard detected (confidence: {p_er_high+p_er_ext:.1%}). Monitor flash floods."
            else:
                msg = f"Compound Heat & Flood hazard warning active. High stress levels detected."

        return {
            "warning": warning_active,
            "warning_level": max_tier,
            "event_type": event_type if warning_active else "None",
            "message": msg
        }

    def get_digital_twin_state(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregates all components into a single unified twin-state response payload."""
        # 1. Main Predictions
        pred_res = self.predict(request, apply_deltas=True)
        
        hw_out = pred_res["heatwave"]
        er_out = pred_res["extreme_rainfall"]
        
        hw_probs = hw_out.pop("_probabilities")
        hw_feats = hw_out.pop("_features")
        er_probs = er_out.pop("_probabilities")
        er_feats = er_out.pop("_features")

        # 2. Overall Risk Aggregation
        overall_risk = self.calculate_overall_risk(hw_out, er_out, hw_probs, er_probs)

        # 3. Scenario Analysis
        scenario_res = self.simulate_scenario(request)

        # 4. Driver Analysis
        drivers = {
            "top_drivers": self.analyze_drivers(hw_feats, er_feats)
        }

        # 5. Impact Advisories
        temp_anom = hw_feats.get("hw_temperature_anomaly", 0.0)
        runoff_press = er_feats.get("er_runoff_pressure", 0.0)
        soil_sat = er_feats.get("er_soil_saturation", 0.0)
        rain_anom = er_feats.get("er_rainfall_anomaly", 0.0)
        
        hw_impact = self.get_heatwave_impact(hw_out["severity"], temp_anom, hw_probs)
        er_impact = self.get_extreme_rainfall_impact(er_out["severity"], runoff_press, soil_sat, rain_anom)
        
        impact = {
            "heatwave_impact": hw_impact,
            "rainfall_impact": er_impact
        }

        # 6. Early Warning Alert
        warnings_alert = self.generate_early_warning(hw_probs, er_probs)

        return {
            "heatwave_prediction": hw_out,
            "rainfall_extreme_prediction": er_out,
            "overall_extreme_weather": overall_risk,
            "scenario_analysis": scenario_res,
            "driver_analysis": drivers,
            "impact_assessment": impact,
            "early_warning": warnings_alert,
            "source": request.get("source"),
            "confidence_source": request.get("confidence_source"),
            "last_updated": request.get("last_updated")
        }
