# AeroPulse
# Step 7 - Test Live ADS-B Data Around VOBL

import requests

#kempegowda international airport
VOBL_LAT = 13.1986
VOBL_LON = 77.7066

#Radius in nautical miles
RADIUS_NM = 25

URL = (   f"https://api.adsb.lol/v2/lat/{VOBL_LAT}"
    f"/lon/{VOBL_LON}"
    f"/dist/{RADIUS_NM}")

print("AeroPulse - Live ADS-B Test")
print("Requesting aircragt around VOBL...")

response = requests.get(URL, timeout = 30)

print("HTTP Status", response.status_code)

response.raise_for_status()

data = response.json()

aircraft = data.get("ac", [])

print("Aircraft received:", len(aircraft))

print("\n First 5 aircraft")

for plane in aircraft[:5]:
    print("\nAircraft")

    print("ICAO:", plane.get("hex"))
    print("Flight:", plane.get("flight"))
    print("Latitude:", plane.get("lat"))
    print("Longitude:", plane.get("lon"))
    print("Altitude:", plane.get("alt_baro"))
    print("Ground speed:", plane.get("gs"))
    print("Track:", plane.get("track"))
    print("Vertical rate:", plane.get("baro_rate"))
