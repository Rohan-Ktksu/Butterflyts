# Step 17.1 - Export aircraft classification results

from pathlib import Path

from classify_all_aircraft import results_df, latest_file


PROCESSED_DIR = Path("data/processed")


# Create processed-data directory if it does not exist
PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# Get timestamp portion from raw ADS-B filename
source_name = latest_file.stem

timestamp_part = source_name.replace(
    "vobl_adsb_",
    ""
)


# Create output filenames
parquet_file = (
    PROCESSED_DIR
    / f"aircraft_classifications_{timestamp_part}.parquet"
)

csv_file = (
    PROCESSED_DIR
    / f"aircraft_classifications_{timestamp_part}.csv"
)


# Save classification data
results_df.to_parquet(
    parquet_file,
    index=False
)

results_df.to_csv(
    csv_file,
    index=False
)


# Display export summary
print()
print("Classification export complete")

print(
    "Aircraft records:",
    len(results_df)
)

print(
    "Parquet file:",
    parquet_file
)

print(
    "CSV file:",
    csv_file
)