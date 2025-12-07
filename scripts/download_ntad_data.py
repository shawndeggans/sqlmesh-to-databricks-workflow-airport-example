#!/usr/bin/env python3
"""
Download NTAD Aviation data from BTS ArcGIS API.

Data sources:
- Aviation Facilities: ~20,000 airports/heliports
- Runway Ends: Runway-level detail with dimensions and surface types

Both are updated every 28 days.
"""

import json
from pathlib import Path

import httpx
import pyarrow as pa
import pyarrow.parquet as pq

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "raw"

# ArcGIS API endpoints
AVIATION_FACILITIES_URL = (
    "https://services.arcgis.com/xOi1kZaI0eWDREZC/arcgis/rest/services/"
    "Aviation_Facilities/FeatureServer/0/query"
)
RUNWAY_ENDS_URL = (
    "https://services.arcgis.com/xOi1kZaI0eWDREZC/arcgis/rest/services/"
    "Runway_Ends/FeatureServer/0/query"
)


def fetch_arcgis_features(url: str, timeout: float = 120.0) -> list[dict]:
    """Fetch all features from an ArcGIS FeatureServer endpoint.

    Uses pagination to handle large datasets.
    """
    all_features = []
    offset = 0
    batch_size = 2000  # ArcGIS default max is often 1000-2000

    params = {
        "where": "1=1",
        "outFields": "*",
        "f": "json",
        "resultRecordCount": batch_size,
    }

    with httpx.Client(timeout=timeout) as client:
        while True:
            params["resultOffset"] = offset
            print(f"  Fetching records {offset} to {offset + batch_size}...")

            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            features = data.get("features", [])
            if not features:
                break

            # Extract attributes (properties) from each feature
            for feature in features:
                attrs = feature.get("attributes", {})
                # Also extract geometry if present
                if "geometry" in feature:
                    geom = feature["geometry"]
                    if geom:
                        attrs["_longitude"] = geom.get("x")
                        attrs["_latitude"] = geom.get("y")
                all_features.append(attrs)

            # Check if we got fewer than requested (last page)
            if len(features) < batch_size:
                break

            offset += batch_size

    return all_features


def save_to_parquet(records: list[dict], output_path: Path) -> None:
    """Save records to a parquet file."""
    if not records:
        print(f"  No records to save for {output_path.name}")
        return

    # Convert to PyArrow table
    table = pa.Table.from_pylist(records)

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to parquet
    pq.write_table(table, output_path)
    print(f"  Saved {len(records)} records to {output_path}")


def download_aviation_facilities() -> None:
    """Download Aviation Facilities data."""
    print("Downloading Aviation Facilities...")
    features = fetch_arcgis_features(AVIATION_FACILITIES_URL)
    output_path = DATA_DIR / "aviation_facilities.parquet"
    save_to_parquet(features, output_path)


def download_runway_ends() -> None:
    """Download Runway Ends data."""
    print("Downloading Runway Ends...")
    features = fetch_arcgis_features(RUNWAY_ENDS_URL)
    output_path = DATA_DIR / "runway_ends.parquet"
    save_to_parquet(features, output_path)


def main() -> None:
    """Download all NTAD data sources."""
    print(f"Data will be saved to: {DATA_DIR}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    download_aviation_facilities()
    download_runway_ends()

    print("\nDownload complete!")


if __name__ == "__main__":
    main()
