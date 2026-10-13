# Step 15.4 - Combined flight evidence classifier

from pathlib import Path
import math

import pandas as pd

VOBL_LAT = 13.1986
VOBL_LON = 77.7066

EARTH_RADIUS_NM = 3440.065

ADSB_DIR = Path("data/raw/adsb")
RUNWAYS_FILE = Path("data/external/ourairports/runways.csv")


# Convert latitude and longitude to local nautical-mile coordinates
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


# Calculate distance from a point to a runway segment
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


# Calculate distance from VOBL airport
def calculate_distance_nm(lat1, lon1, lat2, lon2):

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

    return EARTH_RADIUS_NM * c


# Calculate distance from aircraft position to runway
def calculate_runway_distance(
    aircraft_lat,
    aircraft_lon,
    runway
):

    aircraft_x, aircraft_y = latlon_to_xy_nm(
        aircraft_lat,
        aircraft_lon
    )

    start_x, start_y = latlon_to_xy_nm(
        runway["le_latitude_deg"],
        runway["le_longitude_deg"]
    )

    end_x, end_y = latlon_to_xy_nm(
        runway["he_latitude_deg"],
        runway["he_longitude_deg"]
    )

    return point_to_segment_distance_nm(
        aircraft_x,
        aircraft_y,
        start_x,
        start_y,
        end_x,
        end_y
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


# Convert data types
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


trajectory = (
    df[df["icao"] == top_icao]
    .sort_values("timestamp_utc")
    .reset_index(drop=True)
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


# Find the candidate runway
runway_distance_results = {}


for _, runway in vobl_runways.iterrows():

    runway_name = (
        str(runway["le_ident"])
        + "/"
        + str(runway["he_ident"])
    )

    distances = []

    for _, aircraft in trajectory.iterrows():

        distance = calculate_runway_distance(
            aircraft["latitude"],
            aircraft["longitude"],
            runway
        )

        distances.append(distance)

    runway_distance_results[
        runway_name
    ] = {
        "runway": runway,
        "distances": distances,
        "minimum_distance": min(distances)
    }


# Select runway with closest approach
candidate_runway_name = min(
    runway_distance_results,
    key=lambda name:
        runway_distance_results[name][
            "minimum_distance"
        ]
)


candidate_result = runway_distance_results[
    candidate_runway_name
]


# Track the same candidate runway
trajectory["runway_distance_nm"] = (
    candidate_result["distances"]
)


# Calculate airport distance
trajectory["airport_distance_nm"] = trajectory.apply(
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


# Runway movement
initial_runway_distance = (
    first_record["runway_distance_nm"]
)

final_runway_distance = (
    last_record["runway_distance_nm"]
)

runway_distance_change = (
    final_runway_distance
    - initial_runway_distance
)


# Airport movement
initial_airport_distance = (
    first_record["airport_distance_nm"]
)

final_airport_distance = (
    last_record["airport_distance_nm"]
)

airport_distance_change = (
    final_airport_distance
    - initial_airport_distance
)


# Altitude movement
initial_altitude = (
    first_record["altitude_baro"]
)

final_altitude = (
    last_record["altitude_baro"]
)

altitude_change = (
    final_altitude
    - initial_altitude
)


# Ground speed movement
valid_speeds = trajectory[
    "ground_speed"
].dropna()


if len(valid_speeds) >= 2:

    initial_speed = valid_speeds.iloc[0]
    final_speed = valid_speeds.iloc[-1]

    speed_change = (
        final_speed
        - initial_speed
    )

else:

    speed_change = float("nan")


# Average vertical rate
average_vertical_rate = (
    trajectory["vertical_rate"]
    .dropna()
    .mean()
)


# Find closest approach to candidate runway
minimum_runway_distance = (
    trajectory["runway_distance_nm"]
    .min()
)


closest_position = (
    trajectory["runway_distance_nm"]
    .idxmin()
)


if len(trajectory) > 1:

    closest_progress = (
        closest_position
        / (len(trajectory) - 1)
    )

else:

    closest_progress = 0


# Classify horizontal state
if airport_distance_change > 1.0:

    horizontal_state = "OUTBOUND"

elif airport_distance_change < -1.0:

    horizontal_state = "INBOUND"

else:

    horizontal_state = "STABLE"


# Classify vertical state
if altitude_change > 500:

    vertical_state = "CLIMBING"

elif altitude_change < -500:

    vertical_state = "DESCENDING"

else:

    vertical_state = "LEVEL"


# Classify runway movement
if runway_distance_change > 1.0:

    runway_state = "MOVING_AWAY"

elif runway_distance_change < -1.0:

    runway_state = "MOVING_TOWARD"

else:

    runway_state = "STABLE"


# Calculate departure evidence
departure_score = 0


if minimum_runway_distance <= 1.5:
    departure_score += 1


if closest_progress <= 0.35:
    departure_score += 1


if runway_state == "MOVING_AWAY":
    departure_score += 1


if horizontal_state == "OUTBOUND":
    departure_score += 1


if vertical_state == "CLIMBING":
    departure_score += 1


if (
    not pd.isna(average_vertical_rate)
    and average_vertical_rate > 300
):
    departure_score += 1


if (
    not pd.isna(speed_change)
    and speed_change > 20
):
    departure_score += 1


# Calculate arrival evidence
arrival_score = 0


if minimum_runway_distance <= 1.5:
    arrival_score += 1


if closest_progress >= 0.65:
    arrival_score += 1


if runway_state == "MOVING_TOWARD":
    arrival_score += 1


if horizontal_state == "INBOUND":
    arrival_score += 1


if vertical_state == "DESCENDING":
    arrival_score += 1


if (
    not pd.isna(average_vertical_rate)
    and average_vertical_rate < -300
):
    arrival_score += 1


if (
    not pd.isna(speed_change)
    and speed_change < -20
):
    arrival_score += 1


# Final pattern classification
if (
    departure_score >= 5
    and departure_score > arrival_score
):

    flight_pattern = "DEPARTURE_LIKE"

elif (
    arrival_score >= 5
    and arrival_score > departure_score
):

    flight_pattern = "ARRIVAL_LIKE"

elif (
    horizontal_state == "OUTBOUND"
    and vertical_state == "CLIMBING"
):

    flight_pattern = "OUTBOUND_CLIMB"

elif (
    horizontal_state == "INBOUND"
    and vertical_state == "DESCENDING"
):

    flight_pattern = "INBOUND_DESCENT"

else:

    flight_pattern = "UNCLASSIFIED"


# Display results
print()

print("Butterflyts flight evidence analysis")

print("ICAO:", top_icao)
print("Flight:", flight_name)

print()

print("Candidate runway:", candidate_runway_name)

print(
    "Minimum runway distance:",
    round(minimum_runway_distance, 2),
    "NM"
)

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
    round(runway_distance_change, 2),
    "NM"
)

print()

print(
    "Initial airport distance:",
    round(initial_airport_distance, 2),
    "NM"
)

print(
    "Final airport distance:",
    round(final_airport_distance, 2),
    "NM"
)

print(
    "Airport distance change:",
    round(airport_distance_change, 2),
    "NM"
)

print()

print(
    "Altitude change:",
    round(altitude_change, 2),
    "ft"
)

print(
    "Speed change:",
    round(speed_change, 2),
    "knots"
)

print(
    "Average vertical rate:",
    round(average_vertical_rate, 2),
    "ft/min"
)

print()

print(
    "Horizontal state:",
    horizontal_state
)

print(
    "Vertical state:",
    vertical_state
)

print(
    "Runway state:",
    runway_state
)

print()

print(
    "Departure evidence score:",
    departure_score,
    "/ 7"
)

print(
    "Arrival evidence score:",
    arrival_score,
    "/ 7"
)

print()

print(
    "Flight pattern:",
    flight_pattern
)