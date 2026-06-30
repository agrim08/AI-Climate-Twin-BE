import os
import joblib
import pandas as pd
import numpy as np

# Exact features expected by the LightGBM model
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

def predict_temperature(model_path: str, params: dict) -> float:
    """
    Predicts the temperature based on the provided climate and geographical parameters.
    
    Args:
        model_path: Path to the trained .pkl model.
        params: Dictionary containing the raw input parameters.
    """
    # 1. Load Model
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found at {model_path}")
    
    model = joblib.load(model_path)
    
    # 2. Prepare the feature dictionary with default 0.0 values
    input_data = {feat: 0.0 for feat in MODEL_FEATURES}
    
    # 3. Populate base features
    for key in params:
        if key in input_data:
            input_data[key] = params[key]
            
    # 4. Handle Categorical Climate Zone
    zone = params.get("climate_zone", "").replace(" ", "_")
    if zone in CLIMATE_ZONES:
        input_data[f"climate_zone_{zone}"] = 1.0
    else:
        print(f"Warning: Unknown climate zone '{zone}'. Predictions may be less accurate.")
        
    # 5. Convert to DataFrame (LightGBM expects 2D array/DataFrame)
    # We must ensure columns are strictly ordered as the model expects
    df_input = pd.DataFrame([input_data])[MODEL_FEATURES]
    
    # 6. Predict
    prediction = model.predict(df_input)[0]
    
    return prediction

if __name__ == "__main__":
    # Define path to the model
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_file = os.path.join(script_dir, "..", "models", "temperature.pkl")
    
    # Example Parameters (e.g. A city in the Indo-Gangetic Plains during Summer)
    sample_params = {
        "latitude": 28.61,               # Delhi Latitude
        "longitude": 77.20,              # Delhi Longitude
        "year": 2024,
        "month_sin": np.sin(2 * np.pi * 6 / 12.0), # June
        "month_cos": np.cos(2 * np.pi * 6 / 12.0),
        "rainfall_mm": 50.0,             # 50 mm rainfall
        "soil_moisture": 0.25,           # 25% volumetric moisture
        "evabs": -0.001,                 # Evaporation
        "sro": 0.002,                    # Surface runoff
        
        # Historical Data (e.g. previous month was 35C)
        "temperature_prev_1": 35.5,
        "temperature_prev_3": 25.0,
        "rainfall_prev_1": 10.0,
        "rainfall_prev_3": 5.0,
        "soil_moisture_prev_1": 0.15,
        
        # Rolling Averages
        "rolling_temp_3m": 31.0,
        "rolling_temp_6m": 25.0,
        "rolling_rainfall_3m": 20.0,
        "rolling_rainfall_6m": 15.0,
        
        "climate_zone": "Indo-Gangetic Plains"
    }
    
    predicted_temp = predict_temperature(model_file, sample_params)
    
    print("\n--- Temperature Prediction Test ---")
    print(f"Location: {sample_params['climate_zone']} (Lat: {sample_params['latitude']}, Lon: {sample_params['longitude']})")
    print(f"Previous Month Temp: {sample_params['temperature_prev_1']} °C")
    print(f"Predicted Current Temp: {predicted_temp:.2f} °C")
    print("-----------------------------------\n")
