# AeroPulse
# Verify Bengaluru Airport in OurAirports

import pandas as pd

AIRPORT_FILE = "data/external/ourairports/airports.csv"

df = pd.read_csv(AIRPORT_FILE)
vobl = df[df["ident"] == "VOBL"]

if vobl.empty:
    print("ERROR: VOBL not found.")
else:
    print("\n VOBL Airport Record")
    columns = ["ident", "name", "latitude_deg", "longitude_deg", "elevation_ft", "municipality"]
    print(vobl[columns].to_string(index=False))
    