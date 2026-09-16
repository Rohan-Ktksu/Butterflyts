# Step 8 - Visualize Live Aircraft Around VOBL

import requests
import pandas as pd
import matplotlib.pyplot as plt

#VOBL/Bengaluru Airport

VOBL_LAT = 13.1986
VOBL_LON = 77.7066
#25 nautical miles
RADIUS_NM = 25

#ADBS.lol API
URL = (
       f"https://api.adsb.lol/v2/lat/{VOBL_LAT}"f"/lon/{VOBL_LON}"f"/dist/{RADIUS_NM}")
print("Butterflyts - Live Aircraft Visualization")
print("Requesting aircraft around VOBL....")

response = requests.get(URL, timeout=30)

print("HTTPS Status:", response.status_code)

response.raise_for_status()

data = response.json()

aircraft = data.get("ac", [])
print("Aircraft received:", len(aircraft))

#convert ADS-B records to DataFrame

records = []

for plane in aircraft:
    lat = plane.get("lat")
    lon = plane.get("lon")
#we cannot plot aircraft without coordinates
    if lat is None or lon is None:
        continue
    records.append({"icao": plane.get("hex"),
            "flight": plane.get("flight"),
            "latitude": lat,
            "longitude": lon,
            "altitude": plane.get("alt_baro"),
            "speed": plane.get("gs"),
            "track": plane.get("track"),
            "vertical_rate": plane.get("baro_rate"),})
df = pd.DataFrame(records)
print("Aircraft with  valid coordinates:", len(df))

if df.empty:
    print("No aircraft with valid coordinates found.")
    raise SystemExit
#create plot
plt.figure(figsize=(10,10))
#plot aircraft
plt.scatter(df["longitude"], df["latitude"], s=40, label="Aircraft")
# ------------------------------------------------------------
# Load and plot VOBL runways
# ------------------------------------------------------------

RUNWAY_FILE = "data/external/ourairports/runways.csv"

runways = pd.read_csv(RUNWAY_FILE)

vobl_runways = runways[
    runways["airport_ident"] == "VOBL"
]

for _, runway in vobl_runways.iterrows():

    # Coordinates of both runway ends
    le_lon = runway["le_longitude_deg"]
    le_lat = runway["le_latitude_deg"]

    he_lon = runway["he_longitude_deg"]
    he_lat = runway["he_latitude_deg"]

    # Draw runway
    plt.plot(
        [le_lon, he_lon],
        [le_lat, he_lat],
        linewidth=4
    )

    # Label low-numbered runway end
    plt.annotate(
        runway["le_ident"],
        (le_lon, le_lat),
        fontsize=8
    )

    # Label high-numbered runway end
    plt.annotate(
        runway["he_ident"],
        (he_lon, he_lat),
        fontsize=8
    )
#plot VOBL aircraft
plt.scatter(VOBL_LON, VOBL_LAT, marker="*", s=250, label="VOBL")

#add aircraft labels

for _, plane in df.iterrows():
    flight = plane["flight"]

    if pd.isna(flight) or not str(flight).strip():
        flight = plane["icao"]
    else:
        flight = str(flight).strip()
    altitude = plane["altitude"]
    label = f"{flight}"
    if altitude is not None:
        label += f"\n{altitude} ft"
    plt.annotate(label, (plane["longitude"], plane["latitude"]), xytext = (5,5), textcoords= "offset points", fontsize = 7)

#plot settings

plt.title("Butterflyts - Live Aircraft Around Bengaluru Airport (VOBL)")

plt.xlabel("Longitude")
plt.ylabel("latitude")

plt.grid(True)
plt.legend()

plt.tight_layout()
plt.show()