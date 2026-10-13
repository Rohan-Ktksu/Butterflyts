# Step 15.2 - Analyze aircraft proximity to VOBL runways

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


# Calculate distance from a point to a runway line segment
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


# Load VOBL runways
if not RUNWAYS_FILE.exists():
    print("Runways file not found:", RUNWAYS_FILE)
    raise SystemExit

runways = pd.read_csv(RUNWAYS_FILE)

vobl_runways = runways[
    runways["airport_ident"] == "VOBL"
].copy()

if vobl_runways.empty:
    print("No VOBL runways found.")
    raise SystemExit


# Keep runways with valid endpoint coordinates
vobl_runways = vobl_runways.dropna(
    subset=[
        "le_latitude_deg",
        "le_longitude_deg",
        "he_latitude_deg",
        "he_longitude_deg"
    ]
)

print("VOBL runways found:")

print(
    vobl_runways[
        [
            "le_ident",
            "he_ident",
            "length_ft",
            "width_ft"
        ]
    ].to_string(index=False)
)


# Find collected ADS-B files
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

print()
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


if trajectory.empty:
    print("No trajectory found.")
    raise SystemExit


# Get flight number
flight_values = trajectory["flight"].dropna()

if flight_values.empty:
    flight_name = top_icao
else:
    flight_name = str(
        flight_values.iloc[0]
    ).strip()


# Analyze first aircraft position
first_record = trajectory.iloc[0]

aircraft_x, aircraft_y = latlon_to_xy_nm(
    first_record["latitude"],
    first_record["longitude"]
)


runway_results = []


# Calculate distance to each runway
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

    runway_results.append(
        {
            "runway": runway_name,
            "distance_nm": distance
        }
    )


# Convert results to DataFrame
runway_distance_df = pd.DataFrame(
    runway_results
)

runway_distance_df = runway_distance_df.sort_values(
    "distance_nm"
)


# Find nearest runway
nearest_runway = runway_distance_df.iloc[0]

nearest_runway_name = nearest_runway["runway"]
nearest_runway_distance = nearest_runway["distance_nm"]


# Classify runway proximity
if nearest_runway_distance <= 0.5:
    runway_proximity = "VERY_CLOSE"

elif nearest_runway_distance <= 1.5:
    runway_proximity = "NEAR"

elif nearest_runway_distance <= 3.0:
    runway_proximity = "MODERATE"

else:
    runway_proximity = "FAR"


# Display results
print()
print("Runway proximity analysis")

print("ICAO:", top_icao)
print("Flight:", flight_name)

print(
    "First observation:",
    first_record["timestamp_utc"]
)

print(
    "Aircraft latitude:",
    round(first_record["latitude"], 6)
)

print(
    "Aircraft longitude:",
    round(first_record["longitude"], 6)
)

print()

print(
    runway_distance_df.to_string(
        index=False,
        formatters={
            "distance_nm": lambda value: f"{value:.2f}"
        }
    )
)

print()

print(
    "Nearest runway:",
    nearest_runway_name
)

print(
    "Distance to runway:",
    round(nearest_runway_distance, 2),
    "NM"
)

print(
    "Runway proximity:",
    runway_proximity
)