#step 9: Aircraft Distance and Bearing from VOBL
import math
import requests
import pandas as pd

#VOBL / Bengaluru Airport
VOBL_LAT = 13.1986
VOBL_LON = 77.7066

RADIUS_NM = 25

#Calculate distance betwween two coordinates
#Haversine formula

def calculate_distance_nm(lat1, lon1, lat2, lon2):
    #Earth radius in nautical miles
    earth_radius_nm = 3440.065
    #convert degrees to radians
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)
    #Difference between coordinates
    delta_lat = lat2-lat1
    delta_lon = lon2-lon1
    #Haversine formula
    a = (math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2)*math.sin(delta_lon/2)**2)
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance_nm = earth_radius_nm*c

    return distance_nm
#calculate bearing from point 1 to point 2
def calculate_bearing(lat1, lon1, lat2, lon2):
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)

    x = math.sin(delta_lon)* math.cos(lat2)

    y = (math.cos(lat1)*math.sin(lat2) - math.sin(lat1)*math.cos(lat2)*math.cos(delta_lon))

    bearing = math.degrees(math.atan2(x, y))
    #convert negative agles to 0-360 degrees
    bearing = (bearing+360) % 360

    return bearing
#Get Live ADS-B aircraft
URL = (
    f"https://api.adsb.lol/v2/lat/{VOBL_LAT}"
    f"/lon/{VOBL_LON}"
    f"/dist/{RADIUS_NM}"
)

print("Butterflyts - Aircraft Distance and Bearing")
print("Requesting live aircraft...")

response = requests.get(URL, timeout=30)

print("HTTP Status:", response.status_code)

response.raise_for_status()

data = response.json()

aircraft = data.get("ac", [])

print("Aircraft received:", len(aircraft))

#Process aircraft

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

    bearing = calculate_bearing(
            VOBL_LAT,
            VOBL_LON,
            lat,
            lon
        )

    records.append({
            "icao": plane.get("hex"),
            "flight": plane.get("flight"),
            "latitude": lat,
            "longitude": lon,
            "altitude": plane.get("alt_baro"),
            "speed": plane.get("gs"),
            "track": plane.get("track"),
            "vertical_rate": plane.get("baro_rate"),
            "distance_nm": round(distance_nm, 2),
            "bearing": round(bearing, 1),
        })
df = pd.DataFrame(records)

#sort nearest aircraft first

if not df.empty:
    df = df.sort_values("distance_nm")
#display aircraft
print("\nAircraft around VOBL")
print("--------------------")

for _, plane in df.iterrows():

    flight = plane["flight"]

    if pd.isna(flight) or not str(flight).strip():
        flight = plane["icao"]
    else:
        flight = str(flight).strip()

    print()
    print("Flight:", flight)
    print("Distance:", plane["distance_nm"], "NM")
    print("Bearing:", plane["bearing"], "degrees")
    print("Altitude:", plane["altitude"])
    print("Track:", plane["track"])
    print("Vertical rate:", plane["vertical_rate"])