# AeroPulse
# Download OurAirports datasets

from pathlib import Path
import requests

DATASETS = {
    "airports.csv":"https://ourairports.com/data/airports.csv",
    "runways.csv":"https://ourairports.com/data/runways.csv",
}
OUTPUT_DIR = Path("data/external/ourairports")

def download_file(filename, url):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = OUTPUT_DIR/ filename
    print(f"Downloading{filename}...")
    response= requests.get(url, timeout=60)
    response.raise_for_status()

    output_path.write_bytes(response.content)

    print(f"Saved:{output_path}" )
    print(f"Size:{output_path.stat().st_size/1024/1024:.2f} MB")

def main():
    print("AeroPulse - OurAirports Downloader")

    for filename, url in DATASETS.items():
        download_file(filename, url)
    print("\nDownload complete.")
if __name__ == "__main__":
    main()
