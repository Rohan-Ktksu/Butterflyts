# Step 11 - Inspect collected ADS-B trajectory data

from pathlib import Path
import pandas as pd

# Data directory
DATA_DIR = Path("data/raw/adsb")

# Find all collected Parquet files
files = list(DATA_DIR.glob("vobl_adsb_*.parquet"))

if not files:
    print("No ADS-B Parquet files found.")
    raise SystemExit

# Use most recently created file
latest_file = max(
    files,
    key=lambda file: file.stat().st_mtime
)

print("Reading:", latest_file)

# Read Parquet file
df = pd.read_parquet(latest_file)

# Dataset information
print()
print("Dataset information")

print("Observations:", len(df))
print("Unique aircraft:", df["icao"].nunique())
print("Columns:", list(df.columns))

# Count observations for every aircraft
aircraft_counts = (
    df.groupby(["icao", "flight"], dropna=False)
    .size()
    .reset_index(name="observations")
    .sort_values("observations", ascending=False)
)

print()
print("Observations per aircraft")

print(
    aircraft_counts.to_string(index=False)
)

# Keep only airborne aircraft
airborne_df = df[df["on_ground"] == False]

print()
print("Airborne dataset")

print("Airborne observations:", len(airborne_df))
print(
    "Unique airborne aircraft:",
    airborne_df["icao"].nunique()
)

# Count airborne observations for each aircraft
airborne_counts = (
    airborne_df.groupby(["icao", "flight"], dropna=False)
    .size()
    .reset_index(name="observations")
    .sort_values("observations", ascending=False)
)

print()
print("Airborne observations per aircraft")

print(
    airborne_counts.to_string(index=False)
)

# Check if airborne aircraft exist
if airborne_counts.empty:
    print()
    print("No airborne aircraft found.")
    raise SystemExit

# Select aircraft with most airborne observations
top_icao = airborne_counts.iloc[0]["icao"]

print()
print("Selected aircraft")
print("ICAO:", top_icao)

# Get trajectory for selected aircraft
trajectory = (
    airborne_df[airborne_df["icao"] == top_icao]
    .sort_values("timestamp_utc")
)

# Columns to display
columns = [
    "timestamp_utc",
    "icao",
    "flight",
    "latitude",
    "longitude",
    "altitude_baro",
    "on_ground",
    "ground_speed",
    "track",
    "vertical_rate",
]

# Display trajectory
print()
print("Example airborne trajectory")

print(
    trajectory[columns].to_string(index=False)
)