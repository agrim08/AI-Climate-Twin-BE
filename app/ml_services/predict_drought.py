import os
import json
import logging
import joblib
import pandas as pd
import numpy as np
from typing import Dict, Any, List

# Setup Structured Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
CLASS_ORDER = ["Low", "Medium", "High", "Extreme"]
LABEL_DECODER = {i: c for i, c in enumerate(CLASS_ORDER)}

# Fallback feature importances matching LightGBM trained model features
FEATURE_IMPORTANCES = {
    'sm_zscore': 12856, 'rainfall_spi': 11724, 'temperature_zscore': 10448, 'evaporation_pressure': 6020, 
    'evaporation_stress': 5982, 'temperature_anomaly': 5516, 'rainfall_deficit_pct': 5369, 
    'temperature_stress': 3654, 'rainfall_deficit': 3573, 'temperature_prev_3': 3546, 'longitude': 3305, 
    'rolling_sm_6m': 3081, 'sm_anomaly': 2818, 'sm_trend': 2580, 'sm_deficit_pct': 2455, 'rainfall_evap_ratio': 2237, 
    'compound_drought_stress': 2155, 'zone_rain_zscore': 2145, 'latitude': 2100, 'rolling_temp_6m': 2078, 
    'drought_acceleration': 2078, 'rainfall_prev_3': 1983, 'zone_aridity_index': 1969, 'evabs': 1938, 
    'water_balance': 1926, 'temperature_c': 1910, 'cumulative_sm_deficit_6m': 1869, 'rainfall_mm': 1820, 
    'cumulative_deficit_6m': 1762, 'zone_sm_zscore': 1759, 'drought_momentum': 1713, 'drought_trend': 1687, 
    'drought_recovery': 1581, 'deficit_volatility_3m': 1535, 'rolling_rainfall_6m': 1463, 'soil_moisture': 1390, 
    'zone_rain_deficit': 1365, 'moisture_stress': 1360, 'cumulative_sm_deficit_3m': 1342, 'rainfall_prev_1': 1328, 
    'dry_month_streak': 1321, 'rainfall_deficit_lag1': 1314, 'rolling_sm_3m': 1234, 'rolling_rainfall_3m': 1195, 
    'sro': 1195, 'cumulative_deficit_3m': 1147, 'sm_zone_anomaly': 1146, 'rainfall_runoff_ratio': 1146, 'year': 1141, 
    'temperature_prev_1': 1118, 'rolling_temp_3m': 1038, 'soil_moisture_prev_1': 1023, 'water_availability_index': 976, 
    'runoff_efficiency': 940, 'zone_sm_deficit': 927, 'rainfall_climatology': 917, 'hydrological_stress': 843, 
    'sm_deficit': 828, 'month_cos': 633, 'month': 592, 'low_sm_streak': 560, 'month_sin': 444, 'deficit_streak': 319, 
    'heat_excess': 3
}

# Explicit order of features as seen by the model during training
# We enforce this order during prediction to prevent mismatch errors.
MODEL_FEATURES = [
    'sm_zscore', 'rainfall_spi', 'temperature_zscore', 'evaporation_pressure', 
    'evaporation_stress', 'temperature_anomaly', 'rainfall_deficit_pct', 
    'temperature_stress', 'rainfall_deficit', 'temperature_prev_3', 'longitude', 
    'rolling_sm_6m', 'sm_anomaly', 'sm_trend', 'sm_deficit_pct', 'rainfall_evap_ratio', 
    'compound_drought_stress', 'zone_rain_zscore', 'latitude', 'rolling_temp_6m', 
    'drought_acceleration', 'rainfall_prev_3', 'zone_aridity_index', 'evabs', 
    'water_balance', 'temperature_c', 'cumulative_sm_deficit_6m', 'rainfall_mm', 
    'cumulative_deficit_6m', 'zone_sm_zscore', 'drought_momentum', 'drought_trend', 
    'drought_recovery', 'deficit_volatility_3m', 'rolling_rainfall_6m', 'soil_moisture', 
    'zone_rain_deficit', 'moisture_stress', 'cumulative_sm_deficit_3m', 'rainfall_prev_1', 
    'dry_month_streak', 'rainfall_deficit_lag1', 'rolling_sm_3m', 'rolling_rainfall_3m', 
    'sro', 'cumulative_deficit_3m', 'sm_zone_anomaly', 'rainfall_runoff_ratio', 'year', 
    'temperature_prev_1', 'rolling_temp_3m', 'soil_moisture_prev_1', 'water_availability_index', 
    'runoff_efficiency', 'zone_sm_deficit', 'rainfall_climatology', 'hydrological_stress', 
    'sm_deficit', 'month_cos', 'month', 'low_sm_streak', 'month_sin', 'deficit_streak', 
    'heat_excess'
]


