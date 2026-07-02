# src/ingestion/simulate_iot.py
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import random

print("=" * 50)
print("IOT ENERGY SIMULATOR")
print("=" * 50)

# Load villages
with open("data/villages.json", "r") as f:
    data = json.load(f)
    villages = data["villages"]

print(f"Generating IoT data for {len(villages)} villages...")
print("")

all_readings = []

# Generate 7 days of 15-minute interval data for each village
start_time = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(days=7)
end_time = datetime.now()

for village in villages:
    print(f"Generating: {village['name']}")
    
    # Base consumption varies by village type
    # Battery capacity affects consumption patterns
    base_consumption = village.get("battery_capacity", 200) / 2  # Average power in kW
    population = village.get("population", 300)
    
    # Generate timestamps at 15-minute intervals
    timestamps = pd.date_range(start=start_time, end=end_time, freq='15min')
    
    for ts in timestamps:
        # Time of day patterns
        hour = ts.hour
        
        # Morning peak (6-9 AM)
        if 6 <= hour < 9:
            time_factor = 1.5
        # Evening peak (6-10 PM)
        elif 18 <= hour < 22:
            time_factor = 1.8
        # Night (11 PM - 5 AM)
        elif 23 <= hour or hour < 6:
            time_factor = 0.3
        # Midday (10 AM - 5 PM)
        else:
            time_factor = 0.8
        
        # Weekend adjustment (Saturday/Sunday)
        if ts.weekday() >= 5:
            time_factor *= 0.7
        
        # Add random noise
        noise = np.random.normal(1.0, 0.15)
        
        # Calculate consumption in kW
        consumption = base_consumption * time_factor * noise
        consumption = max(0, consumption)  # Can't be negative
        
        # Add some "events" (random spikes)
        if random.random() < 0.02:  # 2% chance of spike
            consumption *= (1 + random.uniform(0.1, 0.5))
        
        all_readings.append({
            "village_id": village["id"],
            "village_name": village["name"],
            "timestamp": ts.isoformat(),
            "hour": hour,
            "day_of_week": ts.weekday(),
            "is_weekend": 1 if ts.weekday() >= 5 else 0,
            "consumption_kw": round(consumption, 2),
            "battery_level": round(random.uniform(0.3, 0.95), 2),  # Simulated battery %
            "device_id": f"SENSOR_{village['id']}_{random.randint(1, 5)}"
        })
    
    print(f"  ✅ Generated {len([x for x in all_readings if x['village_id'] == village['id']])} readings")

# Convert to DataFrame
df = pd.DataFrame(all_readings)

# Save as Parquet
filename = f"data/raw/iot_{datetime.now().strftime('%Y%m%d_%H%M')}.parquet"
df.to_parquet(filename, index=False)

print("")
print("=" * 50)
print("SIMULATION COMPLETE!")
print("=" * 50)
print(f"Total readings: {len(df)}")
print(f"Villages: {df['village_name'].nunique()}")
print(f"Saved to: {filename}")
print("")
print("Sample data:")
print(df[["village_name", "timestamp", "consumption_kw", "battery_level"]].head(10))
print("")
print("Summary by village:")
summary = df.groupby('village_name').agg({
    'consumption_kw': ['mean', 'min', 'max'],
    'battery_level': ['mean']
}).round(2)
print(summary)