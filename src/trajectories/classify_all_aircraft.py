# Step 16.1 - Classify all aircraft trajectories

from pathlib import Path
import math

import pandas as pd

VOBL_LAT = 13.1986
VOBL_LON = 77.7066

EARTH_RADIUS_NM = 3440.065

ADSB_DIR = Path("data/raw/adsb")
RUNWAYS_FILE = Path("data/external/ourairports/runways.csv")
MIN_OBSERVATIONS = 5

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


# Calculate distance between two geographic coordinates
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


# Calculate aircraft distance from a runway
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


# Select newest ADS-B file
latest_file = max(
    files,
    key=lambda file: file.stat().st_mtime
)

if __name__ == "__main__":
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
    subset=["timestamp_utc"]
)


if df.empty:

    print("No valid airborne observations found.")
    raise SystemExit


# Store classification results
results = []


# Analyze every aircraft
for icao, trajectory in df.groupby("icao"):

    trajectory = (
        trajectory
        .sort_values("timestamp_utc")
        .reset_index(drop=True)
    )

    observation_count = len(trajectory)

    # Get flight number
    flight_values = (
        trajectory["flight"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    flight_values = flight_values[
        flight_values != ""
    ]

    if flight_values.empty:
        flight_name = "UNKNOWN"
    else:
        flight_name = flight_values.iloc[0]


    # Handle aircraft with insufficient observations
    if observation_count < MIN_OBSERVATIONS:

        results.append(
            {
                "icao": icao,
                "flight": flight_name,
                "observations": observation_count,
                "candidate_runway": "UNKNOWN",
                "minimum_runway_nm": float("nan"),
                "runway_associated": False,
                "airport_change_nm": float("nan"),
                "altitude_change_ft": float("nan"),
                "speed_change_knots": float("nan"),
                "average_vertical_rate": float("nan"),
                "departure_score": 0,
                "arrival_score": 0,
                "pattern": "INSUFFICIENT_DATA"
            }
        )

        continue


    # Find candidate runway
    runway_results = {}


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


        runway_results[
            runway_name
        ] = {
            "distances": distances,
            "minimum_distance": min(distances)
        }


    candidate_runway_name = min(
        runway_results,
        key=lambda name:
            runway_results[name][
                "minimum_distance"
            ]
    )


    candidate_result = runway_results[
        candidate_runway_name
    ]


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


    # Calculate runway movement
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


    minimum_runway_distance = (
        trajectory["runway_distance_nm"].min()
    )


    closest_position = (
        trajectory["runway_distance_nm"].idxmin()
    )


    closest_progress = (
        closest_position
        / (observation_count - 1)
    )


    # Calculate airport movement
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


    # Calculate altitude change
    valid_altitudes = (
        trajectory["altitude_baro"]
        .dropna()
    )


    if len(valid_altitudes) >= 2:

        altitude_change = (
            valid_altitudes.iloc[-1]
            - valid_altitudes.iloc[0]
        )

    else:

        altitude_change = float("nan")


    # Calculate ground speed change
    valid_speeds = (
        trajectory["ground_speed"]
        .dropna()
    )


    if len(valid_speeds) >= 2:

        speed_change = (
            valid_speeds.iloc[-1]
            - valid_speeds.iloc[0]
        )

    else:

        speed_change = float("nan")


    # Calculate average vertical rate
    valid_vertical_rates = (
        trajectory["vertical_rate"]
        .dropna()
    )


    if valid_vertical_rates.empty:

        average_vertical_rate = float("nan")

    else:

        average_vertical_rate = (
            valid_vertical_rates.mean()
        )


    # Classify horizontal movement
    if airport_distance_change > 1.0:

        horizontal_state = "OUTBOUND"

    elif airport_distance_change < -1.0:

        horizontal_state = "INBOUND"

    else:

        horizontal_state = "STABLE"


    # Classify altitude movement
    if pd.isna(altitude_change):

        vertical_state = "UNKNOWN"

    elif altitude_change > 500:

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


    # Departure evidence
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


    # Arrival evidence
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

    # Determine whether trajectory was close enough to a VOBL runway
    runway_associated = (
        minimum_runway_distance <= 3.0
    )
    # Classify flight pattern
    if (
        runway_associated
        and departure_score >= 5
        and departure_score > arrival_score
    ):

        pattern = "DEPARTURE_LIKE"

    elif (
        runway_associated
        and arrival_score >= 5
        and arrival_score > departure_score
    ):

        pattern = "ARRIVAL_LIKE"

    elif (
        horizontal_state == "OUTBOUND"
        and vertical_state == "CLIMBING"
    ):

        pattern = "OUTBOUND_CLIMB"

    elif (
        horizontal_state == "INBOUND"
        and vertical_state == "DESCENDING"
    ):

        pattern = "INBOUND_DESCENT"

    elif (
        horizontal_state == "OUTBOUND"
        and vertical_state == "LEVEL"
    ):

        pattern = "OUTBOUND_LEVEL"

    elif (
        horizontal_state == "INBOUND"
        and vertical_state == "LEVEL"
    ):

        pattern = "INBOUND_LEVEL"

    else:

        pattern = "UNCLASSIFIED"


    # Store aircraft result
    results.append(
        {
            "icao": icao,
            "flight": flight_name,
            "observations": observation_count,
            "candidate_runway": candidate_runway_name,
            "minimum_runway_nm": minimum_runway_distance,
            "runway_associated": runway_associated,
            "airport_change_nm": airport_distance_change,
            "altitude_change_ft": altitude_change,
            "speed_change_knots": speed_change,
            "average_vertical_rate": average_vertical_rate,
            "departure_score": departure_score,
            "arrival_score": arrival_score,
            "pattern": pattern
        }
    )


# Convert results into DataFrame
results_df = pd.DataFrame(results)


# Sort aircraft by number of observations
results_df = results_df.sort_values(
    "observations",
    ascending=False
)


# Round numeric values
numeric_columns = [
    "minimum_runway_nm",
    "airport_change_nm",
    "altitude_change_ft",
    "speed_change_knots",
    "average_vertical_rate"
]


results_df[numeric_columns] = (
    results_df[numeric_columns]
    .round(2)
)


# Display results when this file is run directly
if __name__ == "__main__":

    print()
    print("Butterflyts all-aircraft classification")
    print()

    print(
        results_df.to_string(
            index=False
        )
    )

    print()
    print("Flight pattern summary")

    print(
        results_df["pattern"]
        .value_counts()
        .to_string()
    )