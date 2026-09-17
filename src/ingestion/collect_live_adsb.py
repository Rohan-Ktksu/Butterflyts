#step 11- Collect Live ADS-B Trajectory Data
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

#VOBL/ Bengaluru Airport

VOBL_LAT = 13.1986
VOBL_LON  = 77.7066

RADIUS_NM = 25

#collection settings
INTERVAL_SECONDS = 15
COLLECTION_MINUTES = 5

#Data directory
OUTPUT_DIR = Path("data/raw/adsb")
OUTPUT_DIR.mkdir(parents=True, exist_ok = True)
# ADSB.lol API
URL = (
    f"https://api.adsb.lol/v2/lat/{VOBL_LAT}"
    f"/lon/{VOBL_LON}"
    f"/dist/{RADIUS_NM}"
)


def fetch_aircraft():

    response = requests.get(URL, timeout=30)

    print("HTTP Status:", response.status_code)

    response.raise_for_status()

    data = response.json()

    return data.get("ac", [])


def process_aircraft(aircraft, timestamp):
    records = []
    for plane in aircraft:
        lat = plane.get("lat")
        lon = plane.get("lon")
        if lat is None or lon is None:
            continue
        altitude_baro = plane.get("alt_baro")

        if altitude_baro == "ground":
            on_ground = True
            altitude_baro = None
        else:
            on_ground = False
        records.append({
            "timestamp_utc": timestamp,
            "icao": plane.get("hex"),
            "flight": plane.get("flight"),
            "latitude": lat,
            "longitude": lon,
            "altitude_baro": altitude_baro,
            "on_ground": on_ground,
            "altitude_geom": plane.get("alt_geom"),
            "ground_speed": plane.get("gs"),
            "track": plane.get("track"),
            "vertical_rate": plane.get("baro_rate"),
            "squawk": plane.get("squawk"),
            "category": plane.get("category"),
        })

    return records
print("Butterflyts - Live ADS-B Collector")
print("Airport: VOBL")
print("Radius:", RADIUS_NM, "NM")
print("Interval:", INTERVAL_SECONDS, "seconds")
print("Duration:",  COLLECTION_MINUTES, "minutes")
print()

all_records = []

number_of_cycles = int(COLLECTION_MINUTES * 60 / INTERVAL_SECONDS)
for cycle in range(number_of_cycles):
    time_stamp = datetime.now(timezone.utc)
    print(f"Cycle {cycle +1}/{number_of_cycles}", "-", time_stamp.isoformat())
    try:
        aircraft = fetch_aircraft()
        records = process_aircraft(aircraft, time_stamp)
        all_records.extend(records)
        print("Aircraft:", len(aircraft), "| Valid positions:", len(records))
    except requests.RequestException as error:
            print("ADS-B request failed:", error)
    #Don't wait after the final request
    if cycle < number_of_cycles -1 :
        time.sleep(INTERVAL_SECONDS)
#convert collected observations to DataFRame
df = pd.DataFrame(all_records)
if df.empty:
    print("\nNo aircraft observation collected.")
else:
    #Create unique filename using UTC time
    file_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_file = (OUTPUT_DIR/f"vobl_adsb_{file_timestamp}.parquet")
    df.to_parquet(output_file, index=False)
    print()
    print("Collection complete")
    print("Observations:", len(df))
    print("Unique aircraft:", df["icao"].nunique())
    print("File:", output_file)

