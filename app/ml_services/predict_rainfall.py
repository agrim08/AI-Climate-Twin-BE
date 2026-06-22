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
CLIMATE_ZONES = [
    'Central_Plateau_Region', 'Eastern_Coastal_Region', 'Himalayan_Region',
    'Indo-Gangetic_Plains', 'North-East_Region', 'Southern_Peninsular_Region',
    'Thar_Desert_Region', 'Western_Coastal_Region', 'Western_Ghats_Region'
]

# Note: The order must strictly match the training data feature columns.
# We explicitly order them during preparation to match exactly.
MODEL_FEATURES = [
    'latitude', 'longitude', 'year', 'month', 'temperature_c', 'soil_moisture', 'evabs', 'sro',
    'month_sin', 'month_cos', 'temperature_prev_1', 'temperature_prev_3', 'rainfall_prev_1',
    'rainfall_prev_3', 'soil_moisture_prev_1', 'rolling_temp_3m', 'rolling_rainfall_3m',
    'rolling_temp_6m', 'rolling_rainfall_6m', 'is_monsoon', 'pre_monsoon', 'post_monsoon',
    'is_winter_dry', 'monsoon_phase', 'monsoon_phase_sin', 'monsoon_phase_cos',
    'rainfall_climatology', 'rolling_rainfall_std_3m', 'rolling_rainfall_std_6m',
    'rolling_rainfall_cv_3m', 'rolling_rainfall_median_3m', 'rolling_rainfall_median_6m',
    'dry_months_streak', 'wet_months_streak', 'rainfall_trend', 'rainfall_acceleration',
    'rainfall_growth_rate', 'rainfall_momentum', 'rainfall_seasonal_deviation',
    'temperature_climatology', 'temperature_anomaly', 'temp_trend_3m', 'soil_moisture_trend',
    'evabs_trend', 'sro_trend', 'soil_moisture_zone_anomaly', 'zone_rainfall_climatology',
    'climate_zone_Central Plateau Region', 'climate_zone_Eastern Coastal Region',
    'climate_zone_Himalayan Region', 'climate_zone_Indo-Gangetic Plains',
    'climate_zone_North-East Region', 'climate_zone_Southern Peninsular Region',
    'climate_zone_Thar Desert Region', 'climate_zone_Western Coastal Region',
    'climate_zone_Western Ghats Region'
]

