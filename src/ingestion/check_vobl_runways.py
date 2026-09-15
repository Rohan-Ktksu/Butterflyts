# AeroPulse
# Find VOBL runway geometry

import pandas as pd

RUNWAY_FILE = "data/external/ourairports/runways.csv"

df = pd.read_csv(RUNWAY_FILE)

vobl_runways = df[df["airport_ident"]== "VOBL"]

if vobl_runways.empty:
    print("ERROR: No VOBL runways found.")
else:
    print("\n VOBL Runways")
    columns = [ "airport_ident",
        "length_ft",
        "width_ft",
        "surface",
        "le_ident",
        "le_latitude_deg",
        "le_longitude_deg",
        "le_heading_degT",
        "he_ident",
        "he_latitude_deg",
        "he_longitude_deg",
        "he_heading_degT"]
    available_columns = [column for column in columns if column in vobl_runways.columns]

    print(vobl_runways[available_columns].to_string(index=False))