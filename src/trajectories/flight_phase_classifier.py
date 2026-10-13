# Step 15 - Rule-based aircraft flight phase classification

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
files = list(DATA_DIR.glob("vobl_adsb_*.parquet"))

if not files:
    print("No ADS-B Parquet files found.")
    raise SystemExit


# Select newest file
latest_file = max(
    files,
    key=lambda file: file.stat().st_mtime
)

print("Reading:", latest_file)


# Read ADS-B data
df = pd.read_parquet(latest_file)


# Keep airborne aircraft with valid positions
df = df[
    (df["on_ground"] == False)
    & df["icao"].notna()
    & df["latitude"].notna()
    & df["longitude"].notna()
].copy()

if df.empty:
    print("No valid airborne observations found.")
    raise SystemExit


# Convert columns into correct data types
df["timestamp_utc"] = pd.to_datetime(
    df["timestamp_utc"],
    utc=True,
    errors="coerce"
)

df["altitude_baro"] = pd.to_numeric(
    df["altitude_baro"],
    errors="coerce"
)

df["ground_speed"] = pd.to_numeric(
    df["ground_speed"],
    errors="coerce"
)

df["vertical_rate"] = pd.to_numeric(
    df["vertical_rate"],
    errors="coerce"
)


# Remove observations missing important values
df = df.dropna(
    subset=[
        "timestamp_utc",
        "altitude_baro"
    ]
)


# Select aircraft with most observations
aircraft_counts = (
    df.groupby("icao")
    .size()
    .sort_values(ascending=False)
)

top_icao = aircraft_counts.index[0]


# Extract selected aircraft trajectory
trajectory = df[df["icao"] == top_icao].copy()

trajectory = trajectory.sort_values("timestamp_utc")

if len(trajectory) < 2:
    print("At least two observations are required.")
    raise SystemExit


# Get flight number
flight_values = trajectory["flight"].dropna()

if flight_values.empty:
    flight_name = top_icao
else:
    flight_name = str(
        flight_values.iloc[0]
    ).strip()


# Calculate distance from VOBL
trajectory["distance_nm"] = trajectory.apply(
    lambda row: calculate_distance_nm(
        VOBL_LAT,
        VOBL_LON,
        row["latitude"],
        row["longitude"]
    ),
    axis=1
)


# Get first and last observations
first_record = trajectory.iloc[0]
last_record = trajectory.iloc[-1]


# Calculate overall movement
initial_distance = first_record["distance_nm"]
final_distance = last_record["distance_nm"]

distance_change = (
    final_distance
    - initial_distance
)


# Calculate altitude movement
initial_altitude = first_record["altitude_baro"]
final_altitude = last_record["altitude_baro"]

altitude_change = (
    final_altitude
    - initial_altitude
)


# Calculate average ground speed
average_ground_speed = (
    trajectory["ground_speed"]
    .dropna()
    .mean()
)


# Calculate average vertical rate
average_vertical_rate = (
    trajectory["vertical_rate"]
    .dropna()
    .mean()
)


# Classify horizontal movement
if distance_change > 0.5:
    horizontal_state = "OUTBOUND"

elif distance_change < -0.5:
    horizontal_state = "INBOUND"

else:
    horizontal_state = "STABLE"


# Classify altitude movement
if altitude_change > 200:
    vertical_state = "CLIMBING"

elif altitude_change < -200:
    vertical_state = "DESCENDING"

else:
    vertical_state = "LEVEL"


# Combine movement features into flight phase
if (
    horizontal_state == "OUTBOUND"
    and vertical_state == "CLIMBING"
):
    flight_phase = "OUTBOUND_CLIMB"

elif (
    horizontal_state == "INBOUND"
    and vertical_state == "DESCENDING"
):
    flight_phase = "INBOUND_DESCENT"

elif (
    horizontal_state == "OUTBOUND"
    and vertical_state == "LEVEL"
):
    flight_phase = "OUTBOUND_LEVEL"

elif (
    horizontal_state == "INBOUND"
    and vertical_state == "LEVEL"
):
    flight_phase = "INBOUND_LEVEL"

elif vertical_state == "CLIMBING":
    flight_phase = "CLIMBING_MANEUVER"

elif vertical_state == "DESCENDING":
    flight_phase = "DESCENDING_MANEUVER"

else:
    flight_phase = "UNCLASSIFIED"


# Display analysis
print()
print("Butterflyts flight phase analysis")
print("ICAO:", top_icao)
print("Flight:", flight_name)
print("Observations:", len(trajectory))

print()
print("Trajectory evidence")

print(
    "Initial distance:",
    round(initial_distance, 2),
    "NM"
)

print(
    "Final distance:",
    round(final_distance, 2),
    "NM"
)

print(
    "Distance change:",
    round(distance_change, 2),
    "NM"
)

print(
    "Altitude change:",
    round(altitude_change, 2),
    "ft"
)

print(
    "Average ground speed:",
    round(average_ground_speed, 2),
    "knots"
)

print(
    "Average vertical rate:",
    round(average_vertical_rate, 2),
    "ft/min"
)

print()
print("Horizontal state:", horizontal_state)
print("Vertical state:", vertical_state)

print()
print("Flight phase:", flight_phase)