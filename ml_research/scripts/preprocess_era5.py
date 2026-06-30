import os
import pandas as pd
import numpy as np

def generate_percentile_labels(df, col, q_low=0.75, q_high=0.90, labels=['Low', 'Medium', 'High']):
    """Helper to generate percentile-based risk labels."""
    # Compute per-city percentiles to account for different baselines
    def label_city(group):
        p_low = group[col].quantile(q_low)
        p_high = group[col].quantile(q_high)
        
        conditions = [
            group[col] > p_high,
            group[col] > p_low
        ]
        choices = [labels[2], labels[1]]
        
        return pd.Series(np.select(conditions, choices, default=labels[0]), index=group.index)

    return df.groupby('city', group_keys=False).apply(label_city)

def process_climate_data(input_file: str, output_file: str):
    print(f"Reading raw city dataset from {input_file}...")
    df = pd.read_csv(input_file)
    
    df['date'] = pd.to_datetime(df['date'])
    
    # -------------------------------------------------------------------------
    # 1. Unit Conversion & Basic Feature Engineering
    # -------------------------------------------------------------------------
    print("Applying unit conversions and creating basic features...")
    df['temperature_c'] = df['t2m'] - 273.15
    df['rainfall_mm'] = df['tp'] * 1000.0
    
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    
    # Cyclic month features
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12.0)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12.0)
    
    # Average soil moisture
    df['soil_moisture'] = (df['swvl1'] + df['swvl2']) / 2.0
    
    # -------------------------------------------------------------------------
    # 2. Lag and Rolling Features
    # -------------------------------------------------------------------------
    print("Calculating lag and rolling features per city...")
    # Sort ensure chronological order per city
    df = df.sort_values(by=['city', 'date']).reset_index(drop=True)
    
    # We will use groupby to ensure lags don't cross between cities
    grouped = df.groupby('city')
    
    df['temperature_prev_1'] = grouped['temperature_c'].shift(1)
    df['temperature_prev_3'] = grouped['temperature_c'].shift(3)
    
    df['rainfall_prev_1'] = grouped['rainfall_mm'].shift(1)
    df['rainfall_prev_3'] = grouped['rainfall_mm'].shift(3)
    
    df['soil_moisture_prev_1'] = grouped['soil_moisture'].shift(1)
    
    # Rolling averages (using min_periods=1 to not lose too much data, or min_periods=window to be strict)
    # The requirements say we must drop missing values later, so min_periods=window is safer for ML
    df['rolling_temp_3m'] = grouped['temperature_c'].transform(lambda x: x.rolling(3).mean())
    df['rolling_rainfall_3m'] = grouped['rainfall_mm'].transform(lambda x: x.rolling(3).mean())
    df['rolling_temp_6m'] = grouped['temperature_c'].transform(lambda x: x.rolling(6).mean())
    df['rolling_rainfall_6m'] = grouped['rainfall_mm'].transform(lambda x: x.rolling(6).mean())
    
    # -------------------------------------------------------------------------
    # 3. Target Variables
    # -------------------------------------------------------------------------
    print("Generating target variables...")
    df['target_temperature_next_month'] = grouped['temperature_c'].shift(-1)
    df['target_rainfall_next_month'] = grouped['rainfall_mm'].shift(-1)
    
    # -------------------------------------------------------------------------
    # 4. Risk Labels
    # -------------------------------------------------------------------------
    print("Generating risk labels...")
    # Heatwave risk: based on temperature percentiles
    df['heatwave_risk'] = generate_percentile_labels(df, 'temperature_c', 0.75, 0.90, ['Low', 'Medium', 'High'])
    
    # Drought risk: based on inverse of rainfall and soil moisture
    # Let's create a combined drought index: lower soil moisture + lower rainfall = higher drought risk
    # We negate so that HIGHER value means MORE drought, then use the percentile helper
    df['drought_index'] = -1.0 * (df['rainfall_mm'] + (df['soil_moisture'] * 100)) # Simple combination
    df['drought_risk'] = generate_percentile_labels(df, 'drought_index', 0.75, 0.90, ['Low', 'Medium', 'High'])
    df.drop(columns=['drought_index'], inplace=True)
    
    # Climate Risk Score (0-100)
    # Simple heuristic: normalize temp (higher is riskier), normalize drought (higher is riskier)
    # We will compute a global 0-100 score
    temp_norm = (df['temperature_c'] - df['temperature_c'].min()) / (df['temperature_c'].max() - df['temperature_c'].min())
    
    # Encode risks as 0, 0.5, 1.0
    risk_map = {'Low': 0.0, 'Medium': 0.5, 'High': 1.0}
    hw_score = df['heatwave_risk'].map(risk_map)
    dr_score = df['drought_risk'].map(risk_map)
    
    # Weighted sum
    raw_risk_score = (temp_norm * 0.3) + (hw_score * 0.35) + (dr_score * 0.35)
    df['climate_risk_score'] = (raw_risk_score * 100).clip(0, 100).round(2)
    
    # -------------------------------------------------------------------------
    # 5. Data Cleaning
    # -------------------------------------------------------------------------
    print("Cleaning dataset...")
    # Replace inf with NaN so we can drop them
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    
    # Drop rows with NaN (caused by shifts and rolling)
    df.dropna(inplace=True)
    
    # Drop duplicates
    df.drop_duplicates(inplace=True)
    
    # Select final columns in order
    final_columns = [
        'city', 'climate_zone', 'latitude', 'longitude', 'date', 'year', 'month',
        'temperature_c', 'rainfall_mm', 'soil_moisture', 'evabs', 'sro',
        'month_sin', 'month_cos', 
        'temperature_prev_1', 'temperature_prev_3',
        'rainfall_prev_1', 'rainfall_prev_3', 'soil_moisture_prev_1',
        'rolling_temp_3m', 'rolling_rainfall_3m',
        'rolling_temp_6m', 'rolling_rainfall_6m',
        'target_temperature_next_month', 'target_rainfall_next_month',
        'drought_risk', 'heatwave_risk', 'climate_risk_score'
    ]
    df = df[final_columns]
    
    # Ensure datatypes
    df['year'] = df['year'].astype(int)
    df['month'] = df['month'].astype(int)
    
    # Sort
    df = df.sort_values(by=['city', 'date']).reset_index(drop=True)
    
    # -------------------------------------------------------------------------
    # 6. Save and Validation Report
    # -------------------------------------------------------------------------
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df.to_csv(output_file, index=False)
    print(f"Dataset successfully saved to {output_file}\n")
    
    print("=== VALIDATION REPORT ===")
    print(f"Total Rows:    {len(df)}")
    print(f"Total Cities:  {df['city'].nunique()}")
    print(f"Date Range:    {df['date'].min().date()} to {df['date'].max().date()}")
    print("\nMissing Values Summary:")
    print(df.isnull().sum()[df.isnull().sum() > 0]) # Should be empty
    print("\nSample Rows:")
    print(df.head(3)[['city', 'date', 'temperature_c', 'rainfall_mm', 'climate_risk_score']])
    print("\nDescriptive Statistics (Key Variables):")
    print(df[['temperature_c', 'rainfall_mm', 'soil_moisture', 'climate_risk_score']].describe().round(2))
    print("=========================")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, "..", "data", "raw", "city_raw_climate.csv")
    output_file = os.path.join(script_dir, "..", "data", "processed", "climate_master.csv")
    
    process_climate_data(input_file, output_file)
