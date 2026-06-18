import os
# pyrefly: ignore [missing-import]
import xarray as xr

# Resolve the path relative to this script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "..", "data", "raw", "era5", "era5_land.nc")

ds = xr.open_dataset(file_path)

print(ds)