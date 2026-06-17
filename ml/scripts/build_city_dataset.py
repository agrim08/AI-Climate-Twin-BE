import os
import json
import pandas as pd
# pyrefly: ignore [missing-import]
import xarray as xr
from tqdm import tqdm

def extract_city_data(era5_path: str, locations_path: str, output_path: str):
    print(f"Loading representative locations from {locations_path}...")
    with open(locations_path, 'r') as f:
        locations = json.load(f)

    print(f"Loading ERA5 dataset from {era5_path}...")
    ds = xr.open_dataset(era5_path)

    all_cities_data = []

    print("Extracting data for each location...")
    for city, data in tqdm(locations.items(), desc="Processing Locations"):
        lat = data["lat"]
        lon = data["lon"]
        climate_zone = data["climate_zone"]

        try:
            city_ds = ds.sel(latitude=lat, longitude=lon, method="nearest")
            city_df = city_ds.to_dataframe().reset_index()
            
            city_df['city'] = city
            city_df['latitude'] = lat
            city_df['longitude'] = lon
            city_df['climate_zone'] = climate_zone
            
            if 'valid_time' in city_df.columns:
                city_df.rename(columns={'valid_time': 'date'}, inplace=True)
                
            cols_to_keep = ['city', 'climate_zone', 'latitude', 'longitude', 'date', 
                            't2m', 'tp', 'swvl1', 'swvl2', 'evabs', 'sro']
            
            city_df = city_df[cols_to_keep]
            all_cities_data.append(city_df)
            
        except Exception as e:
            print(f"Error processing {city}: {e}")

    print("Concatenating location data...")
    final_df = pd.concat(all_cities_data, ignore_index=True)
    
    final_df = final_df.sort_values(by=['city', 'date']).reset_index(drop=True)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"Saving to {output_path}...")
    final_df.to_csv(output_path, index=False)
    
    print("\n=== EXTRACTION VALIDATION REPORT ===")
    print(f"Total Locations: {len(locations)}")
    print(f"Climate Zones Covered: {final_df['climate_zone'].nunique()}")
    print(f"Date Range: {final_df['date'].min().date()} to {final_df['date'].max().date()}")
    
    print("\nRecords Per Zone:")
    zone_counts = final_df['climate_zone'].value_counts()
    for zone, count in zone_counts.items():
        print(f"{zone}: {count} records")
        
    print("\nSample Distribution (First 3 rows):")
    print(final_df.head(3)[['city', 'climate_zone', 'date', 't2m']])
    print("====================================\n")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, "..", "data", "raw", "era5", "era5_land.nc")
    locations_file = os.path.join(script_dir, "..", "config", "representative_locations.json")
    output_file = os.path.join(script_dir, "..", "data", "raw", "city_raw_climate.csv")
    
    extract_city_data(input_file, locations_file, output_file)
