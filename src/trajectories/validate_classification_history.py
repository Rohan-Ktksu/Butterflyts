# Step 18.2 - Validate historical classification dataset

from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal


PROCESSED_DIR = Path("data/processed")

HISTORY_PARQUET = (
    PROCESSED_DIR
    / "classification_history.parquet"
)

HISTORY_CSV = (
    PROCESSED_DIR
    / "classification_history.csv"
)


# Check files exist
if not HISTORY_PARQUET.exists():
    print("History Parquet file not found.")
    raise SystemExit


if not HISTORY_CSV.exists():
    print("History CSV file not found.")
    raise SystemExit


print("Parquet:", HISTORY_PARQUET)
print("CSV:", HISTORY_CSV)


# Read historical datasets
parquet_df = pd.read_parquet(
    HISTORY_PARQUET
)

csv_df = pd.read_csv(
    HISTORY_CSV
)


# Convert CSV timestamp back to datetime
csv_df["collection_time_utc"] = pd.to_datetime(
    csv_df["collection_time_utc"],
    utc=True,
    errors="coerce"
)


# Validate row counts
print()
print("Row count validation")

print(
    "Parquet rows:",
    len(parquet_df)
)

print(
    "CSV rows:",
    len(csv_df)
)


if len(parquet_df) != len(csv_df):
    print("FAILED: Row counts do not match.")
    raise SystemExit


# Validate columns
print()
print("Column validation")

print(
    "Parquet columns:",
    len(parquet_df.columns)
)

print(
    "CSV columns:",
    len(csv_df.columns)
)


if list(parquet_df.columns) != list(csv_df.columns):
    print("FAILED: Column names do not match.")
    raise SystemExit


# Sort before comparison
sort_columns = [
    "session_id",
    "icao"
]


parquet_compare = (
    parquet_df
    .sort_values(sort_columns)
    .reset_index(drop=True)
)


csv_compare = (
    csv_df
    .sort_values(sort_columns)
    .reset_index(drop=True)
)


# Compare CSV and Parquet data
try:

    assert_frame_equal(
        parquet_compare,
        csv_compare,
        check_dtype=False,
        check_exact=False,
        rtol=1e-5,
        atol=1e-5
    )

    files_match = True

except AssertionError as error:

    files_match = False

    print()
    print("FAILED: CSV and Parquet differ.")
    print(error)


# Validate required historical columns
required_columns = [
    "icao",
    "flight",
    "observations",
    "candidate_runway",
    "minimum_runway_nm",
    "runway_associated",
    "airport_change_nm",
    "altitude_change_ft",
    "speed_change_knots",
    "average_vertical_rate",
    "departure_score",
    "arrival_score",
    "pattern",
    "session_id",
    "collection_time_utc",
    "source_file"
]


missing_columns = [
    column
    for column in required_columns
    if column not in parquet_df.columns
]


print()
print("Required column validation")


if missing_columns:

    print(
        "FAILED: Missing columns:",
        missing_columns
    )

    raise SystemExit

else:

    print("All required columns are present.")


# Validate session timestamps
invalid_times = (
    parquet_df["collection_time_utc"]
    .isna()
    .sum()
)


print()
print("Timestamp validation")

print(
    "Invalid collection timestamps:",
    invalid_times
)


if invalid_times > 0:
    print("FAILED: Invalid session timestamps found.")
    raise SystemExit


# Validate session identifiers
invalid_session_ids = (
    ~parquet_df["session_id"]
    .astype(str)
    .str.match(r"^\d{8}_\d{6}$")
).sum()


print()
print("Session ID validation")

print(
    "Invalid session IDs:",
    invalid_session_ids
)


if invalid_session_ids > 0:
    print("FAILED: Invalid session IDs found.")
    raise SystemExit


# Validate duplicate session-aircraft rows
duplicate_count = parquet_df.duplicated(
    subset=[
        "session_id",
        "icao"
    ]
).sum()


print()
print("Duplicate validation")

print(
    "Duplicate session-aircraft rows:",
    duplicate_count
)


if duplicate_count > 0:
    print("FAILED: Duplicate historical records found.")
    raise SystemExit


# Display historical dataset statistics
print()
print("Historical dataset statistics")

print(
    "Sessions:",
    parquet_df["session_id"]
    .nunique()
)

print(
    "Aircraft records:",
    len(parquet_df)
)

print(
    "Unique ICAO aircraft:",
    parquet_df["icao"]
    .nunique()
)


# Display pattern counts
print()
print("Historical flight patterns")

print(
    parquet_df["pattern"]
    .value_counts()
    .to_string()
)


# Final result
print()

if files_match:

    print("HISTORY VALIDATION PASSED")

    print(
        "Historical CSV and Parquet datasets match."
    )

else:

    print("HISTORY VALIDATION FAILED")