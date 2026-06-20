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
MODEL_FEATURES = [
    'latitude', 'longitude', 'year', 'month_sin', 'month_cos', 
    'rainfall_mm', 'soil_moisture', 'evabs', 'sro', 
    'temperature_prev_1', 'temperature_prev_3', 
    'rainfall_prev_1', 'rainfall_prev_3', 'soil_moisture_prev_1', 
    'rolling_temp_3m', 'rolling_temp_6m', 
    'rolling_rainfall_3m', 'rolling_rainfall_6m', 
    'climate_zone_Central_Plateau_Region', 'climate_zone_Eastern_Coastal_Region', 
    'climate_zone_Himalayan_Region', 'climate_zone_Indo-Gangetic_Plains', 
    'climate_zone_North-East_Region', 'climate_zone_Southern_Peninsular_Region', 
    'climate_zone_Thar_Desert_Region', 'climate_zone_Western_Coastal_Region', 
    'climate_zone_Western_Ghats_Region'
]

CLIMATE_ZONES = [
    'Central_Plateau_Region', 'Eastern_Coastal_Region', 'Himalayan_Region',
    'Indo-Gangetic_Plains', 'North-East_Region', 'Southern_Peninsular_Region',
    'Thar_Desert_Region', 'Western_Coastal_Region', 'Western_Ghats_Region'
]

