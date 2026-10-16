# Step 18.1 - Build historical aircraft classification dataset

from pathlib import Path

import pandas as pd


PROCESSED_DIR = Path("data/processed")

HISTORY_PARQUET = (
    PROCESSED_DIR
    / "classification_history.parquet"
)

HISTORY_CSV = (
    PROCESSED_DIR
    / "classification_history.csv"
)


# Find all per-session classification files
classification_files = sorted(
    PROCESSED_DIR.glob(
        "aircraft_classifications_*.parquet"
    )
)


if not classification_files:
    print("No classification files found.")
    raise SystemExit


print(
    "Classification sessions found:",
    len(classification_files)
)


# Store each session dataset
session_datasets = []


for classification_file in classification_files:

    print(
        "Reading:",
        classification_file
    )


    # Read one classification session
    session_df = pd.read_parquet(
        classification_file
    )


    # Extract session identifier from filename
    session_id = (
        classification_file.stem
        .replace(
            "aircraft_classifications_",
            ""
        )
    )


    # Convert session identifier into timestamp
    collection_time = pd.to_datetime(
        session_id,
        format="%Y%m%d_%H%M%S",
        utc=True,
        errors="coerce"
    )


    # Add historical tracking information
    session_df["session_id"] = session_id

    session_df["collection_time_utc"] = (
        collection_time
    )

    session_df["source_file"] = (
        classification_file.name
    )


    session_datasets.append(
        session_df
    )


# Combine all sessions
history_df = pd.concat(
    session_datasets,
    ignore_index=True
)


# Sort historical records
history_df = history_df.sort_values(
    [
        "collection_time_utc",
        "icao"
    ]
).reset_index(drop=True)


# Check for duplicate aircraft within a session
duplicate_count = history_df.duplicated(
    subset=[
        "session_id",
        "icao"
    ]
).sum()


print()
print("Historical dataset summary")

print(
    "Sessions:",
    history_df["session_id"]
    .nunique()
)

print(
    "Total aircraft records:",
    len(history_df)
)

print(
    "Unique ICAO aircraft:",
    history_df["icao"]
    .nunique()
)

print(
    "Duplicate session-aircraft rows:",
    duplicate_count
)


# Display historical pattern counts
print()
print("Historical flight patterns")

print(
    history_df["pattern"]
    .value_counts()
    .to_string()
)


# Save historical dataset
history_df.to_parquet(
    HISTORY_PARQUET,
    index=False
)

history_df.to_csv(
    HISTORY_CSV,
    index=False
)


print()
print("Historical dataset saved")

print(
    "Parquet:",
    HISTORY_PARQUET
)

print(
    "CSV:",
    HISTORY_CSV
)