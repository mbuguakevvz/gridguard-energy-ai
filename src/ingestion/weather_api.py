# src/ingestion/weather_api.py
import requests
import json
from datetime import datetime

print("Weather ingestion module")
print("Testing API connection...")

try:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": -1.286,
        "longitude": 36.817,
        "hourly": "temperature_2m",
        "forecast_days": 1
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        print("API connection successful!")
        data = response.json()
        print(f"Data received: {len(data)} keys")
    else:
        print(f"API error: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")