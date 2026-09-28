# Step 12 - Calculate aircraft trajectory features

from pathlib import Path
import math

import pandas as pd


VOBL_LAT = 13.1986
VOBL_LON = 77.7066

DATA_DIR = Path("data/raw/adsb")


# Calculate distance between two coordinates in nautical miles
def calculate_distance_nm(lat1, lon1, lat2, lon2):

    earth_radius_nm = 3440.065

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return earth_radius_nm * c


# Find collected ADS-B files
files = list(
    DATA_DIR.glob("vobl_adsb_*.parquet")
)

if not files:
    print("No ADS-B Parquet files found.")
    raise SystemExit


# Select newest file
latest_file = max(
    files,
    key=lambda file: file.stat().st_mtime
)

print("Reading:", latest_file)


# Read trajectory data
df = pd.read_parquet(latest_file)


# Keep airborne observations
df = df[df["on_ground"] == False].copy()


# Sort observations by aircraft and time
df = df.sort_values(
    ["icao", "timestamp_utc"]
)


# Calculate distance from VOBL
df["distance_nm"] = df.apply(
    lambda row: calculate_distance_nm(
        VOBL_LAT,
        VOBL_LON,
        row["latitude"],
        row["longitude"]
    ),
    axis=1
)


# Get previous distance for each aircraft
df["previous_distance_nm"] = (
    df.groupby("icao")["distance_nm"]
    .shift(1)
)


# Calculate distance change
df["distance_change_nm"] = (
    df["distance_nm"]
    - df["previous_distance_nm"]
)


# Get previous altitude
df["previous_altitude_ft"] = (
    df.groupby("icao")["altitude_baro"]
    .shift(1)
)


# Calculate altitude change
df["altitude_change_ft"] = (
    df["altitude_baro"]
    - df["previous_altitude_ft"]
)


# Get previous timestamp
df["previous_timestamp"] = (
    df.groupby("icao")["timestamp_utc"]
    .shift(1)
)


# Calculate elapsed time
df["elapsed_seconds"] = (
    df["timestamp_utc"]
    - df["previous_timestamp"]
).dt.total_seconds()


# Classify distance trend
def classify_distance_trend(change):

    if pd.isna(change):
        return "UNKNOWN"

    if change < -0.05:
        return "TOWARD"

    if change > 0.05:
        return "AWAY"

    return "STABLE"


df["movement_trend"] = (
    df["distance_change_nm"]
    .apply(classify_distance_trend)
)


# Select aircraft with most observations
top_icao = (
    df.groupby("icao")
    .size()
    .sort_values(ascending=False)
    .index[0]
)


trajectory = (
    df[df["icao"] == top_icao]
    .sort_values("timestamp_utc")
)


# Display calculated trajectory features
columns = [
    "timestamp_utc",
    "icao",
    "flight",
    "distance_nm",
    "distance_change_nm",
    "altitude_baro",
    "altitude_change_ft",
    "elapsed_seconds",
    "ground_speed",
    "track",
    "vertical_rate",
    "movement_trend",
]


print()
print("Trajectory feature analysis")
print("ICAO:", top_icao)

print(
    trajectory[columns].to_string(
        index=False
    )
)