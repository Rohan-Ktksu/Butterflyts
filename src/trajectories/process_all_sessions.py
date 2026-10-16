
# Step 19.3 - Automatically process all ADS-B sessions

from pathlib import Path

from classification_engine import classify_adsb_file


RAW_DIR = Path("data/raw/adsb")
PROCESSED_DIR = Path("data/processed")

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# Find all raw ADS-B recordings
raw_files = sorted(
    RAW_DIR.glob("vobl_adsb_*.parquet")
)

if not raw_files:
    print("No raw ADS-B files found.")
    raise SystemExit

print("Raw ADS-B sessions found:", len(raw_files))

successful = 0
skipped = 0
failed = 0

# Process each recording independently
for raw_file in raw_files:

    session_id = raw_file.stem.removeprefix(
        "vobl_adsb_"
    )

    parquet_output = (
        PROCESSED_DIR
        / f"aircraft_classifications_{session_id}.parquet"
    )

    csv_output = (
        PROCESSED_DIR
        / f"aircraft_classifications_{session_id}.csv"
    )

    print()
    print("Processing:", raw_file.name)

    # Skip sessions already exported in both formats
    if parquet_output.exists() and csv_output.exists():
        print("Already processed. Skipping.")
        skipped += 1
        continue

    try:
        # Classify aircraft in this recording
        results_df = classify_adsb_file(raw_file)

        # Export results
        results_df.to_parquet(
            parquet_output,
            index=False
        )

        results_df.to_csv(
            csv_output,
            index=False
        )

        print("Aircraft classified:", len(results_df))
        print("Parquet:", parquet_output)
        print("CSV:", csv_output)

        successful += 1

    except (ValueError, OSError, KeyError, TypeError) as error:
        print("FAILED:", error)
        failed += 1

# Display batch processing summary
print()
print("Batch processing summary")

print("Total sessions:", len(raw_files))
print("Successfully processed:", successful)
print("Already processed:", skipped)
print("Failed:", failed)
# Stop pipeline if any session failed
if failed > 0:
    print("Batch processing failed.")
    raise SystemExit(1)