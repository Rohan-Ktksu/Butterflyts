#Determine whether aircraft are moving toward VOBL
import math
import requests
import pandas as pd
#VOBL / Bengaluru Airport
VOBL_LAT = 13.1986
VOBL_LON = 77.7066

RADIUS_NM = 25

#calculate distance

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

#calculate bearing
def calculate_bearing(lat1, lon1, lat2, lon2):
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    delta_lon = math.radians(lon2 - lon1)

    x = math.sin(delta_lon) * math.cos(lat2)

    y = (
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1)
        * math.cos(lat2)
        * math.cos(delta_lon)
    )

    bearing = math.degrees(math.atan2(x, y))

    return (bearing + 360) % 360
#calculate smallest difference between two headigns

def heading_difference(angle1, angle2):
    difference = abs(angle1 - angle2)

    if difference > 180:
        difference = 360 - difference
    return difference
#classify aircraft movement

def classify_movement(track, bearing_to_airport):
    if track is None or pd.isna(track):
        return "UNKNOWN", None
    difference = heading_difference(track, bearing_to_airport)
    if difference <= 45:
        movement = "TOWARD"
    elif difference >= 135:
        movement = "AWAY"
    else:
        movement = "CROSSING"
    return movement, difference
#get live ads-b data
URL = (
    f"https://api.adsb.lol/v2/lat/{VOBL_LAT}"
    f"/lon/{VOBL_LON}"
    f"/dist/{RADIUS_NM}"
)

print("Butterflyts - Aircraft Movement Direction")
print("Requesting live aircraft...")

response = requests.get(URL, timeout=30)

print("HTTP Status:", response.status_code)

response.raise_for_status()

data = response.json()

aircraft = data.get("ac", [])

print("Aircraft received:", len(aircraft))

#process aircraft
records = []

for plane in aircraft:

    lat = plane.get("lat")
    lon = plane.get("lon")

    if lat is None or lon is None:
        continue

    distance_nm = calculate_distance_nm(
        VOBL_LAT,
        VOBL_LON,
        lat,
        lon
    )

    # Direction FROM airport TO aircraft
    bearing_from_airport = calculate_bearing(
        VOBL_LAT,
        VOBL_LON,
        lat,
        lon
    )

    # Direction FROM aircraft TO airport
    bearing_to_airport = calculate_bearing(
        lat,
        lon,
        VOBL_LAT,
        VOBL_LON
    )

    track = plane.get("track")

    movement, difference = classify_movement(
        track,
        bearing_to_airport
    )

    records.append({
        "icao": plane.get("hex"),
        "flight": plane.get("flight"),
        "latitude": lat,
        "longitude": lon,
        "altitude": plane.get("alt_baro"),
        "speed": plane.get("gs"),
        "track": track,
        "vertical_rate": plane.get("baro_rate"),
        "distance_nm": round(distance_nm, 2),
        "bearing_from_airport": round(bearing_from_airport, 1),
        "bearing_to_airport": round(bearing_to_airport, 1),
        "heading_difference": (
            round(difference, 1)
            if difference is not None
            else None
        ),
        "movement": movement,
    })


df = pd.DataFrame(records)

if not df.empty:
    df = df.sort_values("distance_nm")
#Display results

print("\nAircraft movement around VOBL")
print("-----------------------------")

for _, plane in df.iterrows():

    flight = plane["flight"]

    if pd.isna(flight) or not str(flight).strip():
        flight = plane["icao"]
    else:
        flight = str(flight).strip()

    print()
    print("Flight:", flight)
    print("Distance:", plane["distance_nm"], "NM")
    print(
        "Bearing to airport:",
        plane["bearing_to_airport"],
        "degrees"
    )
    print("Track:", plane["track"])
    print(
        "Heading difference:",
        plane["heading_difference"]
    )
    print("Movement:", plane["movement"])
    print("Altitude:", plane["altitude"])
    print(
        "Vertical rate:",
        plane["vertical_rate"]
    )