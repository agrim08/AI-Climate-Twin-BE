import os
import sys
import json

# Ensure app directory is in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.ml_services.predict_extreme_weather import ExtremeWeatherPredictor

def test_extreme_weather_intelligence():
    print("==================================================")
    print("STAGING: Initializing ExtremeWeatherPredictor...")
    print("==================================================")
    
    predictor = ExtremeWeatherPredictor()
    print("ExtremeWeatherPredictor loaded successfully.")
    
    # Prepare sample request representing high extreme weather conditions
    sample_request = {
        "year": 2030,
        "month": 7,  # July peak monsoon
        "latitude": 28.61,
        "longitude": 77.20,
        "temperature_c": 42.5,
        "rainfall_mm": 250.0,  # Heavy rainfall
        "soil_moisture": 0.42,  # Saturation
        "evabs": -0.005,
        "sro": 0.045,  # High surface runoff
        
        # Lag variables
        "temperature_prev_1": 40.0,
        "temperature_prev_3": 38.0,
        "rainfall_prev_1": 150.0,
        "rainfall_prev_3": 100.0,
        "soil_moisture_prev_1": 0.40,
        "rolling_temp_3m": 39.5,
        "rolling_rainfall_3m": 120.0,
        "rolling_temp_6m": 35.0,
        "rolling_rainfall_6m": 90.0,
        
        # Climatologies (city × month level)
        "temp_climo_mean": 38.0,
        "temp_climo_std": 2.0,
        "rain_climo_mean": 180.0,
        "rain_climo_std": 30.0,
        "sm_climo_mean": 0.35,
        "sm_climo_std": 0.05,

        # Zone Climatologies (zone × month level)
        "zone_temp_mean": 38.0,
        "zone_temp_std": 2.0,
        "zone_rain_mean": 180.0,
        "zone_rain_std": 30.0,

        # India-wide seasonal baseline
        "seasonal_temp_mean": 38.0,
        "seasonal_rain_mean": 180.0,

        # Streaks / Persistence
        "consecutive_hot_months": 2.0,
        "consecutive_wet_months": 3.0,

        # Scenario delta modifiers
        "temperature_delta": +2.0,
        "rainfall_delta": +20.0,
        "soil_moisture_delta": +10.0,
        "evaporation_delta": +5.0,
        "runoff_delta": +15.0,

        # Additional metadata
        "climate_zone": "Indo-Gangetic Plains"
    }
    
    # 1. Test Single Prediction
    print("\n--- Test Part 1: Single Prediction & Confidence ---")
    pred_res = predictor.predict(sample_request, apply_deltas=True)
    
    # Pop out internal private properties for printing
    print_res = pred_res.copy()
    hw_probs = print_res["heatwave"].pop("_probabilities", None)
    hw_feats = print_res["heatwave"].pop("_features", None)
    er_probs = print_res["extreme_rainfall"].pop("_probabilities", None)
    er_feats = print_res["extreme_rainfall"].pop("_features", None)
    print(json.dumps(print_res, indent=2))
    
    assert "heatwave" in pred_res
    assert "extreme_rainfall" in pred_res
    assert pred_res["heatwave"]["category"] in ["Low", "Medium", "High", "Extreme"]
    assert pred_res["extreme_rainfall"]["category"] in ["Low", "Medium", "High", "Extreme"]
    assert 0.0 <= pred_res["heatwave"]["severity"] <= 100.0
    assert 0.0 <= pred_res["extreme_rainfall"]["severity"] <= 100.0
    assert 0.0 <= pred_res["heatwave"]["confidence"] <= 1.0
    assert 0.0 <= pred_res["extreme_rainfall"]["confidence"] <= 1.0
    print("Part 1: OK")
    
    # 2. Test Batch Prediction
    print("\n--- Test Batch Prediction ---")
    batch_res = predictor.batch_predict([sample_request, sample_request])
    print(f"Batch prediction size: {len(batch_res)}")
    assert len(batch_res) == 2
    assert "heatwave" in batch_res[0]
    print("Batch Prediction: OK")

    # 3. Test Combined Overall Risk
    print("\n--- Test Part 2: Combined Extreme Weather Risk ---")
    risk_res = predictor.calculate_overall_risk(
        pred_res["heatwave"], pred_res["extreme_rainfall"], hw_probs, er_probs
    )
    print(json.dumps(risk_res, indent=2))
    assert risk_res["overall_extreme_weather_risk"] in ["Low", "Medium", "High", "Extreme"]
    assert 0.0 <= risk_res["overall_risk_score"] <= 100.0
    print("Part 2: OK")

    # 4. Test Scenario Simulation
    print("\n--- Test Part 3: Scenario Simulation (Chaining vs Direct) ---")
    sim_res = predictor.simulate_scenario(sample_request)
    print(json.dumps(sim_res, indent=2))
    assert "baseline_risk" in sim_res
    assert "baseline_score" in sim_res
    assert "scenario_risk" in sim_res
    assert "scenario_score" in sim_res
    assert "risk_change" in sim_res
    print("Part 3: OK")

    # 5. Test Driver Analysis
    print("\n--- Test Part 4: Driver Analysis ---")
    drivers_res = predictor.analyze_drivers(hw_feats, er_feats)
    print(f"Top active drivers: {drivers_res}")
    assert isinstance(drivers_res, list)
    assert len(drivers_res) > 0
    print("Part 4: OK")

    # 6. Test Impact Assessments
    print("\n--- Test Part 5: Impact Advisories ---")
    temp_anom = hw_feats.get("hw_temperature_anomaly", 0.0)
    runoff_press = er_feats.get("er_runoff_pressure", 0.0)
    soil_sat = er_feats.get("er_soil_saturation", 0.0)
    rain_anom = er_feats.get("er_rainfall_anomaly", 0.0)
    
    hw_impact = predictor.get_heatwave_impact(pred_res["heatwave"]["severity"], temp_anom, hw_probs)
    er_impact = predictor.get_extreme_rainfall_impact(pred_res["extreme_rainfall"]["severity"], runoff_press, soil_sat, rain_anom)
    print("Heatwave Impact:")
    print(json.dumps(hw_impact, indent=2))
    print("Rainfall Impact:")
    print(json.dumps(er_impact, indent=2))
    
    assert hw_impact["health_risk"] in ["Low", "Medium", "High", "Extreme"]
    assert er_impact["flash_flood_risk"] in ["Low", "Medium", "High", "Extreme"]
    print("Part 5: OK")

    # 7. Test Early Warning alerts
    print("\n--- Test Part 6: Early Warning Alerts ---")
    warning_res = predictor.generate_early_warning(hw_probs, er_probs)
    print(json.dumps(warning_res, indent=2))
    assert "warning" in warning_res
    assert "warning_level" in warning_res
    assert "event_type" in warning_res
    assert "message" in warning_res
    print("Part 6: OK")

    # 8. Test Climate Twin Integration Layer (Twin State)
    print("\n--- Test Part 7: Unified Twin State ---")
    twin_res = predictor.get_digital_twin_state(sample_request)
    print(json.dumps(list(twin_res.keys()), indent=2))
    assert "heatwave_prediction" in twin_res
    assert "rainfall_extreme_prediction" in twin_res
    assert "overall_extreme_weather" in twin_res
    assert "scenario_analysis" in twin_res
    assert "driver_analysis" in twin_res
    assert "impact_assessment" in twin_res
    assert "early_warning" in twin_res
    print("Part 7: OK")

    print("\n==================================================")
    print("SUCCESS: All verification checks passed successfully!")
    print("==================================================")

if __name__ == "__main__":
    test_extreme_weather_intelligence()
