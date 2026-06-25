import asyncio
import joblib
import numpy as np
import pandas as pd
from app.ml_services.predict_drought import DroughtPredictor, MODEL_FEATURES, LABEL_DECODER

async def main():
    predictor = DroughtPredictor()
    print("Model type:", type(predictor.model))
    
    # Let's inspect the model booster if it's LightGBM
    try:
        booster = predictor.model.booster_
        print("Booster features:", booster.feature_name()[:10], "... total:", len(booster.feature_name()))
    except Exception as e:
        print("Could not inspect booster:", e)
        
    # Let's see if the model has classes
    try:
        print("Model classes:", predictor.model.classes_)
    except Exception as e:
        print("Could not get model classes:", e)

    # Let's check if we can get non-Low predictions by testing other records in the climate dataset
    # We can load the processed climate_master.csv or drought_training_dataset.csv
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, "ml_research", "data", "processed", "drought_training_dataset.csv")
    if os.path.exists(data_path):
        print(f"Loading dataset from {data_path}")
        df = pd.read_csv(data_path)
        print("Dataset shape:", df.shape)
        # Let's check the distribution of the target in the dataset
        if 'drought_category' in df.columns:
            print("Target 'drought_category' distribution in CSV:")
            print(df['drought_category'].value_counts())
        elif 'drought_class' in df.columns:
            print("Target 'drought_class' distribution in CSV:")
            print(df['drought_class'].value_counts())
            
        # Let's make predictions on all rows of the dataset using the loaded model and see if we get different classes
        # The training features are in MODEL_FEATURES
        X = df[MODEL_FEATURES]
        preds = predictor.model.predict(X)
        pred_labels = [LABEL_DECODER[int(p)] for p in preds]
        from collections import Counter
        print("Predicted categories distribution on dataset:")
        print(Counter(pred_labels))
    else:
        print("Training dataset not found at", data_path)

if __name__ == "__main__":
    asyncio.run(main())
