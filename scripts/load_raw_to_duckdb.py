#!/usr/bin/env python3
"""
Load raw parquet files into DuckDB for local development.

Creates a 'raw' schema and loads:
- raw.aviation_facilities
- raw.runway_ends
"""

from pathlib import Path

import duckdb

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "dev.duckdb"


def load_parquet_to_table(
    conn: duckdb.DuckDBPyConnection,
    parquet_path: Path,
    table_name: str,
) -> None:
    """Load a parquet file into a DuckDB table."""
    if not parquet_path.exists():
        print(f"  Skipping {table_name}: {parquet_path} not found")
        return

    # Drop and recreate table from parquet
    conn.execute(f"DROP TABLE IF EXISTS raw.{table_name}")
    conn.execute(
        f"CREATE TABLE raw.{table_name} AS SELECT * FROM read_parquet('{parquet_path}')"
    )

    # Get row count
    result = conn.execute(f"SELECT COUNT(*) FROM raw.{table_name}").fetchone()
    count = result[0] if result else 0
    print(f"  Loaded {count:,} rows into raw.{table_name}")


def main() -> None:
    """Load all raw data into DuckDB."""
    print(f"Database: {DB_PATH}")

    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Connect to DuckDB (creates file if not exists)
    conn = duckdb.connect(str(DB_PATH))

    # Create raw schema
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw")

    # Load each data source
    print("\nLoading data into raw schema...")
    load_parquet_to_table(
        conn,
        RAW_DIR / "aviation_facilities.parquet",
        "aviation_facilities",
    )
    load_parquet_to_table(
        conn,
        RAW_DIR / "runway_ends.parquet",
        "runway_ends",
    )

    # Show summary
    print("\nTables in raw schema:")
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'raw'"
    ).fetchall()
    for (table_name,) in tables:
        result = conn.execute(f"SELECT COUNT(*) FROM raw.{table_name}").fetchone()
        count = result[0] if result else 0
        print(f"  raw.{table_name}: {count:,} rows")

    conn.close()
    print("\nLoad complete!")


if __name__ == "__main__":
    main()
