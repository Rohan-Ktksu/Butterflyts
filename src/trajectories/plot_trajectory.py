#visualize recorded aircraft trajectory
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

#Bengaluru Airport coordiantes
VOBL_LAT = 13.1986
VOBL_LON = 77.7066

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

# Read collected observations
df = pd.read_parquet(latest_file)

# Keep airborne observations with valid aircraft identifiers
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
    utc=True
)

# Sort observations by aircraft and timestamp
df = df.sort_values(["icao", "timestamp_utc"])

# Select aircraft with most observations
aircraft_counts = (
    df.groupby("icao")
    .size()
    .sort_values(ascending=False)
)

top_icao = aircraft_counts.index[0]

# Get selected aircraft trajectory
trajectory = (
    df[df["icao"] == top_icao]
    .sort_values("timestamp_utc")
)

if len(trajectory) < 2:
    print("At least two observations are required.")
    raise SystemExit

# Get flight number
flight_values = trajectory["flight"].dropna()

if flight_values.empty:
    flight_name = top_icao
else:
    flight_name = str(flight_values.iloc[0]).strip()

# Get first and last positions
start = trajectory.iloc[0]
end = trajectory.iloc[-1]

#create trajectory plot
plt.figure(figsize = (10,7))
#Draw aircraft path
plt.plot(trajectory["longitude"], trajectory["latitude"], marker = "o", linestyle="-", label="Aircraft trajectory")
#mark airport position
plt.scatter(VOBL_LON, VOBL_LAT, marker="*", s=250, label = "VOBL Airport")

#Mark starting poisition
plt.scatter(start["longitude"], start["latitude"], marker = "s", s = 120, label = "Start")
# Mark ending position
plt.scatter(
    end["longitude"],
    end["latitude"],
    marker="X",
    s=180,
    color="red",
    label="End",
    zorder=10
)
#Display aircraft movement direction
for i in range(len(trajectory)-1):
    current = trajectory.iloc[i]
    next_point = trajectory.iloc[i+1]
    plt.annotate("", xy=(next_point["longitude"],next_point["latitude"]), xytext = (current["longitude"], current["latitude"]), arrowprops={"arrowstyle": "->", "lw":1})
#configure graph
plt.title(f"Butterflyts - Aircraft Trajectory({flight_name})")
plt.xlabel("longitude")
plt.legend()
plt.grid(True)
plt.axis("equal")
plt.tight_layout()

#display graph
plt.show()
