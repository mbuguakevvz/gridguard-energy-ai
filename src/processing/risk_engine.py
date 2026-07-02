# src/processing/risk_engine.py
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import os

print("=" * 60)
print("GRIDGUARD RISK ENGINE")
print("=" * 60)

# Load weather data
weather_files = [f for f in os.listdir('data/raw') if f.startswith('weather_') and f.endswith('.parquet')]
if not weather_files:
    print("❌ No weather data found!")
    exit(1)

weather_file = sorted(weather_files)[-1]  # Latest file
weather_df = pd.read_parquet(f'data/raw/{weather_file}')
print(f"✅ Loaded weather data: {len(weather_df)} rows")

# Load IoT data
iot_files = [f for f in os.listdir('data/raw') if f.startswith('iot_') and f.endswith('.parquet')]
if not iot_files:
    print("❌ No IoT data found!")
    exit(1)

iot_file = sorted(iot_files)[-1]  # Latest file
iot_df = pd.read_parquet(f'data/raw/{iot_file}')
print(f"✅ Loaded IoT data: {len(iot_df)} rows")

# Load village info
with open("data/villages.json", "r") as f:
    data = json.load(f)
    villages = data["villages"]

# Convert timestamps
weather_df['time'] = pd.to_datetime(weather_df['time'])
iot_df['timestamp'] = pd.to_datetime(iot_df['timestamp'])

# Create risk scores
print("\n" + "=" * 60)
print("CALCULATING RISK SCORES")
print("=" * 60)

risk_data = []

for village in villages:
    village_id = village['id']
    village_name = village['name']
    battery_capacity = village['battery_capacity']
    
    print(f"\n📊 Analyzing: {village_name}")
    
    # Filter data for this village
    weather_village = weather_df[weather_df['village_id'] == village_id]
    iot_village = iot_df[iot_df['village_id'] == village_id]
    
    if weather_village.empty or iot_village.empty:
        print(f"  ⚠️ No data for {village_name}, skipping")
        continue
    
    # Merge weather and IoT data
    # For each IoT timestamp, find the nearest weather hour
    iot_village = iot_village.copy()
    iot_village['hour'] = iot_village['timestamp'].dt.floor('H')
    weather_village['hour'] = weather_village['time']
    
    merged = pd.merge(
        iot_village,
        weather_village[['hour', 'village_id', 'shortwave_radiation', 'temperature_2m', 'precipitation']],
        on=['hour', 'village_id'],
        how='left'
    )
    
    # Fill missing weather data (forward fill)
    merged['shortwave_radiation'] = merged['shortwave_radiation'].ffill()
    merged['temperature_2m'] = merged['temperature_2m'].ffill()
    merged['precipitation'] = merged['precipitation'].fillna(0)
    
    # Calculate risk factors
    # Factor 1: Solar deficit (low radiation means less solar generation)
    merged['solar_deficit'] = 1 - (merged['shortwave_radiation'] / 500)  # 500 W/m² is good
    merged['solar_deficit'] = merged['solar_deficit'].clip(0, 1)
    
    # Factor 2: Battery risk (lower battery = higher risk)
    merged['battery_risk'] = 1 - merged['battery_level']  # Battery level 0-1
    
    # Factor 3: Demand stress (higher consumption = higher risk)
    merged['demand_stress'] = merged['consumption_kw'] / (battery_capacity * 0.8)
    merged['demand_stress'] = merged['demand_stress'].clip(0, 1)
    
    # Factor 4: Weather severity (rain + cold = less solar efficiency)
    merged['weather_risk'] = 0
    merged.loc[merged['precipitation'] > 5, 'weather_risk'] += 0.3
    merged.loc[merged['temperature_2m'] < 15, 'weather_risk'] += 0.2
    merged.loc[merged['temperature_2m'] > 30, 'weather_risk'] += 0.1
    merged['weather_risk'] = merged['weather_risk'].clip(0, 1)
    
    # Calculate combined risk score (weighted)
    merged['risk_score'] = (
        0.4 * merged['solar_deficit'] +
        0.3 * merged['battery_risk'] +
        0.2 * merged['demand_stress'] +
        0.1 * merged['weather_risk']
    )
    
    # Round and cap risk score
    merged['risk_score'] = (merged['risk_score'] * 100).round(1)  # Percentage
    merged['risk_score'] = merged['risk_score'].clip(0, 100)
    
    # Determine recommendation
    merged['recommendation'] = 'GREEN (Stay on Solar)'
    merged.loc[merged['risk_score'] > 50, 'recommendation'] = 'YELLOW (Prepare Diesel)'
    merged.loc[merged['risk_score'] > 70, 'recommendation'] = 'RED (Switch to Diesel NOW!)'
    
    # Save to risk data
    risk_records = merged[['timestamp', 'village_id', 'village_name', 
                          'consumption_kw', 'battery_level', 
                          'shortwave_radiation', 'temperature_2m', 
                          'precipitation', 'risk_score', 'recommendation']].copy()
    
    risk_data.append(risk_records)
    
    # Summary stats
    print(f"  ✅ Generated {len(risk_records)} risk scores")
    print(f"     Avg Risk: {risk_records['risk_score'].mean():.1f}%")
    print(f"     Max Risk: {risk_records['risk_score'].max():.1f}%")
    print(f"     RED Alerts: {len(risk_records[risk_records['risk_score'] > 70])}")
    print(f"     YELLOW Alerts: {len(risk_records[(risk_records['risk_score'] > 50) & (risk_records['risk_score'] <= 70)])}")

# Combine all risk data
final_risk_df = pd.concat(risk_data, ignore_index=True)

# Save risk data
filename = f"data/processed/risk_scores_{datetime.now().strftime('%Y%m%d_%H%M')}.parquet"
final_risk_df.to_parquet(filename, index=False)

# Also save as CSV for easy viewing
csv_filename = f"reports/risk_report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
final_risk_df.to_csv(csv_filename, index=False)

print("\n" + "=" * 60)
print("RISK ENGINE COMPLETE!")
print("=" * 60)
print(f"Total risk records: {len(final_risk_df)}")
print(f"Saved to: {filename}")
print(f"CSV report: {csv_filename}")

# Show high-risk summary
print("\n" + "=" * 60)
print("HIGH RISK SUMMARY (Risk > 70%)")
print("=" * 60)
high_risk = final_risk_df[final_risk_df['risk_score'] > 70]
if not high_risk.empty:
    print(high_risk[['village_name', 'timestamp', 'risk_score', 'recommendation']].head(10))
else:
    print("✅ No high-risk events detected!")

# Show recent recommendations
print("\n" + "=" * 60)
print("RECENT RECOMMENDATIONS (Last 24 hours)")
print("=" * 60)
recent = final_risk_df[final_risk_df['timestamp'] > (datetime.now() - timedelta(hours=24))]
if not recent.empty:
    print(recent[['village_name', 'timestamp', 'risk_score', 'recommendation']].head(20))
else:
    print("No recent data")