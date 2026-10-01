
# Step 13.2 - Visualize aircraft altitude over time

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

# Read the dataset
df = pd.read_parquet(latest_file)

# Keep airborne observations with valid ICAO identifiers
df = df[
    (df["on_ground"] == False)
    & df["icao"].notna()
].copy()

if df.empty:
    print("No airborne observations found.")
    raise SystemExit

# Convert timestamps into datetime values
df["timestamp_utc"] = pd.to_datetime(
    df["timestamp_utc"],
    utc=True,
    errors="coerce"
)

# Convert altitude values into numbers
df["altitude_baro"] = pd.to_numeric(
    df["altitude_baro"],
    errors="coerce"
)

# Select aircraft with the most observations
aircraft_counts = (
    df.groupby("icao")
    .size()
    .sort_values(ascending=False)
)

top_icao = aircraft_counts.index[0]

# Extract observations for the selected aircraft
trajectory = df[df["icao"] == top_icao].copy()

# Remove records with missing timestamps or altitude
trajectory = trajectory.dropna(
    subset=["timestamp_utc", "altitude_baro"]
)

# Sort observations chronologically
trajectory = trajectory.sort_values("timestamp_utc")

if len(trajectory) < 2:
    print("At least two valid altitude observations are required.")
    raise SystemExit

# Get flight number
flight_values = trajectory["flight"].dropna()

if flight_values.empty:
    flight_name = top_icao
else:
    flight_name = str(flight_values.iloc[0]).strip()

# Get first and last altitude observations
start = trajectory.iloc[0]
end = trajectory.iloc[-1]

# Create altitude graph
fig, ax = plt.subplots(figsize=(11, 6))

# Draw altitude progression
ax.plot(
    trajectory["timestamp_utc"],
    trajectory["altitude_baro"],
    marker="o",
    linestyle="-",
    label="Barometric altitude"
)

# Mark starting altitude
ax.scatter(
    start["timestamp_utc"],
    start["altitude_baro"],
    marker="s",
    s=120,
    color="green",
    label="Start",
    zorder=5
)

# Mark ending altitude
ax.scatter(
    end["timestamp_utc"],
    end["altitude_baro"],
    marker="X",
    s=140,
    color="red",
    label="End",
    zorder=5
)

# Format time labels
ax.xaxis.set_major_formatter(
    mdates.DateFormatter("%H:%M:%S", tz=mdates.UTC)
)

fig.autofmt_xdate()

# Configure graph
ax.set_title(
    f"Butterflyts - Aircraft Altitude ({flight_name})"
)

ax.set_xlabel("time (UTC)")
ax.set_ylabel("barometric altitude (ft)")

ax.legend()
ax.grid(True)

fig.tight_layout()

# Display graph
plt.show()
