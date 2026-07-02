# src/ingestion/weather_full.py
import requests
import pandas as pd
import json
from datetime import datetime
import os

print("=" * 50)
print("GRIDGUARD WEATHER INGESTION")
print("=" * 50)

# Load villages
with open("data/villages.json", "r") as f:
    data = json.load(f)
    villages = data["villages"]

print(f"Loading weather for {len(villages)} villages...")
print("")

all_data = []

for village in villages:
    print(f"Fetching: {village['name']} ({village['lat']}, {village['lon']})")
    
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": village["lat"],
        "longitude": village["lon"],
        "hourly": [
            "temperature_2m",
            "shortwave_radiation",
            "precipitation",
            "windspeed_10m",
            "relative_humidity_2m"
        ],
        "timezone": "Africa/Nairobi",
        "forecast_days": 7
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            weather_data = response.json()
            
            # Convert to DataFrame
            df = pd.DataFrame(weather_data["hourly"])
            df["village"] = village["name"]
            df["village_id"] = village["id"]
            df["fetched_at"] = datetime.now().isoformat()
            
            all_data.append(df)
            print(f"  ✅ Success - {len(df)} rows")
        else:
            print(f"  ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"  ❌ Exception: {e}")
    
    print("")

# Combine all data
if all_data:
    final_df = pd.concat(all_data, ignore_index=True)
    
    # Save as Parquet
    filename = f"data/raw/weather_{datetime.now().strftime('%Y%m%d_%H%M')}.parquet"
    final_df.to_parquet(filename, index=False)
    
    print("=" * 50)
    print("INGESTION COMPLETE!")
    print("=" * 50)
    print(f"Total rows: {len(final_df)}")
    print(f"Saved to: {filename}")
    print(f"Columns: {list(final_df.columns)}")
    print("")
    print("Sample data:")
    print(final_df[["village", "time", "temperature_2m", "shortwave_radiation"]].head(10))
else:
    print("❌ No data collected!")