class TemperaturePredictor:
    """
    Final inference layer for the Climate State Temperature Model.
    Designed for backend and simulation engine integration.
    """
    
    def __init__(self, model_dir: str = None):
        if model_dir is None:
            # Default to the known model directory relative to this script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            model_dir = os.path.join(script_dir, "models")
            
        self.model_path = os.path.join(model_dir, "temperature.pkl")
        self.metrics_path = os.path.join(model_dir, "temperature_metrics.json")
        self.model = None
        self.metrics = None
        
        self.load_model()
        
    def load_model(self):
        """Loads the serialized LightGBM model and its residual metrics."""
        try:
            logger.info(f"Loading temperature model from {self.model_path}")
            self.model = joblib.load(self.model_path)
            
            # Load metrics for confidence estimation
            if os.path.exists(self.metrics_path):
                with open(self.metrics_path, 'r') as f:
                    self.metrics = json.load(f)
                logger.info(f"Model loaded successfully. Base RMSE: {self.metrics.get('RMSE', 'Unknown'):.4f}°C")
            else:
                self.metrics = {"RMSE": 1.5} # Fallback default
                logger.warning("Metrics file not found. Using fallback heuristics for confidence.")
                
        except Exception as e:
            logger.error(f"Failed to load temperature model: {str(e)}")
            raise RuntimeError(f"Model initialization failed: {str(e)}")
            
    def _estimate_confidence(self, request: Dict[str, Any]) -> str:
        """
        Estimates prediction confidence based on input extremity and model residual statistics.
        Out-of-distribution inputs (far future, extreme climate events) lower the confidence 
        from 'high' to 'medium' or 'low'.
        """
        confidence = "high"
        
        # Heuristic rules based on training distributions
        year = request.get("year", 2024)
        if year > 2040:
            confidence = "low"  # Too far into the future, highly uncertain
        elif year > 2030:
            confidence = "medium"
            
        # Extreme residual triggers (e.g. massive rainfall anomaly)
        if request.get("rainfall_mm", 0) > 300: # 300mm a month is extreme
            confidence = "low"
        
        # Missing critical lag features (imputed as 0s in prepare_features)
        if request.get("temperature_prev_1") is None:
            confidence = "low"
            
        return confidence

    def prepare_features(self, request: Dict[str, Any]) -> Dict[str, float]:
        """
        Converts the raw API/Engine request into the exact dictionary required 
        by the LightGBM model (including auto-generating cyclic features and OHE).
        """
        # Validate required base fields
        required_fields = ["latitude", "longitude", "year", "month", "climate_zone"]
        for field in required_fields:
            if field not in request:
                raise ValueError(f"Missing required field: {field}")
                
        # Initialize default vector with zeros
        features = {feat: 0.0 for feat in MODEL_FEATURES}
        
        # Direct float mappings
        direct_mappings = [
            "latitude", "longitude", "year", "rainfall_mm", "soil_moisture", 
            "evabs", "sro", "temperature_prev_1", "temperature_prev_3", 
            "rainfall_prev_1", "rainfall_prev_3", "soil_moisture_prev_1", 
            "rolling_temp_3m", "rolling_temp_6m", 
            "rolling_rainfall_3m", "rolling_rainfall_6m"
        ]
        
        for field in direct_mappings:
            if field in request and request[field] is not None:
                features[field] = float(request[field])
                
        # 5. Automatically generate month_sin and month_cos
        month = float(request["month"])
        if not (1 <= month <= 12):
            raise ValueError(f"Month must be between 1 and 12, got {month}")
            
        features["month_sin"] = float(np.sin(2 * np.pi * month / 12.0))
        features["month_cos"] = float(np.cos(2 * np.pi * month / 12.0))
        
        # Process Climate Zone (One-Hot Encoding)
        zone_raw = request["climate_zone"]
        zone_formatted = str(zone_raw).replace(" ", "_")
        zone_key = f"climate_zone_{zone_formatted}"
        
        if zone_formatted in CLIMATE_ZONES:
            features[zone_key] = 1.0
        else:
            logger.warning(f"Unknown climate zone '{zone_raw}' provided. All OHE flags set to 0.")

        return features

    def predict(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predicts temperature for a single location state.
        
        Returns:
            Dict containing the predicted temperature and confidence interval.
        """
        try:
            # Prepare and structure
            features_dict = self.prepare_features(request)
            df_input = pd.DataFrame([features_dict])[MODEL_FEATURES]
            
            # Predict
            pred_val = float(self.model.predict(df_input)[0])
            
            # Confidence Estimation
            confidence = self._estimate_confidence(request)
            
            return {
                "predicted_temperature_c": round(pred_val, 2),
                "confidence": confidence,
                "model_rmse_c": round(self.metrics.get("RMSE", 1.5), 2)
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
            # Prepare all inputs
            features_list = []
            confidences = []
            
            for req in requests:
                features_list.append(self.prepare_features(req))
                confidences.append(self._estimate_confidence(req))
                
            df_input = pd.DataFrame(features_list)[MODEL_FEATURES]
            
            # Batch Predict
            predictions = self.model.predict(df_input)
            
            # Format outputs
            results = []
            for pred_val, conf in zip(predictions, confidences):
                results.append({
                    "predicted_temperature_c": round(float(pred_val), 2),
                    "confidence": conf,
                    "model_rmse_c": round(self.metrics.get("RMSE", 1.5), 2)
                })
                
            return results
            
        except Exception as e:
            logger.error(f"Batch prediction failed: {str(e)}", exc_info=True)
            raise

# Example Usage Block (can be executed directly for verification)
if __name__ == "__main__":
    predictor = TemperaturePredictor()
    
    sample_request = {
        "city": "Delhi",
        "climate_zone": "Indo-Gangetic Plains",
        "latitude": 28.61,
        "longitude": 77.20,
        "year": 2030,
        "month": 5,
        "rainfall_mm": 12.5,
        "soil_moisture": 0.2,
        "evabs": -0.002,
        "sro": 0.001,
        "temperature_prev_1": 34.0,
        "temperature_prev_3": 22.0,
        "rainfall_prev_1": 5.0,
        "rainfall_prev_3": 10.0,
        "soil_moisture_prev_1": 0.15,
        "rolling_temp_3m": 29.0,
        "rolling_temp_6m": 20.0,
        "rolling_rainfall_3m": 8.0,
        "rolling_rainfall_6m": 12.0
    }
    
    print("\n--- Single Prediction ---")
    res = predictor.predict(sample_request)
    print(json.dumps(res, indent=2))
    
    print("\n--- Batch Prediction ---")
    batch_res = predictor.batch_predict([sample_request, sample_request])
    print(json.dumps(batch_res, indent=2))
