# Step 14.1 - Visualize aircraft ground speed over time

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

# Keep airborne aircraft with valid ICAO identifiers
df = df[
    (df["on_ground"] == False)
    & df["icao"].notna()
].copy()

if df.empty:
    print("No airborne observations found.")
    raise SystemExit

# Convert timestamps
df["timestamp_utc"] = pd.to_datetime(
    df["timestamp_utc"],
    utc=True,
    errors="coerce"
)

# Convert ground speed into numeric values
df["ground_speed"] = pd.to_numeric(
    df["ground_speed"],
    errors="coerce"
)

# Count observations for each aircraft
aircraft_counts = (
    df.groupby("icao")
    .size()
    .sort_values(ascending=False)
)

# Select aircraft with most observations
top_icao = aircraft_counts.index[0]

# Get trajectory for selected aircraft
trajectory = df[df["icao"] == top_icao].copy()

# Keep valid timestamp and speed observations
trajectory = trajectory.dropna(
    subset=["timestamp_utc", "ground_speed"]
)

# Sort chronologically
trajectory = trajectory.sort_values("timestamp_utc")

if len(trajectory) < 2:
    print("At least two valid speed observations are required.")
    raise SystemExit

# Get flight number
flight_values = trajectory["flight"].dropna()

if flight_values.empty:
    flight_name = top_icao
else:
    flight_name = str(flight_values.iloc[0]).strip()

# Get first and last observations
start = trajectory.iloc[0]
end = trajectory.iloc[-1]

# Calculate speed statistics
initial_speed = start["ground_speed"]
final_speed = end["ground_speed"]

minimum_speed = trajectory["ground_speed"].min()
maximum_speed = trajectory["ground_speed"].max()
average_speed = trajectory["ground_speed"].mean()

speed_change = final_speed - initial_speed

# Calculate observation duration
duration_seconds = (
    end["timestamp_utc"]
    - start["timestamp_utc"]
).total_seconds()

# Display speed summary
print()
print("Ground speed analysis")
print("ICAO:", top_icao)
print("Flight:", flight_name)
print("Observations:", len(trajectory))
print("Initial speed:", round(initial_speed, 2), "knots")
print("Final speed:", round(final_speed, 2), "knots")
print("Speed change:", round(speed_change, 2), "knots")
print("Minimum speed:", round(minimum_speed, 2), "knots")
print("Maximum speed:", round(maximum_speed, 2), "knots")
print("Average speed:", round(average_speed, 2), "knots")
print("Duration:", round(duration_seconds, 2), "seconds")

# Create ground speed graph
fig, ax = plt.subplots(figsize=(11, 6))

# Plot ground speed
ax.plot(
    trajectory["timestamp_utc"],
    trajectory["ground_speed"],
    marker="o",
    linestyle="-",
    label="Ground speed"
)

# Mark starting speed
ax.scatter(
    start["timestamp_utc"],
    start["ground_speed"],
    marker="s",
    s=120,
    label="Start",
    zorder=5
)

# Mark ending speed
ax.scatter(
    end["timestamp_utc"],
    end["ground_speed"],
    marker="X",
    s=140,
    label="End",
    zorder=5
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
    f"Butterflyts - Aircraft Ground Speed ({flight_name})"
)

ax.set_xlabel("time (UTC)")
ax.set_ylabel("ground speed (knots)")

ax.legend()
ax.grid(True)

fig.tight_layout()

# Display graph
plt.show()