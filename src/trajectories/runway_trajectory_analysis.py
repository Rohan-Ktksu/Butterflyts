# Step 15.3 - Analyze runway distance across aircraft trajectory

from pathlib import Path
import math

import pandas as pd

VOBL_LAT = 13.1986
VOBL_LON = 77.7066

EARTH_RADIUS_NM = 3440.065

ADSB_DIR = Path("data/raw/adsb")
RUNWAYS_FILE = Path("data/external/ourairports/runways.csv")


# Convert latitude and longitude into local nautical-mile coordinates
def latlon_to_xy_nm(lat, lon):

    lat0 = math.radians(VOBL_LAT)

    x = (
        math.radians(lon - VOBL_LON)
        * math.cos(lat0)
        * EARTH_RADIUS_NM
    )

    y = (
        math.radians(lat - VOBL_LAT)
        * EARTH_RADIUS_NM
    )

    return x, y


# Calculate shortest distance from a point to a runway segment
def point_to_segment_distance_nm(
    point_x,
    point_y,
    start_x,
    start_y,
    end_x,
    end_y
):

    segment_x = end_x - start_x
    segment_y = end_y - start_y

    point_x_offset = point_x - start_x
    point_y_offset = point_y - start_y

    segment_length_squared = (
        segment_x ** 2
        + segment_y ** 2
    )

    if segment_length_squared == 0:

        return math.sqrt(
            point_x_offset ** 2
            + point_y_offset ** 2
        )

    projection = (
        point_x_offset * segment_x
        + point_y_offset * segment_y
    ) / segment_length_squared

    projection = max(
        0,
        min(1, projection)
    )

    closest_x = (
        start_x
        + projection * segment_x
    )

    closest_y = (
        start_y
        + projection * segment_y
    )

    distance_x = point_x - closest_x
    distance_y = point_y - closest_y

    return math.sqrt(
        distance_x ** 2
        + distance_y ** 2
    )


# Load runway data
if not RUNWAYS_FILE.exists():

    print("Runways file not found:", RUNWAYS_FILE)
    raise SystemExit


runways = pd.read_csv(RUNWAYS_FILE)


vobl_runways = runways[
    runways["airport_ident"] == "VOBL"
].copy()


vobl_runways = vobl_runways.dropna(
    subset=[
        "le_latitude_deg",
        "le_longitude_deg",
        "he_latitude_deg",
        "he_longitude_deg"
    ]
)


if vobl_runways.empty:

    print("No valid VOBL runways found.")
    raise SystemExit


# Find ADS-B files
files = list(
    ADSB_DIR.glob("vobl_adsb_*.parquet")
)


if not files:

    print("No ADS-B Parquet files found.")
    raise SystemExit


# Select newest ADS-B file
latest_file = max(
    files,
    key=lambda file: file.stat().st_mtime
)


print("Reading:", latest_file)


# Read ADS-B data
df = pd.read_parquet(latest_file)


# Keep valid airborne observations
df = df[
    (df["on_ground"] == False)
    & df["icao"].notna()
    & df["latitude"].notna()
    & df["longitude"].notna()
].copy()


df["timestamp_utc"] = pd.to_datetime(
    df["timestamp_utc"],
    utc=True,
    errors="coerce"
)


df = df.dropna(
    subset=["timestamp_utc"]
)


# Select aircraft with most observations
aircraft_counts = (
    df.groupby("icao")
    .size()
    .sort_values(ascending=False)
)


top_icao = aircraft_counts.index[0]


trajectory = (
    df[df["icao"] == top_icao]
    .sort_values("timestamp_utc")
    .copy()
)


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


# Calculate nearest runway distance for each observation
nearest_runways = []
nearest_distances = []


for _, aircraft in trajectory.iterrows():

    aircraft_x, aircraft_y = latlon_to_xy_nm(
        aircraft["latitude"],
        aircraft["longitude"]
    )

    observation_results = []

    for _, runway in vobl_runways.iterrows():

        start_x, start_y = latlon_to_xy_nm(
            runway["le_latitude_deg"],
            runway["le_longitude_deg"]
        )

        end_x, end_y = latlon_to_xy_nm(
            runway["he_latitude_deg"],
            runway["he_longitude_deg"]
        )

        distance = point_to_segment_distance_nm(
            aircraft_x,
            aircraft_y,
            start_x,
            start_y,
            end_x,
            end_y
        )

        runway_name = (
            str(runway["le_ident"])
            + "/"
            + str(runway["he_ident"])
        )

        observation_results.append(
            (
                runway_name,
                distance
            )
        )

    nearest = min(
        observation_results,
        key=lambda item: item[1]
    )

    nearest_runways.append(
        nearest[0]
    )

    nearest_distances.append(
        nearest[1]
    )


# Store runway results
trajectory["nearest_runway"] = nearest_runways

trajectory["runway_distance_nm"] = nearest_distances


# Calculate runway distance change
trajectory["previous_runway_distance_nm"] = (
    trajectory["runway_distance_nm"]
    .shift(1)
)


trajectory["runway_distance_change_nm"] = (
    trajectory["runway_distance_nm"]
    - trajectory["previous_runway_distance_nm"]
)


# Get first and last runway distances
first_record = trajectory.iloc[0]
last_record = trajectory.iloc[-1]


initial_runway_distance = (
    first_record["runway_distance_nm"]
)


final_runway_distance = (
    last_record["runway_distance_nm"]
)


total_runway_distance_change = (
    final_runway_distance
    - initial_runway_distance
)


# Classify overall runway movement
if total_runway_distance_change > 1.0:

    runway_movement = "MOVING_AWAY"

elif total_runway_distance_change < -1.0:

    runway_movement = "MOVING_TOWARD"

else:

    runway_movement = "STABLE"


# Display trajectory details
columns = [
    "timestamp_utc",
    "icao",
    "flight",
    "nearest_runway",
    "runway_distance_nm",
    "runway_distance_change_nm"
]


print()

print("Runway trajectory analysis")

print(
    trajectory[columns]
    .to_string(index=False)
)


# Display overall runway summary
print()

print("Overall runway movement")

print("ICAO:", top_icao)

print("Flight:", flight_name)

print(
    "Initial runway distance:",
    round(initial_runway_distance, 2),
    "NM"
)

print(
    "Final runway distance:",
    round(final_runway_distance, 2),
    "NM"
)

print(
    "Runway distance change:",
    round(total_runway_distance_change, 2),
    "NM"
)

print(
    "Runway movement:",
    runway_movement
)