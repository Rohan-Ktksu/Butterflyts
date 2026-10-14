# Step 17.2 - Validate exported aircraft classification files

from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal


PROCESSED_DIR = Path("data/processed")


# Find exported Parquet files
parquet_files = list(
    PROCESSED_DIR.glob(
        "aircraft_classifications_*.parquet"
    )
)

if not parquet_files:
    print("No classification Parquet files found.")
    raise SystemExit


# Select newest Parquet file
latest_parquet = max(
    parquet_files,
    key=lambda file: file.stat().st_mtime
)


# Find matching CSV file
csv_file = latest_parquet.with_suffix(".csv")

if not csv_file.exists():
    print("Matching CSV file not found:", csv_file)
    raise SystemExit


print("Parquet:", latest_parquet)
print("CSV:", csv_file)


# Read exported data
parquet_df = pd.read_parquet(
    latest_parquet
)

csv_df = pd.read_csv(
    csv_file
)


# Check row counts
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


# Check column names
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


# Sort both datasets before comparison
sort_columns = [
    "icao",
    "flight"
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


# Compare CSV and Parquet values
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
    print("FAILED: File contents are different.")
    print(error)


# Check expected columns
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
    "pattern"
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


# Check for duplicate aircraft rows
duplicate_icao = (
    parquet_df["icao"]
    .duplicated()
    .sum()
)


print()
print("Duplicate aircraft validation")

print(
    "Duplicate ICAO rows:",
    duplicate_icao
)


# Display pattern counts
print()
print("Stored flight patterns")

print(
    parquet_df["pattern"]
    .value_counts()
    .to_string()
)


# Final validation result
print()

if files_match:

    print("EXPORT VALIDATION PASSED")

    print(
        "CSV and Parquet contain matching classification data."
    )

else:

    print("EXPORT VALIDATION FAILED")