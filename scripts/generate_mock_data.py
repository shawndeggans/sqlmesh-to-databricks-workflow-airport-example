#!/usr/bin/env python3
"""
Generate mock data for CI/offline testing.

Creates synthetic aviation facilities and runway data that matches
the schema of the real NTAD data, without requiring network access.
"""

import random
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "raw"

# Sample data for generating realistic mock records
STATES = [
    ("AL", "Alabama"), ("AK", "Alaska"), ("AZ", "Arizona"), ("AR", "Arkansas"),
    ("CA", "California"), ("CO", "Colorado"), ("CT", "Connecticut"), ("DE", "Delaware"),
    ("FL", "Florida"), ("GA", "Georgia"), ("HI", "Hawaii"), ("ID", "Idaho"),
    ("IL", "Illinois"), ("IN", "Indiana"), ("IA", "Iowa"), ("KS", "Kansas"),
    ("KY", "Kentucky"), ("LA", "Louisiana"), ("ME", "Maine"), ("MD", "Maryland"),
    ("MA", "Massachusetts"), ("MI", "Michigan"), ("MN", "Minnesota"), ("MS", "Mississippi"),
    ("MO", "Missouri"), ("MT", "Montana"), ("NE", "Nebraska"), ("NV", "Nevada"),
    ("NH", "New Hampshire"), ("NJ", "New Jersey"), ("NM", "New Mexico"), ("NY", "New York"),
    ("NC", "North Carolina"), ("ND", "North Dakota"), ("OH", "Ohio"), ("OK", "Oklahoma"),
    ("OR", "Oregon"), ("PA", "Pennsylvania"), ("RI", "Rhode Island"), ("SC", "South Carolina"),
    ("SD", "South Dakota"), ("TN", "Tennessee"), ("TX", "Texas"), ("UT", "Utah"),
    ("VT", "Vermont"), ("VA", "Virginia"), ("WA", "Washington"), ("WV", "West Virginia"),
    ("WI", "Wisconsin"), ("WY", "Wyoming"),
]

CITIES = [
    "Springfield", "Franklin", "Clinton", "Madison", "Georgetown",
    "Salem", "Bristol", "Fairview", "Oakland", "Newport",
    "Riverside", "Greenville", "Burlington", "Manchester", "Milton",
]

AIRPORT_CATEGORIES = ["A", "B", "C", "D"]
SERVICE_TYPES = ["COMMERCIAL", "GENERAL AVIATION", "MILITARY", "PRIVATE"]
OWNER_TYPES = ["PUBLIC", "PRIVATE", "MILITARY"]
OPER_STATUS = ["OPERATIONAL", "CLOSED", "ABANDONED"]
CONGESTION_LEVELS = ["NONE", "LOW", "MEDIUM", "HIGH"]
SURFACE_TYPES = ["ASPH", "CONC", "TURF", "GRVL", "DIRT", "WATER"]


def generate_loc_id(index: int) -> str:
    """Generate a 3-4 character FAA location identifier."""
    # Mix of realistic patterns
    if index < 26:
        return chr(65 + index) + "00"
    elif index < 100:
        return f"K{chr(65 + (index % 26))}{index % 10}"
    else:
        return f"{index:04d}"[:4]


def generate_aviation_facilities(num_records: int = 500) -> list[dict]:
    """Generate mock aviation facilities records."""
    records = []

    for i in range(num_records):
        state_code, state_name = random.choice(STATES)
        city = random.choice(CITIES)
        loc_id = generate_loc_id(i)

        # Generate coordinates roughly within continental US
        latitude = random.uniform(25.0, 48.0)
        longitude = random.uniform(-124.0, -70.0)

        # Larger airports have more enplanements and operations
        is_major = random.random() < 0.1

        record = {
            "LOCID": loc_id,
            "ARPT_NAME": f"{city} {'International' if is_major else 'Regional'} Airport",
            "CITY": city,
            "STATE_ABBR": state_code,
            "COUNTY": f"{city} County",
            "LATITUDE": latitude,
            "LONGITUDE": longitude,
            "ELEVATION": random.randint(0, 10000),
            "ARPT_CAT": random.choice(AIRPORT_CATEGORIES),
            "SERV_TYPE": "COMMERCIAL" if is_major else random.choice(SERVICE_TYPES),
            "OWNER_TYPE": random.choice(OWNER_TYPES),
            "OPERSTATUS": "OPERATIONAL" if random.random() < 0.95 else random.choice(OPER_STATUS),
            "CONESSION": random.choice(CONGESTION_LEVELS),
            "TOT_ENP": random.randint(100000, 50000000) if is_major else random.randint(0, 100000),
            "AC_OPNS": random.randint(50000, 500000) if is_major else random.randint(100, 50000),
            "ACT_DATE": f"{random.randint(1940, 2020)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            "_latitude": latitude,
            "_longitude": longitude,
        }
        records.append(record)

    return records


def generate_runway_ends(facilities: list[dict]) -> list[dict]:
    """Generate mock runway ends records for each facility."""
    records = []

    for facility in facilities:
        loc_id = facility["LOCID"]

        # Each airport has 1-4 runways
        num_runways = random.randint(1, 4)

        for r in range(num_runways):
            # Runway designations are based on magnetic heading
            heading = random.randint(1, 36)
            opposite = (heading + 18) % 36 or 36
            runway_id = f"{heading:02d}/{opposite:02d}"

            # Major airports have longer runways
            is_major = facility.get("TOT_ENP", 0) > 100000
            base_length = 8000 if is_major else 3000

            record = {
                "LOCID": loc_id,
                "RUNWAY_ID": runway_id,
                "LENGTH": random.randint(base_length, base_length + 5000),
                "WIDTH": random.choice([75, 100, 150, 200]),
                "SURFACE": random.choice(SURFACE_TYPES),
                "PCN": f"{random.randint(20, 100)}/F/B/X/T" if random.random() < 0.7 else None,
            }
            records.append(record)

    return records


def save_to_parquet(records: list[dict], output_path: Path) -> None:
    """Save records to a parquet file."""
    table = pa.Table.from_pylist(records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, output_path)
    print(f"  Generated {len(records)} records -> {output_path}")


def main() -> None:
    """Generate all mock data files."""
    print(f"Generating mock data in: {DATA_DIR}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Set seed for reproducibility
    random.seed(42)

    # Generate facilities first (runways reference them)
    print("\nGenerating aviation facilities...")
    facilities = generate_aviation_facilities(num_records=500)
    save_to_parquet(facilities, DATA_DIR / "aviation_facilities.parquet")

    print("\nGenerating runway ends...")
    runways = generate_runway_ends(facilities)
    save_to_parquet(runways, DATA_DIR / "runway_ends.parquet")

    print("\nMock data generation complete!")


if __name__ == "__main__":
    main()
