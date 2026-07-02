# src/utils/test_setup.py
import pandas as pd
import polars as pl
import duckdb
import json
import sys

print("All imports successful!")
print(f"Python version: {sys.version}")

try:
    with open("data/villages.json", "r") as f:
        villages = json.load(f)
    print(f"Loaded {len(villages['villages'])} villages")
    print("Setup complete!")
except Exception as e:
    print(f"Error: {e}")