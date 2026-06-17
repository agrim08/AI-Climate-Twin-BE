import os
# pyrefly: ignore [missing-import]
import xarray as xr
import numpy as np

def explore_dataset(file_path: str):
    print(f"--- Exploring Dataset: {file_path} ---\n")
    
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    # Open dataset
    ds = xr.open_dataset(file_path)
    
    print("1. Dataset Summary")
    print(ds)
    print("\n" + "="*50 + "\n")

    print("2. Coordinate Ranges")
    lat_min, lat_max = ds['latitude'].min().item(), ds['latitude'].max().item()
    lon_min, lon_max = ds['longitude'].min().item(), ds['longitude'].max().item()
    time_min, time_max = ds['valid_time'].min().values, ds['valid_time'].max().values
    
    print(f"Latitude:  {lat_min:.2f} to {lat_max:.2f}")
    print(f"Longitude: {lon_min:.2f} to {lon_max:.2f}")
    print(f"Time:      {time_min} to {time_max}")
    print("\n" + "="*50 + "\n")

    variables = ['t2m', 'tp', 'swvl1', 'swvl2', 'evabs', 'sro']
    
    print("3. Variable Statistics (Min/Max)")
    for var in variables:
        if var in ds:
            var_min = ds[var].min().item()
            var_max = ds[var].max().item()
            print(f"{var:>6}: Min = {var_min:10.4f}, Max = {var_max:10.4f}")
        else:
            print(f"{var:>6}: Not found in dataset")
            
    print("\n" + "="*50 + "\n")

    print("4. Missing Values Check")
    for var in variables:
        if var in ds:
            # We can use isnull().sum() or count the valid values vs total
            # Note: isnull().sum().item() can be slow on large datasets without dask, 
            # but for 700MB it should take a few seconds
            print(f"Checking {var} for missing values...")
            missing_count = int(ds[var].isnull().sum().item())
            total_count = ds[var].size
            missing_pct = (missing_count / total_count) * 100
            print(f"{var:>6}: {missing_count} missing out of {total_count} ({missing_pct:.2f}%)")
            
    print("\n--- Exploration Complete ---")

if __name__ == "__main__":
    # Resolve relative path to data
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "..", "data", "raw", "era5", "era5_land.nc")
    explore_dataset(file_path)