class DroughtPredictor:
    """
    Production-ready Drought Intelligence Layer service.
    Designed for backend and simulation engine integration.
    """
    
    def __init__(self, model_dir: str = None):
        if model_dir is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            model_dir = os.path.join(script_dir, "models")
            
        self.model_path = os.path.join(model_dir, "drought.pkl")
        self.metrics_path = os.path.join(model_dir, "drought_metrics.json")
        self.feature_importance_path = os.path.join(model_dir, "drought_feature_importance.csv")
        
        self.model = None
        self.metrics = None
        self.feature_importances = None
        
        # Load core model assets
        self.load_model()
        self.load_feature_importances()
        
        # Lazy load Temperature and Rainfall predictors for chained Digital Twin workflows
        self.temp_predictor = None
        self.rain_predictor = None
        try:
            from app.ml_services.predict_temperature import TemperaturePredictor
            from app.ml_services.predict_rainfall import RainfallPredictor
            self.temp_predictor = TemperaturePredictor(model_dir)
            self.rain_predictor = RainfallPredictor(model_dir)
            logger.info("Digital Twin Model Chaining activated: Temperature & Rainfall predictors loaded.")
        except Exception as e:
            logger.warning(
                f"Failed to load Temperature/Rainfall predictors for chaining: {str(e)}. "
                "Scenario simulator will fallback to direct delta modifications."
            )
        
    def load_model(self):
        """Loads the serialized LightGBM model and its residual metrics."""
        try:
            logger.info(f"Loading drought model from {self.model_path}")
            self.model = joblib.load(self.model_path)
            
            if os.path.exists(self.metrics_path):
                with open(self.metrics_path, 'r') as f:
                    self.metrics = json.load(f)
                logger.info(f"Model loaded successfully. Base F1: {self.metrics.get('macro_f1', 0):.4f}")
            else:
                self.metrics = {"macro_f1": 0.85}
                
        except Exception as e:
            logger.error(f"Failed to load drought model: {str(e)}")
            raise RuntimeError(f"Model initialization failed: {str(e)}")

    def load_feature_importances(self):
        """Loads feature importances for local driver analysis."""
        try:
            if os.path.exists(self.feature_importance_path):
                df = pd.read_csv(self.feature_importance_path)
                self.feature_importances = dict(zip(df['Feature'], df['Importance']))
                logger.info("Dynamic feature importances loaded from CSV.")
            else:
                self.feature_importances = FEATURE_IMPORTANCES
                logger.warning("Feature importance CSV not found. Using precompiled fallback importances.")
        except Exception as e:
            logger.error(f"Failed to load feature importances: {str(e)}")
            self.feature_importances = FEATURE_IMPORTANCES

    def prepare_features(self, request: Dict[str, Any], apply_deltas: bool = True) -> Dict[str, float]:
        """
        Dynamically reconstructs all 64 complex drought features from basic API inputs
        so that scenario simulation delta modifiers properly cascade through the math.
        """
        # Copy request dictionary to avoid mutating input request parameters
        req = request.copy()
        
        # --- Modifiers ---
        t_delta = float(req.get("temperature_delta", 0.0)) if apply_deltas else 0.0
        r_delta = float(req.get("rainfall_delta", 0.0)) if apply_deltas else 0.0
        sm_delta = float(req.get("soil_moisture_delta", 0.0)) if apply_deltas else 0.0
        evap_delta = float(req.get("evaporation_delta", 0.0)) if apply_deltas else 0.0
        ro_delta = float(req.get("runoff_delta", 0.0)) if apply_deltas else 0.0

        # --- Base Variables ---
        f = {}
        
        # Geography & Time
        f['latitude'] = float(req.get("latitude", 20.0))
        f['longitude'] = float(req.get("longitude", 80.0))
        f['year'] = int(req.get("year", 2024))
        f['month'] = int(req.get("month", 6))
        f['month_sin'] = np.sin(2 * np.pi * f['month'] / 12.0)
        f['month_cos'] = np.cos(2 * np.pi * f['month'] / 12.0)
        
        # Climate State (With Simulation Modifiers Applied where applicable)
        # For temperature, we apply absolute shift.
        # For rainfall, soil moisture, evaporation and runoff, we apply percentage modifications to prevent physics violations.
        f['temperature_c'] = float(req.get("temperature_c", 30.0)) + t_delta
        f['rainfall_mm'] = max(0.0, float(req.get("rainfall_mm", 10.0)) * (1.0 + r_delta / 100.0))
        f['soil_moisture'] = max(0.0, float(req.get("soil_moisture", 0.2)) * (1.0 + sm_delta / 100.0))
        
        # Evaporation flux is negative, so scaling maintains sign correctness
        f['evabs'] = float(req.get("evabs", -0.001)) * (1.0 + evap_delta / 100.0)
        f['sro'] = max(0.0, float(req.get("sro", 0.001)) * (1.0 + ro_delta / 100.0))
        
        # Historical / Rolling
        f['temperature_prev_1'] = float(req.get("temperature_prev_1", 29.0))
        f['temperature_prev_3'] = float(req.get("temperature_prev_3", 28.0))
        f['rainfall_prev_1'] = float(req.get("rainfall_prev_1", 5.0))
        f['rainfall_prev_3'] = float(req.get("rainfall_prev_3", 2.0))
        f['soil_moisture_prev_1'] = float(req.get("soil_moisture_prev_1", 0.18))
        
        f['rolling_temp_3m'] = float(req.get("rolling_temp_3m", 28.5))
        f['rolling_temp_6m'] = float(req.get("rolling_temp_6m", 25.0))
        f['rolling_rainfall_3m'] = float(req.get("rolling_rainfall_3m", 15.0))
        f['rolling_rainfall_6m'] = float(req.get("rolling_rainfall_6m", 30.0))
        
        f['rolling_sm_3m'] = float(req.get("rolling_sm_3m", 0.22))
        f['rolling_sm_6m'] = float(req.get("rolling_sm_6m", 0.25))
        
        # Streaks & Persistence
        f['dry_month_streak'] = float(req.get("dry_month_streak", 0.0))
        f['deficit_streak'] = float(req.get("deficit_streak", 0.0))
        f['low_sm_streak'] = float(req.get("low_sm_streak", 0.0))
        
        # Cumulative Deficits
        f['cumulative_deficit_3m'] = float(req.get("cumulative_deficit_3m", -10.0))
        f['cumulative_deficit_6m'] = float(req.get("cumulative_deficit_6m", -25.0))
        f['cumulative_sm_deficit_3m'] = float(req.get("cumulative_sm_deficit_3m", 0.05))
        f['cumulative_sm_deficit_6m'] = float(req.get("cumulative_sm_deficit_6m", 0.10))
        
        # Climatology Baselines (Required for Z-scores and anomalies)
        rain_climo = float(req.get("rainfall_climatology", 12.0))
        rain_climo_std = float(req.get("rainfall_climatology_std", 5.0))
        
        sm_climo = float(req.get("sm_climatology", 0.25))
        sm_climo_std = float(req.get("sm_climatology_std", 0.05))
        
        temp_climo = float(req.get("temperature_climatology", 28.0))
        temp_climo_std = float(req.get("temperature_climatology_std", 2.0))
        
        lag1_climo = float(req.get("lag1_climatology", 10.0))
        
        # Zone Baselines
        z_rain_climo = float(req.get("zone_rain_climatology", 10.0))
        z_rain_std = float(req.get("zone_rain_climatology_std", 4.0))
        z_sm_climo = float(req.get("zone_sm_climatology", 0.20))
        z_sm_std = float(req.get("zone_sm_climatology_std", 0.04))
        z_arid_idx = float(req.get("zone_aridity_index", 1.5))
        
        # --- Derived Water Balance Features ---
        evap_mag = abs(f['evabs'])
        f['water_balance'] = f['rainfall_mm'] - (evap_mag * 30 * 1000) - (f['sro'] * 1000)
        f['rainfall_evap_ratio'] = max(0.0, min(20.0, f['rainfall_mm'] / (evap_mag * 30 * 1000 + 1e-6)))
        f['rainfall_runoff_ratio'] = max(0.0, min(500.0, f['rainfall_mm'] / (f['sro'] * 1000 + 1e-6)))
        f['evaporation_pressure'] = max(0.0, min(100.0, (evap_mag * 30 * 1000) / (f['rainfall_mm'] + 1.0)))
        f['runoff_efficiency'] = max(0.0, min(1.0, (f['sro'] * 1000) / (f['rainfall_mm'] + 1e-6)))
        
        # --- Derived Rainfall Deficits ---
        f['rainfall_climatology'] = rain_climo
        f['rainfall_deficit'] = f['rainfall_mm'] - rain_climo
        f['rainfall_deficit_pct'] = max(-200.0, min(200.0, f['rainfall_deficit'] / (rain_climo + 1e-6) * 100))
        f['rainfall_spi'] = max(-4.0, min(4.0, f['rainfall_deficit'] / (rain_climo_std + 1e-6)))
        f['rainfall_deficit_lag1'] = f['rainfall_prev_1'] - lag1_climo
        
        # --- Derived Soil Moisture ---
        f['sm_anomaly'] = f['soil_moisture'] - sm_climo
        f['sm_zscore'] = max(-4.0, min(4.0, f['sm_anomaly'] / (sm_climo_std + 1e-6)))
        f['sm_deficit'] = max(0.0, sm_climo - f['soil_moisture'])
        f['sm_deficit_pct'] = f['sm_deficit'] / (sm_climo + 1e-6) * 100
        f['sm_trend'] = f['rolling_sm_3m'] - f['rolling_sm_6m']
        
        # --- Derived Temperature Stress ---
        f['temperature_anomaly'] = f['temperature_c'] - temp_climo
        f['temperature_zscore'] = max(-4.0, min(4.0, f['temperature_anomaly'] / (temp_climo_std + 1e-6)))
        rain_norm = max(0.0, min(2.0, f['rainfall_mm'] / (rain_climo + 1e-6)))
        f['temperature_stress'] = f['temperature_anomaly'] * (1.0 - rain_norm)
        f['heat_excess'] = max(0.0, f['temperature_c'] - 35.0)
        
        # --- Derived Zone Features ---
        f['zone_rain_deficit'] = f['rainfall_mm'] - z_rain_climo
        f['zone_rain_zscore'] = max(-4.0, min(4.0, f['zone_rain_deficit'] / (z_rain_std + 1e-6)))
        f['zone_sm_deficit'] = z_sm_climo - f['soil_moisture']
        f['zone_sm_zscore'] = max(-4.0, min(4.0, (f['soil_moisture'] - z_sm_climo) / (z_sm_std + 1e-6)))
        f['sm_zone_anomaly'] = f['soil_moisture'] - z_sm_climo
        f['zone_aridity_index'] = z_arid_idx
        
        # --- Drought Evolution ---
        f['drought_recovery'] = f['rainfall_deficit'] - f['rainfall_deficit_lag1']
        
        short_trend = f['cumulative_deficit_3m'] / 3.0
        long_trend = f['cumulative_deficit_6m'] / 6.0
        f['drought_momentum'] = short_trend - long_trend
        
        f['drought_acceleration'] = float(req.get("drought_acceleration", 0.0))
        f['drought_trend'] = f['rainfall_deficit'] - f['rainfall_deficit_lag1']
        f['deficit_volatility_3m'] = float(req.get("deficit_volatility_3m", 5.0))
        
        # --- Water Stress Indicators ---
        sm_norm = max(0.0, min(1.0, f['soil_moisture'] / 0.5))
        rain_norm2 = max(0.0, min(1.0, f['rainfall_mm'] / 500.0))
        sro_norm = max(0.0, min(1.0, f['sro'] / 0.1))
        
        f['water_availability_index'] = (0.40 * sm_norm + 0.40 * rain_norm2 + 0.20 * sro_norm)
        f['hydrological_stress'] = 1.0 - f['water_availability_index']
        f['moisture_stress'] = f['sm_deficit'] * (1.0 + max(0.0, f['temperature_anomaly']) / 10.0)
        f['evaporation_stress'] = max(0.0, min(20.0, (evap_mag * 30 * 1000) / (f['rainfall_mm'] + f['soil_moisture'] * 100.0 + 1.0)))
        f['compound_drought_stress'] = abs(min(0.0, f['rainfall_deficit'])) * f['sm_deficit']
        
        # Construct final dict enforcing exact column order
        return {feat: f.get(feat, 0.0) for feat in MODEL_FEATURES}

    def predict(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predicts drought category and probabilities.
        """
        try:
            # 1. Engineer all 64 features dynamically
            features_dict = self.prepare_features(request, apply_deltas=True)
            df_input = pd.DataFrame([features_dict])[MODEL_FEATURES]
            
            # 2. Predict Class
            pred_idx = int(self.model.predict(df_input)[0])
            pred_label = LABEL_DECODER[pred_idx]
            
            # 3. Predict Probabilities (For Continuous Risk Score)
            probs = self.model.predict_proba(df_input)[0]
            
            # Risk Score = Probability of High (2) + Probability of Extreme (3)
            risk_score = float(probs[2] + probs[3])
            
            # 4. Confidence Estimation
            # confidence_score = max(class_probabilities)
            # confidence_level: >=0.85 High, >=0.65 Medium, Low otherwise
            confidence_score = float(max(probs))
            if confidence_score >= 0.85:
                confidence_level = "High"
            elif confidence_score >= 0.65:
                confidence_level = "Medium"
            else:
                confidence_level = "Low"
            
            return {
                "drought_category": pred_label,
                "severity_score": round(risk_score, 3),
                "drought_risk_score": round(risk_score, 3), # Kept for backward compatibility
                "confidence_score": round(confidence_score, 3),
                "confidence_level": confidence_level,
                "probabilities": {
                    "Low": round(float(probs[0]), 3),
                    "Medium": round(float(probs[1]), 3),
                    "High": round(float(probs[2]), 3),
                    "Extreme": round(float(probs[3]), 3)
                },
                "source": request.get("source"),
                "confidence_source": request.get("confidence_source"),
                "last_updated": request.get("last_updated")
            }
            
        except Exception as e:
            logger.error(f"Prediction failed: {str(e)}", exc_info=True)
            raise
 
    def batch_predict(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Optimized prediction method for multiple locations/timeframes at once.
        """
        if not requests:
            return []
            
        logger.info(f"Processing batch drought prediction for {len(requests)} items.")
        
        try:
            features_list = [self.prepare_features(req, apply_deltas=True) for req in requests]
            df_input = pd.DataFrame(features_list)[MODEL_FEATURES]
            
            # Batch Predict
            predictions = self.model.predict(df_input)
            probabilities = self.model.predict_proba(df_input)
            
            # Format outputs
            results = []
            for idx, pred_idx in enumerate(predictions):
                req = requests[idx]
                feat = features_list[idx]
                probs = probabilities[idx]
                
                pred_label = LABEL_DECODER[int(pred_idx)]
                risk_score = float(probs[2] + probs[3])
                
                confidence_score = float(max(probs))
                if confidence_score >= 0.85:
                    confidence_level = "High"
                elif confidence_score >= 0.65:
                    confidence_level = "Medium"
                else:
                    confidence_level = "Low"
                
                results.append({
                    "drought_category": pred_label,
                    "severity_score": round(risk_score, 3),
                    "drought_risk_score": round(risk_score, 3),
                    "confidence_score": round(confidence_score, 3),
                    "confidence_level": confidence_level,
                    "probabilities": {
                        "Low": round(float(probs[0]), 3),
                        "Medium": round(float(probs[1]), 3),
                        "High": round(float(probs[2]), 3),
                        "Extreme": round(float(probs[3]), 3)
                    },
                    "source": req.get("source"),
                    "confidence_source": req.get("confidence_source"),
                    "last_updated": req.get("last_updated")
                })
                
            return results
            
        except Exception as e:
            logger.error(f"Batch prediction failed: {str(e)}", exc_info=True)
            raise

    def analyze_drivers(self, features_dict: Dict[str, float]) -> List[str]:
        """
        Identifies the strongest active drought drivers for the current prediction.
        Combines normalized local anomalies with global feature importance weights.
        """
        importances = self.feature_importances or FEATURE_IMPORTANCES
        
        # 1. Rainfall Deficit Driver Score
        rf_spi = features_dict.get('rainfall_spi', 0.0)
        rf_def = features_dict.get('rainfall_deficit', 0.0)
        rf_def_pct = features_dict.get('rainfall_deficit_pct', 0.0)
        
        rf_score = (
            max(0.0, -rf_spi) * importances.get('rainfall_spi', 11724) +
            (max(0.0, -rf_def) / 10.0) * importances.get('rainfall_deficit', 3573) +
            (max(0.0, -rf_def_pct) / 100.0) * importances.get('rainfall_deficit_pct', 5369)
        )
        
        # 2. Low Soil Moisture Driver Score
        sm_zs = features_dict.get('sm_zscore', 0.0)
        sm_anom = features_dict.get('sm_anomaly', 0.0)
        sm_def = features_dict.get('sm_deficit', 0.0)
        m_stress = features_dict.get('moisture_stress', 0.0)
        
        sm_score = (
            max(0.0, -sm_zs) * importances.get('sm_zscore', 12856) +
            max(0.0, -sm_anom) * 10.0 * importances.get('sm_anomaly', 2818) +
            max(0.0, sm_def) * 10.0 * importances.get('sm_deficit', 828) +
            max(0.0, m_stress) * 5.0 * importances.get('moisture_stress', 1360)
        )
        
        # 3. High Temperature Anomaly Driver Score
        t_zs = features_dict.get('temperature_zscore', 0.0)
        t_anom = features_dict.get('temperature_anomaly', 0.0)
        t_stress = features_dict.get('temperature_stress', 0.0)
        h_ex = features_dict.get('heat_excess', 0.0)
        
        temp_score = (
            max(0.0, t_zs) * importances.get('temperature_zscore', 10448) +
            max(0.0, t_anom) * 2.0 * importances.get('temperature_anomaly', 5516) +
            max(0.0, t_stress) * 2.0 * importances.get('temperature_stress', 3654) +
            max(0.0, h_ex) * 5.0 * importances.get('heat_excess', 3)
        )
        
        # 4. High Evaporation Pressure Driver Score
        evap_press = features_dict.get('evaporation_pressure', 0.0)
        evap_stress = features_dict.get('evaporation_stress', 0.0)
        
        evap_score = (
            (evap_press / 100.0) * importances.get('evaporation_pressure', 6020) +
            (evap_stress / 20.0) * importances.get('evaporation_stress', 5982)
        )
        
        # 5. Hydrological Stress Driver Score
        hydro_stress = features_dict.get('hydrological_stress', 0.0)
        w_bal = features_dict.get('water_balance', 0.0)
        
        hydro_score = (
            hydro_stress * importances.get('hydrological_stress', 843) +
            (max(0.0, -w_bal) / 100.0) * importances.get('water_balance', 1926)
        )
        
        drivers = [
            ("Rainfall Deficit", rf_score),
            ("Low Soil Moisture", sm_score),
            ("High Temperature Anomaly", temp_score),
            ("High Evaporation Pressure", evap_score),
            ("Hydrological Stress", hydro_score)
        ]
        
        # Sort by contribution descending
        drivers.sort(key=lambda x: x[1], reverse=True)
        
        # Return top drivers that have a positive score
        top_drivers = [d[0] for d in drivers[:3] if d[1] > 0.0]
        return top_drivers if top_drivers else ["Rainfall Deficit"]

    def get_water_intelligence(self, features_dict: Dict[str, float], risk_score: float) -> Dict[str, Any]:
        """
        Assesses water stress index, reservoir risk, groundwater risk, and water availability status.
        """
        # Inputs
        soil_moisture = features_dict.get('soil_moisture', 0.2)
        rainfall_mm = features_dict.get('rainfall_mm', 10.0)
        sro = features_dict.get('sro', 0.001)
        rain_climo = features_dict.get('rainfall_climatology', 12.0)
        
        # Normalization (relative to standard limits)
        sm_norm = max(0.0, min(1.0, soil_moisture / 0.4))
        rain_norm = max(0.0, min(1.5, rainfall_mm / (rain_climo + 1e-6)))
        sro_norm = max(0.0, min(1.0, sro / 0.05))
        
        # Water Stress Index: 0 to 100
        wsi = 100.0 * (
            0.30 * (1.0 - sm_norm) +
            0.30 * (1.0 - min(1.0, rain_norm)) +
            0.10 * (1.0 - sro_norm) +
            0.30 * risk_score
        )
        wsi = round(max(0.0, min(100.0, wsi)), 1)
        
        # Reservoir Risk: derived from short term runoff efficiency and rainfall deficit
        if rainfall_mm < 10.0 and sro < 0.002 and risk_score > 0.6:
            res_risk = "Critical"
        elif rainfall_mm < 25.0 or sro < 0.005 or risk_score > 0.4:
            res_risk = "High"
        elif risk_score > 0.15:
            res_risk = "Medium"
        else:
            res_risk = "Low"
            
        # Groundwater Risk: based on long term drought metrics
        low_sm_streak = features_dict.get('low_sm_streak', 0.0)
        cum_sm_def_6m = features_dict.get('cumulative_sm_deficit_6m', 0.1)
        sm_zs = features_dict.get('sm_zscore', 0.0)
        
        if low_sm_streak >= 4 or cum_sm_def_6m > 0.4 or sm_zs < -2.0:
            gw_risk = "Critical"
        elif low_sm_streak >= 2 or cum_sm_def_6m > 0.2 or sm_zs < -1.2:
            gw_risk = "High"
        elif sm_zs < -0.5 or cum_sm_def_6m > 0.05:
            gw_risk = "Medium"
        else:
            gw_risk = "Low"
            
        # Status Mapping
        if wsi > 75.0:
            status = "Deficit"
        elif wsi > 50.0:
            status = "Stressed"
        elif wsi > 20.0:
            status = "Sufficient"
        else:
            status = "Abundant"
            
        return {
            "water_stress_index": wsi,
            "reservoir_risk": res_risk,
            "groundwater_risk": gw_risk,
            "water_availability_status": status
        }

    def get_agriculture_intelligence(self, features_dict: Dict[str, float], risk_score: float) -> Dict[str, Any]:
        """
        Assesses crop stress index, irrigation need, and agricultural risk.
        """
        # Inputs
        soil_moisture = features_dict.get('soil_moisture', 0.2)
        temp_c = features_dict.get('temperature_c', 30.0)
        
        # Soil moisture stress scaling (optimal is >0.3, extremely stressed is <0.1)
        sm_factor = max(0.0, min(1.0, (0.3 - soil_moisture) / 0.2))
        
        # Heat stress scaling (optimal is <28C, stressed is >40C)
        temp_factor = max(0.0, min(1.0, (temp_c - 28.0) / 12.0))
        
        # Crop Stress Index: 0 to 100
        csi = 100.0 * (
            0.45 * sm_factor +
            0.25 * temp_factor +
            0.30 * risk_score
        )
        csi = round(max(0.0, min(100.0, csi)), 1)
        
        # Irrigation Need
        if soil_moisture < 0.10 and temp_c > 35.0:
            ir_need = "Critical"
        elif soil_moisture < 0.15 or csi > 65.0:
            ir_need = "High"
        elif soil_moisture < 0.22 or csi > 35.0:
            ir_need = "Medium"
        else:
            ir_need = "Low"
            
        # Agricultural Risk
        df_input = pd.DataFrame([features_dict])[MODEL_FEATURES]
        pred_idx = int(self.model.predict(df_input)[0])
        drought_cat = LABEL_DECODER[pred_idx]
        
        if csi > 75.0 or drought_cat == "Extreme":
            ag_risk = "Critical"
        elif csi > 50.0 or drought_cat == "High":
            ag_risk = "High"
        elif csi > 25.0 or drought_cat == "Medium":
            ag_risk = "Medium"
        else:
            ag_risk = "Low"
            
        return {
            "crop_stress_index": csi,
            "irrigation_need": ir_need,
            "agricultural_risk": ag_risk
        }

    def generate_early_warning(self, probs: List[float], features_dict: Dict[str, float]) -> Dict[str, Any]:
        """
        Evaluates early warning alerts based on probability thresholds and escalation momentum.
        """
        p_med = probs[1]
        p_high = probs[2]
        p_ext = probs[3]
        
        d_momentum = features_dict.get('drought_momentum', 0.0)
        d_trend = features_dict.get('drought_trend', 0.0)
        
        # Warning Level Determination
        if p_ext > 0.30 or (p_high + p_ext) > 0.70:
            warning_level = "Critical"
        elif p_ext > 0.15 or p_high > 0.40:
            warning_level = "High"
        elif p_med > 0.50 or p_high > 0.25:
            warning_level = "Medium"
        else:
            warning_level = "Low"
            
        warning_active = warning_level in ["Medium", "High", "Critical"]
        
        # Generate Actionable Alert Messages
        messages = []
        if p_ext > 0.15:
            messages.append(f"Elevated Extreme Drought probability: {p_ext*100:.1f}%.")
        elif p_high > 0.35:
            messages.append(f"Elevated High Drought probability: {p_high*100:.1f}%.")
            
        if d_momentum < -5.0 or d_trend < -5.0:
            messages.append("Drought severity is rapidly increasing due to accumulating water deficits.")
            
        if not messages:
            if warning_active:
                messages.append("Drought risk is building. Monitoring is advised.")
            else:
                messages.append("No active drought hazards detected.")
                
        message_str = " ".join(messages)
        
        return {
            "warning": warning_active,
            "warning_level": warning_level,
            "message": message_str
        }

    def simulate_scenario(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs baseline prediction vs scenario prediction.
        Attempts preferred chained Digital Twin pipeline first, otherwise falls back to direct delta modifications.
        """
        # --- 1. Compute Baseline Prediction ---
        # Copy request to avoid mutation
        baseline_req = request.copy()
        for key in ["temperature_delta", "rainfall_delta", "soil_moisture_delta", "evaporation_delta", "runoff_delta"]:
            baseline_req[key] = 0.0
            
        baseline_features = self.prepare_features(baseline_req, apply_deltas=False)
        baseline_df = pd.DataFrame([baseline_features])[MODEL_FEATURES]
        baseline_pred_idx = int(self.model.predict(baseline_df)[0])
        baseline_probs = self.model.predict_proba(baseline_df)[0]
        
        baseline_category = LABEL_DECODER[baseline_pred_idx]
        baseline_score = float(baseline_probs[2] + baseline_probs[3])
        
        # --- 2. Compute Scenario Prediction ---
        scenario_req = request.copy()
        chained_run = False
        
        # Preferred chained Digital Twin workflow
        if self.temp_predictor is not None and self.rain_predictor is not None:
            try:
                # Chain step A: Predict future temperature with delta
                temp_res = self.temp_predictor.predict(scenario_req)
                t_delta = float(scenario_req.get("temperature_delta", 0.0))
                scenario_req["temperature_c"] = temp_res["predicted_temperature_c"] + t_delta
                
                # Chain step B: Predict future rainfall using updated temperature and delta
                rain_res = self.rain_predictor.predict(scenario_req)
                r_delta = float(scenario_req.get("rainfall_delta", 0.0))
                scenario_req["rainfall_mm"] = max(0.0, rain_res["predicted_rainfall_mm"] * (1.0 + r_delta / 100.0))
                
                # Chain step C: Scale other state variables by their percentage deltas
                sm_delta = float(scenario_req.get("soil_moisture_delta", 0.0))
                evap_delta = float(scenario_req.get("evaporation_delta", 0.0))
                ro_delta = float(scenario_req.get("runoff_delta", 0.0))
                
                scenario_req["soil_moisture"] = max(0.0, float(scenario_req.get("soil_moisture", 0.2)) * (1.0 + sm_delta / 100.0))
                scenario_req["evabs"] = float(scenario_req.get("evabs", -0.001)) * (1.0 + evap_delta / 100.0)
                scenario_req["sro"] = max(0.0, float(scenario_req.get("sro", 0.001)) * (1.0 + ro_delta / 100.0))
                
                # Since state is updated, prepare features without applying deltas again
                scenario_features = self.prepare_features(scenario_req, apply_deltas=False)
                chained_run = True
                logger.info("Chained scenario simulation completed successfully.")
            except Exception as e:
                logger.warning(f"Chained scenario pipeline execution failed: {str(e)}. Falling back to direct modification.")
                
        if not chained_run:
            # Fallback workflow: Direct Delta modification
            scenario_features = self.prepare_features(scenario_req, apply_deltas=True)
            
        scenario_df = pd.DataFrame([scenario_features])[MODEL_FEATURES]
        scenario_pred_idx = int(self.model.predict(scenario_df)[0])
        scenario_probs = self.model.predict_proba(scenario_df)[0]
        
        scenario_category = LABEL_DECODER[scenario_pred_idx]
        scenario_score = float(scenario_probs[2] + scenario_probs[3])
        
        # Calculate Risk level change
        level_map = {"Low": 0, "Medium": 1, "High": 2, "Extreme": 3}
        baseline_level = level_map.get(baseline_category, 0)
        scenario_level = level_map.get(scenario_category, 0)
        diff = scenario_level - baseline_level
        
        if diff > 0:
            risk_change = f"+{diff} level{'s' if diff > 1 else ''}"
        elif diff < 0:
            risk_change = f"{diff} level{'s' if abs(diff) > 1 else ''}"
        else:
            risk_change = "No change"
            
        return {
            "baseline_category": baseline_category,
            "baseline_score": round(baseline_score, 3),
            "scenario_category": scenario_category,
            "scenario_score": round(scenario_score, 3),
            "risk_change": risk_change
        }

    def get_digital_twin_state(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Unified API caller returning all Drought Intelligence Layer outputs in a single payload.
        """
        # 1. Run main prediction on current settings (with deltas applied)
        features_dict = self.prepare_features(request, apply_deltas=True)
        df_input = pd.DataFrame([features_dict])[MODEL_FEATURES]
        
        pred_idx = int(self.model.predict(df_input)[0])
        pred_label = LABEL_DECODER[pred_idx]
        probs = self.model.predict_proba(df_input)[0]
        risk_score = float(probs[2] + probs[3])
        
        # Calculate confidence indicators
        confidence_score = float(max(probs))
        if confidence_score >= 0.85:
            confidence_level = "High"
        elif confidence_score >= 0.65:
            confidence_level = "Medium"
        else:
            confidence_level = "Low"
            
        prediction_response = {
            "drought_category": pred_label,
            "severity_score": round(risk_score, 3),
            "drought_risk_score": round(risk_score, 3),
            "confidence_score": round(confidence_score, 3),
            "confidence_level": confidence_level,
            "probabilities": {
                "Low": round(float(probs[0]), 3),
                "Medium": round(float(probs[1]), 3),
                "High": round(float(probs[2]), 3),
                "Extreme": round(float(probs[3]), 3)
            }
        }
        
        # 2. Run Scenario Simulation
        scenario_response = self.simulate_scenario(request)
        
        # 3. Driver Analysis
        drivers_response = {
            "top_drivers": self.analyze_drivers(features_dict)
        }
        
        # 4. Hydrological Water Intelligence
        water_response = self.get_water_intelligence(features_dict, risk_score)
        
        # 5. Agricultural Intelligence
        agriculture_response = self.get_agriculture_intelligence(features_dict, risk_score)
        
        # 6. Early Warning Systems
        warning_response = self.generate_early_warning(probs, features_dict)
        
        return {
            "drought_prediction": prediction_response,
            "scenario_analysis": scenario_response,
            "drivers": drivers_response,
            "water_intelligence": water_response,
            "agriculture_intelligence": agriculture_response,
            "early_warning": warning_response,
            "source": request.get("source"),
            "confidence_source": request.get("confidence_source"),
            "last_updated": request.get("last_updated")
        }


# Example Usage Block (can be executed directly for verification)
if __name__ == "__main__":
    predictor = DroughtPredictor()
    
    sample_request = {
        "year": 2030,
        "month": 5, 
        "latitude": 28.61,
        "longitude": 77.20,
        
        # High heat, low rain, depleted soil moisture
        "temperature_c": 42.5,
        "rainfall_mm": 2.0,
        "soil_moisture": 0.08,
        "evabs": -0.005,
        "sro": 0.000,
        
        # Historical context
        "temperature_climatology": 38.0,
        "temperature_climatology_std": 2.0,
        "rainfall_climatology": 20.0,
        "rainfall_climatology_std": 10.0,
        "sm_climatology": 0.15,
        "sm_climatology_std": 0.03,
        
        "zone_rain_climatology": 15.0,
        "zone_sm_climatology": 0.12,
        
        "dry_month_streak": 4.0,
        "low_sm_streak": 3.0,
        
        # Scenario modifiers
        "temperature_delta": +2.0,
        "rainfall_delta": -20.0,
        "soil_moisture_delta": -15.0
    }
    
    print("\n--- Unified Digital Twin State ---")
    res = predictor.get_digital_twin_state(sample_request)
    print(json.dumps(res, indent=2))