class RainfallPredictor:
    """
    Final inference layer for the Climate State Rainfall Model.
    Designed for backend and simulation engine integration.
    """
    
    def __init__(self, model_dir: str = None):
        if model_dir is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            model_dir = os.path.join(script_dir, "models")
            
        self.model_path = os.path.join(model_dir, "rainfall.pkl")
        self.metrics_path = os.path.join(model_dir, "rainfall_metrics.json")
        self.model = None
        self.metrics = None
        
        self.load_model()
        
    def load_model(self):
        """Loads the serialized model and its residual metrics."""
        try:
            logger.info(f"Loading rainfall model from {self.model_path}")
            self.model = joblib.load(self.model_path)
            
            # Load metrics for confidence estimation
            if os.path.exists(self.metrics_path):
                with open(self.metrics_path, 'r') as f:
                    self.metrics = json.load(f)
                logger.info(f"Model loaded successfully. Base RMSE: {self.metrics.get('RMSE', 'Unknown'):.4f} mm")
            else:
                self.metrics = {"RMSE": 2.0} # Fallback
                logger.warning("Metrics file not found. Using fallback heuristics for confidence.")
                
        except Exception as e:
            logger.error(f"Failed to load rainfall model: {str(e)}")
            raise RuntimeError(f"Model initialization failed: {str(e)}")
            
    def _estimate_confidence(self, request: Dict[str, Any], features: Dict[str, float]) -> str:
        """
        Estimates prediction confidence based on inputs and model residuals.
        """
        confidence = "High"
        
        # Far future prediction lowers confidence
        year = request.get("year", 2024)
        if year > 2040:
            confidence = "Low"
        elif year > 2030:
            confidence = "Medium"
            
        # Missing data that was imputed lowers confidence
        if "rainfall_prev_1" not in request or request["rainfall_prev_1"] is None:
            confidence = "Low"

        # High variance scenario (if standard deviation is extremely high)
        if features.get("rolling_rainfall_std_3m", 0) > 20:
            confidence = "Medium"
            
        return confidence

    def _determine_monsoon_status(self, predicted_rainfall: float, climatology: float, is_monsoon: bool) -> str:
        """
        Classifies the monsoon performance compared to historical averages.
        """
        if not is_monsoon:
            return "Non-Monsoon Period"
            
        if climatology <= 0:
            return "Normal Monsoon" # Prevent division by zero
            
        ratio = predicted_rainfall / climatology
        
        if ratio < 0.80:
            return "Weak Monsoon"
        elif ratio > 1.20:
            return "Strong Monsoon"
        else:
            return "Normal Monsoon"

    def prepare_features(self, request: Dict[str, Any]) -> Dict[str, float]:
        """
        Converts the raw API/Engine request into the exact dictionary required 
        by the LightGBM model. Also applies scenario modifiers.
        """
        # Scenario Simulation Modifiers
        temp_delta = float(request.get("temperature_delta", 0.0))
        rain_delta = float(request.get("rainfall_delta", 0.0))
        sm_delta = float(request.get("soil_moisture_delta", 0.0))

        # Base properties
        lat = float(request.get("latitude", 20.0))
        lon = float(request.get("longitude", 80.0))
        year = int(request.get("year", 2024))
        month = int(request.get("month", 6))
        
        # Base variables (with modifiers applied where relevant)
        # For temperature, we apply absolute shift.
        # For soil moisture and rainfall prev, we apply percentage modifications to align with downstream models.
        temp_c = float(request.get("temperature_c", 30.0)) + temp_delta
        sm = max(0.0, min(1.0, float(request.get("soil_moisture", 0.2)) * (1.0 + sm_delta / 100.0)))
        evabs = float(request.get("evabs", -0.001))
        sro = float(request.get("sro", 0.001))
        
        # Lags & Rolling
        temp_prev_1 = float(request.get("temperature_prev_1", 29.0))
        temp_prev_3 = float(request.get("temperature_prev_3", 28.0))
        rain_prev_1 = max(0.0, float(request.get("rainfall_prev_1", 10.0)) * (1.0 + rain_delta / 100.0))
        rain_prev_3 = float(request.get("rainfall_prev_3", 5.0))
        sm_prev_1 = float(request.get("soil_moisture_prev_1", 0.15))
        
        roll_temp_3m = float(request.get("rolling_temp_3m", 28.5))
        roll_rain_3m = float(request.get("rolling_rainfall_3m", 8.0))
        roll_temp_6m = float(request.get("rolling_temp_6m", 25.0))
        roll_rain_6m = float(request.get("rolling_rainfall_6m", 5.0))
        
        roll_rain_std_3m = float(request.get("rolling_rainfall_std_3m", 2.0))
        roll_rain_std_6m = float(request.get("rolling_rainfall_std_6m", 1.5))
        roll_rain_med_3m = float(request.get("rolling_rainfall_median_3m", 7.0))
        roll_rain_med_6m = float(request.get("rolling_rainfall_median_6m", 4.0))
        
        dry_streak = float(request.get("dry_months_streak", 0.0))
        wet_streak = float(request.get("wet_months_streak", 1.0))
        
        # Climatology & Trends
        rain_climo = float(request.get("rainfall_climatology", 12.0))
        zone_rain_climo = float(request.get("zone_rainfall_climatology", 10.0))
        temp_climo = float(request.get("temperature_climatology", 29.5))
        prev_climo = float(request.get("prev_climo", 10.0)) # Need for seasonal dev
        
        sm_trend = float(request.get("soil_moisture_trend", 0.01))
        evabs_trend = float(request.get("evabs_trend", -0.0001))
        sro_trend = float(request.get("sro_trend", 0.0005))
        sm_zone_anom = float(request.get("soil_moisture_zone_anomaly", 0.05))

        # --- Dynamic Engineering ---
        features = {}
        
        features['latitude'] = lat
        features['longitude'] = lon
        features['year'] = year
        features['month'] = month
        features['temperature_c'] = temp_c
        features['soil_moisture'] = sm
        features['evabs'] = evabs
        features['sro'] = sro
        
        features['month_sin'] = np.sin(2 * np.pi * month / 12.0)
        features['month_cos'] = np.cos(2 * np.pi * month / 12.0)
        
        features['temperature_prev_1'] = temp_prev_1
        features['temperature_prev_3'] = temp_prev_3
        features['rainfall_prev_1'] = rain_prev_1
        features['rainfall_prev_3'] = rain_prev_3
        features['soil_moisture_prev_1'] = sm_prev_1
        features['rolling_temp_3m'] = roll_temp_3m
        features['rolling_rainfall_3m'] = roll_rain_3m
        features['rolling_temp_6m'] = roll_temp_6m
        features['rolling_rainfall_6m'] = roll_rain_6m
        
        # Monsoon Intelligence
        features['is_monsoon'] = 1.0 if month in [6, 7, 8, 9] else 0.0
        features['pre_monsoon'] = 1.0 if month in [3, 4, 5] else 0.0
        features['post_monsoon'] = 1.0 if month in [10, 11] else 0.0
        features['is_winter_dry'] = 1.0 if month in [12, 1, 2] else 0.0
        
        phase_map = {1:0, 2:0, 12:0, 3:1, 4:1, 5:1, 6:2, 7:3, 8:3, 9:4, 10:5, 11:5}
        phase = phase_map.get(month, 0)
        features['monsoon_phase'] = float(phase)
        features['monsoon_phase_sin'] = np.sin(2 * np.pi * phase / 6.0)
        features['monsoon_phase_cos'] = np.cos(2 * np.pi * phase / 6.0)
        
        features['rainfall_climatology'] = rain_climo
        features['rolling_rainfall_std_3m'] = roll_rain_std_3m
        features['rolling_rainfall_std_6m'] = roll_rain_std_6m
        features['rolling_rainfall_cv_3m'] = roll_rain_std_3m / (roll_rain_3m + 1e-6)
        features['rolling_rainfall_median_3m'] = roll_rain_med_3m
        features['rolling_rainfall_median_6m'] = roll_rain_med_6m
        
        features['dry_months_streak'] = dry_streak
        features['wet_months_streak'] = wet_streak
        
        # Momentum & Trends
        features['rainfall_trend'] = rain_prev_1 - rain_prev_3
        short_trend = rain_prev_1 - roll_rain_3m
        long_trend = roll_rain_3m - roll_rain_6m
        features['rainfall_acceleration'] = short_trend - long_trend
        features['rainfall_growth_rate'] = max(min((rain_prev_1 - rain_prev_3) / (rain_prev_3 + 1e-6), 10.0), -10.0)
        features['rainfall_momentum'] = rain_prev_1 - rain_climo
        features['rainfall_seasonal_deviation'] = rain_prev_1 - prev_climo
        
        features['temperature_climatology'] = temp_climo
        features['temperature_anomaly'] = temp_c - temp_climo
        features['temp_trend_3m'] = roll_temp_3m - roll_temp_6m
        
        features['soil_moisture_trend'] = sm_trend
        features['evabs_trend'] = evabs_trend
        features['sro_trend'] = sro_trend
        features['soil_moisture_zone_anomaly'] = sm_zone_anom
        features['zone_rainfall_climatology'] = zone_rain_climo
        
        # Process Climate Zone (One-Hot Encoding)
        # Note: In training we didn't use underscores for region names in OHE, 
        # it was like 'climate_zone_Indo-Gangetic Plains'
        zone_raw = request.get("climate_zone", "Unknown")
        
        for feature_name in MODEL_FEATURES:
            if feature_name.startswith("climate_zone_"):
                features[feature_name] = 1.0 if feature_name == f"climate_zone_{zone_raw}" else 0.0

        # Ensure order matches exactly
        return {feat: features.get(feat, 0.0) for feat in MODEL_FEATURES}

    def predict(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predicts rainfall for a single location state.
        """
        try:
            # Prepare and structure
            features_dict = self.prepare_features(request)
            df_input = pd.DataFrame([features_dict])[MODEL_FEATURES]
            
            # Predict
            pred_val = float(self.model.predict(df_input)[0])
            
            # Transform if we used log1p, but in our training script we didn't. 
            # We enforce non-negative rainfall.
            pred_val = max(0.0, pred_val)
            
            # Intelligence
            confidence = self._estimate_confidence(request, features_dict)
            is_monsoon = features_dict['is_monsoon'] > 0.5
            monsoon_status = self._determine_monsoon_status(pred_val, features_dict['rainfall_climatology'], is_monsoon)
            
            # Confidence score bound [0.0, 1.0] using RMSE relative to prediction scale, with floor.
            rmse = self.metrics.get("RMSE", 2.0)
            score_val = max(0.0, min(1.0, 1.0 - (rmse / max(pred_val, 5.0))))
            
            return {
                "predicted_rainfall_mm": round(pred_val, 2),
                "confidence": confidence,
                "confidence_score": round(score_val, 2),
                "monsoon_status": monsoon_status,
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
            
        logger.info(f"Processing batch prediction for {len(requests)} items.")
        
        try:
            features_list = []
            for req in requests:
                features_list.append(self.prepare_features(req))
                
            df_input = pd.DataFrame(features_list)[MODEL_FEATURES]
            
            # Batch Predict
            predictions = self.model.predict(df_input)
            
            # Format outputs
            results = []
            for idx, pred_val in enumerate(predictions):
                pred_val = max(0.0, float(pred_val))
                req = requests[idx]
                feat = features_list[idx]
                
                conf = self._estimate_confidence(req, feat)
                monsoon_stat = self._determine_monsoon_status(pred_val, feat['rainfall_climatology'], feat['is_monsoon'] > 0.5)
                
                rmse = self.metrics.get("RMSE", 2.0)
                score_val = max(0.0, min(1.0, 1.0 - (rmse / max(pred_val, 5.0))))
                
                results.append({
                    "predicted_rainfall_mm": round(pred_val, 2),
                    "confidence": conf,
                    "confidence_score": round(score_val, 2),
                    "monsoon_status": monsoon_stat,
                    "source": req.get("source"),
                    "confidence_source": req.get("confidence_source"),
                    "last_updated": req.get("last_updated")
                })
                
            return results
            
        except Exception as e:
            logger.error(f"Batch prediction failed: {str(e)}", exc_info=True)
            raise

# Example Usage Block
if __name__ == "__main__":
    predictor = RainfallPredictor()
    
    sample_request = {
        "city": "Delhi",
        "climate_zone": "Indo-Gangetic Plains",
        "latitude": 28.61,
        "longitude": 77.20,
        "year": 2030,
        "month": 7,
        "temperature_c": 32.5,
        "soil_moisture": 0.35,
        "evabs": -0.003,
        "sro": 0.005,
        "temperature_prev_1": 34.0,
        "temperature_prev_3": 25.0,
        "rainfall_prev_1": 45.0,
        "rainfall_prev_3": 10.0,
        "soil_moisture_prev_1": 0.25,
        "rolling_temp_3m": 31.0,
        "rolling_rainfall_3m": 60.0,
        "rolling_temp_6m": 25.0,
        "rolling_rainfall_6m": 20.0,
        "rolling_rainfall_std_3m": 15.0,
        "rolling_rainfall_std_6m": 10.0,
        "rolling_rainfall_median_3m": 12.0,
        "rolling_rainfall_median_6m": 5.0,
        "dry_months_streak": 0.0,
        "wet_months_streak": 2.0,
        "rainfall_climatology": 210.0,
        "zone_rainfall_climatology": 180.0,
        "temperature_climatology": 31.5,
        "prev_climo": 80.0,
        "soil_moisture_trend": 0.05,
        "evabs_trend": -0.001,
        "sro_trend": 0.002,
        "soil_moisture_zone_anomaly": 0.02,
        # Simulation options
        "rainfall_delta": -10.0
    }
    
    print("\n--- Single Prediction ---")
    res = predictor.predict(sample_request)
    print(json.dumps(res, indent=2))
    
    print("\n--- Batch Prediction ---")
    batch_res = predictor.batch_predict([sample_request, sample_request])
    print(json.dumps(batch_res, indent=2))
