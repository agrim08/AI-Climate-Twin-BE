import os
import sys
import json
import numpy as np

# Ensure app directory is in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.ml_services.predict_drought import DroughtPredictor

def test_drought_intelligence():
    print("==================================================")
    print("STAGING: Initializing DroughtPredictor service...")
    print("==================================================")
    
    predictor = DroughtPredictor()
    print("DroughtPredictor loaded successfully.")
    
    # 1. Prepare sample request representing high drought conditions
    sample_request = {
        "year": 2030,
        "month": 5, 
        "latitude": 28.61,
        "longitude": 77.20,
        "temperature_c": 42.5,
        "rainfall_mm": 2.0,
        "soil_moisture": 0.08,
        "evabs": -0.005,
        "sro": 0.000,
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
        "temperature_delta": +2.0,
        "rainfall_delta": -20.0,
        "soil_moisture_delta": -15.0,
        "evaporation_delta": +10.0,
        "runoff_delta": -5.0,
        "climate_zone": "Indo-Gangetic Plains"
    }
    
    # 2. Test Part 1: Single prediction and class-probability confidence
    print("\n--- Test Part 1: Single Prediction & Confidence ---")
    pred_res = predictor.predict(sample_request)
    print(json.dumps(pred_res, indent=2))
    
    assert "drought_category" in pred_res
    assert pred_res["drought_category"] in ["Low", "Medium", "High", "Extreme"]
    assert "severity_score" in pred_res
    assert 0.0 <= pred_res["severity_score"] <= 1.0
    assert "confidence_score" in pred_res
    assert 0.0 <= pred_res["confidence_score"] <= 1.0
    assert "confidence_level" in pred_res
    assert pred_res["confidence_level"] in ["High", "Medium", "Low"]
    
    # Test confidence thresholds mapping
    p_max = max(pred_res["probabilities"].values())
    assert abs(p_max - pred_res["confidence_score"]) < 1e-4
    if p_max >= 0.85:
        assert pred_res["confidence_level"] == "High"
    elif p_max >= 0.65:
        assert pred_res["confidence_level"] == "Medium"
    else:
        assert pred_res["confidence_level"] == "Low"
        
    print("Part 1: OK")
    
    # 3. Test Batch prediction support
    print("\n--- Test Batch Prediction ---")
    batch_res = predictor.batch_predict([sample_request, sample_request])
    print(f"Batch prediction size: {len(batch_res)}")
    assert len(batch_res) == 2
    assert "drought_category" in batch_res[0]
    print("Batch Prediction: OK")

    # 4. Test Part 2: Scenario Simulation
    print("\n--- Test Part 2: Scenario Simulation (Chaining vs Direct) ---")
    sim_res = predictor.simulate_scenario(sample_request)
    print(json.dumps(sim_res, indent=2))
    
    assert "baseline_category" in sim_res
    assert "baseline_score" in sim_res
    assert "scenario_category" in sim_res
    assert "scenario_score" in sim_res
    assert "risk_change" in sim_res
    print("Part 2: OK")

    # 5. Test Part 3: Driver Analysis
    print("\n--- Test Part 3: Driver Analysis ---")
    features_dict = predictor.prepare_features(sample_request, apply_deltas=True)
    drivers_res = predictor.analyze_drivers(features_dict)
    print(f"Top active drivers: {drivers_res}")
    
    assert isinstance(drivers_res, list)
    assert len(drivers_res) > 0
    # Since rainfall is 2.0 (climatology is 20.0), Rainfall Deficit should be one of the top drivers
    assert "Rainfall Deficit" in drivers_res or "Low Soil Moisture" in drivers_res
    print("Part 3: OK")

    # 6. Test Part 4: Water Stress Assessment
    print("\n--- Test Part 4: Water stress assessment ---")
    water_res = predictor.get_water_intelligence(features_dict, pred_res["severity_score"])
    print(json.dumps(water_res, indent=2))
    
    assert 0.0 <= water_res["water_stress_index"] <= 100.0
    assert water_res["reservoir_risk"] in ["Low", "Medium", "High", "Critical"]
    assert water_res["groundwater_risk"] in ["Low", "Medium", "High", "Critical"]
    assert water_res["water_availability_status"] in ["Abundant", "Sufficient", "Stressed", "Deficit"]
    print("Part 4: OK")

    # 7. Test Part 5: Agricultural Intelligence
    print("\n--- Test Part 5: Agricultural Impact Indicators ---")
    ag_res = predictor.get_agriculture_intelligence(features_dict, pred_res["severity_score"])
    print(json.dumps(ag_res, indent=2))
    
    assert 0.0 <= ag_res["crop_stress_index"] <= 100.0
    assert ag_res["irrigation_need"] in ["Low", "Medium", "High", "Critical"]
    assert ag_res["agricultural_risk"] in ["Low", "Medium", "High", "Critical"]
    print("Part 5: OK")

    # 8. Test Part 6: Early Warning alerts
    print("\n--- Test Part 6: Early Warning Alerts ---")
    probs_list = [
        pred_res["probabilities"]["Low"],
        pred_res["probabilities"]["Medium"],
        pred_res["probabilities"]["High"],
        pred_res["probabilities"]["Extreme"]
    ]
    warning_res = predictor.generate_early_warning(probs_list, features_dict)
    print(json.dumps(warning_res, indent=2))
    
    assert "warning" in warning_res
    assert "warning_level" in warning_res
    assert "message" in warning_res
    print("Part 6: OK")

    # 9. Test Part 7: Climate Twin Integration Layer
    print("\n--- Test Part 7: Unified Twin State ---")
    twin_res = predictor.get_digital_twin_state(sample_request)
    print(json.dumps(list(twin_res.keys()), indent=2))
    
    assert "drought_prediction" in twin_res
    assert "scenario_analysis" in twin_res
    assert "drivers" in twin_res
    assert "water_intelligence" in twin_res
    assert "agriculture_intelligence" in twin_res
    assert "early_warning" in twin_res
    
    # Assert confidence keys propagate correctly to the unified prediction
    assert "confidence_score" in twin_res["drought_prediction"]
    assert "confidence_level" in twin_res["drought_prediction"]
    print("Part 7: OK")

    print("\n==================================================")
    print("SUCCESS: All verification checks passed successfully!")
    print("==================================================")

if __name__ == "__main__":
    test_drought_intelligence()
