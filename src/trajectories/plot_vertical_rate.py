# Step 14.2 - Compare ADS-B vertical rate with calculated climb rate

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

DATA_DIR = Path("data/raw/adsb")

# Find collected ADS-B files
files = list(DATA_DIR.glob("vobl_adsb_*.parquet"))

if not files:
    print("No ADS-B Parquet files found.")
    raise SystemExit

# Select newest file
latest_file = max(
    files,
    key=lambda file: file.stat().st_mtime
)

print("Reading:", latest_file)

# Read ADS-B data
df = pd.read_parquet(latest_file)

# Keep airborne observations with valid ICAO identifiers
df = df[
    (df["on_ground"] == False)
    & df["icao"].notna()
].copy()

if df.empty:
    print("No airborne observations found.")
    raise SystemExit

# Convert values into correct data types
df["timestamp_utc"] = pd.to_datetime(
    df["timestamp_utc"],
    utc=True,
    errors="coerce"
)

df["altitude_baro"] = pd.to_numeric(
    df["altitude_baro"],
    errors="coerce"
)

df["vertical_rate"] = pd.to_numeric(
    df["vertical_rate"],
    errors="coerce"
)

# Select aircraft with the most observations
aircraft_counts = (
    df.groupby("icao")
    .size()
    .sort_values(ascending=False)
)

top_icao = aircraft_counts.index[0]

# Extract selected aircraft trajectory
trajectory = df[df["icao"] == top_icao].copy()

trajectory = trajectory.dropna(
    subset=["timestamp_utc", "altitude_baro"]
)

trajectory = trajectory.sort_values("timestamp_utc")

if len(trajectory) < 2:
    print("At least two observations are required.")
    raise SystemExit

# Get flight number
flight_values = trajectory["flight"].dropna()

if flight_values.empty:
    flight_name = top_icao
else:
    flight_name = str(flight_values.iloc[0]).strip()

# Get previous altitude
trajectory["previous_altitude"] = (
    trajectory["altitude_baro"].shift(1)
)

# Get previous timestamp
trajectory["previous_timestamp"] = (
    trajectory["timestamp_utc"].shift(1)
)

# Calculate altitude change
trajectory["altitude_change_ft"] = (
    trajectory["altitude_baro"]
    - trajectory["previous_altitude"]
)

# Calculate elapsed time
trajectory["elapsed_seconds"] = (
    trajectory["timestamp_utc"]
    - trajectory["previous_timestamp"]
).dt.total_seconds()

# Calculate climb rate in feet per minute
trajectory["calculated_climb_rate"] = (
    trajectory["altitude_change_ft"]
    / trajectory["elapsed_seconds"]
) * 60

# Remove impossible elapsed times
trajectory.loc[
    trajectory["elapsed_seconds"] <= 0,
    "calculated_climb_rate"
] = float("nan")

# Calculate summary statistics
valid_calculated = trajectory["calculated_climb_rate"].dropna()
valid_reported = trajectory["vertical_rate"].dropna()

print()
print("Vertical rate analysis")
print("ICAO:", top_icao)
print("Flight:", flight_name)
print("Observations:", len(trajectory))

if not valid_calculated.empty:
    print(
        "Average calculated climb rate:",
        round(valid_calculated.mean(), 2),
        "ft/min"
    )

if not valid_reported.empty:
    print(
        "Average ADS-B vertical rate:",
        round(valid_reported.mean(), 2),
        "ft/min"
    )

# Display detailed values
print()
print(
    trajectory[
        [
            "timestamp_utc",
            "altitude_baro",
            "altitude_change_ft",
            "elapsed_seconds",
            "calculated_climb_rate",
            "vertical_rate"
        ]
    ].to_string(index=False)
)

# Create graph
fig, ax = plt.subplots(figsize=(11, 6))

# Plot calculated climb rate
ax.plot(
    trajectory["timestamp_utc"],
    trajectory["calculated_climb_rate"],
    marker="o",
    linestyle="-",
    label="Calculated climb rate"
)

# Plot ADS-B reported vertical rate
ax.plot(
    trajectory["timestamp_utc"],
    trajectory["vertical_rate"],
    marker="s",
    linestyle="--",
    label="ADS-B vertical rate"
)

# Add zero reference line
ax.axhline(
    y=0,
    linestyle=":",
    label="Level flight"
)

# Format time labels
ax.xaxis.set_major_formatter(
    mdates.DateFormatter(
        "%H:%M:%S",
        tz=mdates.UTC
    )
)

fig.autofmt_xdate()

# Configure graph
ax.set_title(
    f"Butterflyts - Vertical Rate Comparison ({flight_name})"
)

ax.set_xlabel("time (UTC)")
ax.set_ylabel("vertical rate (ft/min)")

ax.legend()
ax.grid(True)

fig.tight_layout()

plt.show()