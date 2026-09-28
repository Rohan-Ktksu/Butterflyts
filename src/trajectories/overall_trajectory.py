from pathlib import Path
import math

import pandas as pd
#Bengaluru Airport coordinates
VOBL_LAT = 13.1986
VOBL_LON = 77.7066
DATA_DIR = Path("data/raw/adsb")
#calculate distance between two coordinates in nautical miles

def calculate_distance_nm(lat1, lon1, lat2, lon2):
    earth_radius_nm = 3440.065
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    a = (
        math.sin(delta_lat/2) **2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon/2) **2
    )
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return earth_radius_nm*c;
#Fnd collected adsb-b files
files = list(DATA_DIR.glob("vobl_adsb_*.parquet"))

if not files:
    print("No ADS-B Parquet files found.")
    raise SystemExit

#select the newest file
latest_file = max(files, key=lambda file: file.stat().st_mtime)
print("Reading:", latest_file)

#Read the dataset
df = pd.read_parquet(latest_file)

#keep airborne observations with valid aircraft identifiers
df = df[(df["on_ground"] == False) & df["icao"].notna()].copy()

if df.empty:
    print("No airborne observations found")
    raise SystemExit
print("Reading:", latest_file)

#convert timestampts and altitude into subtle data types
df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc = True)
df["altitude_baro"] = pd.to_numeric(df["altitude_baro"], errors = "coerce")
#Sort observations by aircraft and time
df = df.sort_values(["icao", "timestamp_utc"])
#calculate distance from VOBL for every observation
df["distance_nm"] = df.apply(lambda row: calculate_distance_nm(VOBL_LAT, VOBL_LON, row["latitude"], row["longitude"]), axis = 1)
#count observation for each aircraft
aircraft_counts = (df.groupby("icao").size().sort_values(ascending=False))
#Select the aircraft with the most observations
top_icao = aircraft_counts.index[0]

trajectory= (df[df["icao"] == top_icao].sort_values("timestamp_utc"))
#check whether enough observations exist
if len(trajectory) < 2:
    print("At least two observations are required:")
    raise SystemExit
#Get the first and last observations
first_record = trajectory.iloc[0]
last_record = trajectory.iloc[-1]
#calculate net distance change
initial_distance = first_record["distance_nm"]
final_distance = last_record["distance_nm"]
total_distance_change = final_distance - initial_distance

#calculate net altitude change using valid altitude observations
valid_altitudes = trajectory["altitude_baro"].dropna()
if len(valid_altitudes)>=2:
    initial_altitude = valid_altitudes.iloc[0]
    final_altitude = valid_altitudes.iloc[-1]
    total_altitude_change = final_altitude - initial_altitude
else:
    total_altitude_change = float("nan")
#calculate the duration of the recorded trajectory
total_duration = (last_record["timestamp_utc"] - first_record["timestamp_utc"]).total_seconds()
# Classify overall horizontal movement
if total_distance_change > 0.5:
    overall_movement = "AWAY"
elif total_distance_change < -0.5:
    overall_movement = "TOWARD"
else:
    overall_movement = "STABLE"
# Classify overall altitude trend
if pd.isna(total_altitude_change):
    altitude_trend = "UNKNOWN"
elif total_altitude_change > 200:
    altitude_trend = "CLIMBING"
elif total_altitude_change < -200:
    altitude_trend = "DESCENDING"
else:
    altitude_trend = "LEVEL"
# Display the overall trajectory summary
print()
print("Overall trajectory summary")

print("ICAO:", top_icao)
print("Observations:", len(trajectory))

print("Initial distance:", round(initial_distance, 2), "NM")
print("Final distance:", round(final_distance, 2), "NM")
print("Distance change:", round(total_distance_change, 2), "NM")

print("Altitude change:", round(total_altitude_change, 2), "ft")
print("Duration:", round(total_duration, 2), "seconds")

print("Overall movement:", overall_movement)
print("Altitude trend:", altitude_trend)