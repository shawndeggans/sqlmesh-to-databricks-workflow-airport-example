#!/usr/bin/env python3
"""
Inspect Databricks Catalog

Lists all schemas, tables, and views in the airport_inventory_dev catalog.
Use this script to understand the current state before cleanup operations.

Usage:
    python scripts/inspect_databricks_catalog.py
    python scripts/inspect_databricks_catalog.py --catalog airport_inventory_dev
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def get_connection():
    """Create a Databricks SQL connection using environment variables."""
    from databricks import sql

    host = os.environ.get("DATABRICKS_HOST")
    token = os.environ.get("DATABRICKS_TOKEN")
    http_path = os.environ.get(
        "DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/5f2a600257bdb5b8"
    )

    if not host or not token:
        print("Error: DATABRICKS_HOST and DATABRICKS_TOKEN must be set")
        print("Either export them or add them to .env file")
        sys.exit(1)

    return sql.connect(
        server_hostname=host,
        http_path=http_path,
        access_token=token,
    )


def list_schemas(cursor, catalog: str) -> list[str]:
    """List all schemas in the catalog."""
    cursor.execute(f"SHOW SCHEMAS IN {catalog}")
    return [row[0] for row in cursor.fetchall()]


def list_tables(cursor, catalog: str, schema: str) -> list[dict]:
    """List all tables in a schema."""
    try:
        cursor.execute(f"SHOW TABLES IN {catalog}.{schema}")
        return [
            {"name": row[1], "type": "TABLE", "schema": schema}
            for row in cursor.fetchall()
        ]
    except Exception as e:
        print(f"  Warning: Could not list tables in {schema}: {e}")
        return []


def list_views(cursor, catalog: str, schema: str) -> list[dict]:
    """List all views in a schema."""
    try:
        cursor.execute(f"SHOW VIEWS IN {catalog}.{schema}")
        return [
            {"name": row[1], "type": "VIEW", "schema": schema}
            for row in cursor.fetchall()
        ]
    except Exception as e:
        # Views might not be supported or schema might be empty
        return []


def categorize_schema(schema_name: str) -> str:
    """Categorize a schema by its SQLMesh role."""
    if schema_name == "raw":
        return "source"
    elif schema_name.startswith("sqlmesh__"):
        return "sqlmesh_physical"
    elif "__" in schema_name:
        # e.g., staging__dev, marts__prod
        return "sqlmesh_virtual"
    elif schema_name in ("default", "information_schema"):
        return "system"
    else:
        return "other"


def main():
    parser = argparse.ArgumentParser(
        description="Inspect Databricks catalog contents"
    )
    parser.add_argument(
        "--catalog",
        default="airport_inventory_dev",
        help="Catalog to inspect (default: airport_inventory_dev)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed table/view listings",
    )
    args = parser.parse_args()

    # Load environment variables from .env file
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded environment from {env_path}")

    print(f"\nConnecting to Databricks...")
    conn = get_connection()
    cursor = conn.cursor()

    print(f"Inspecting catalog: {args.catalog}\n")
    print("=" * 60)

    # Get all schemas
    schemas = list_schemas(cursor, args.catalog)
    print(f"Found {len(schemas)} schemas:\n")

    # Categorize schemas
    categories = {
        "source": [],
        "sqlmesh_physical": [],
        "sqlmesh_virtual": [],
        "system": [],
        "other": [],
    }

    for schema in schemas:
        cat = categorize_schema(schema)
        categories[cat].append(schema)

    # Print by category
    category_labels = {
        "source": "Source Data (raw)",
        "sqlmesh_physical": "SQLMesh Physical Tables (sqlmesh__*)",
        "sqlmesh_virtual": "SQLMesh Virtual Environments (*__env)",
        "system": "System Schemas",
        "other": "Other Schemas",
    }

    summary = []

    for cat, label in category_labels.items():
        if categories[cat]:
            print(f"\n{label}:")
            print("-" * 40)
            for schema in sorted(categories[cat]):
                tables = list_tables(cursor, args.catalog, schema)
                views = list_views(cursor, args.catalog, schema)

                table_count = len(tables)
                view_count = len(views)
                total = table_count + view_count

                print(f"  {schema}: {table_count} tables, {view_count} views")
                summary.append({
                    "schema": schema,
                    "category": cat,
                    "tables": table_count,
                    "views": view_count,
                })

                if args.verbose and (tables or views):
                    for t in tables:
                        print(f"    - [TABLE] {t['name']}")
                    for v in views:
                        print(f"    - [VIEW]  {v['name']}")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    total_schemas = len(schemas)
    sqlmesh_schemas = len(categories["sqlmesh_physical"]) + len(categories["sqlmesh_virtual"])

    print(f"Total schemas: {total_schemas}")
    print(f"SQLMesh-managed schemas: {sqlmesh_schemas}")
    print(f"  - Physical (sqlmesh__*): {len(categories['sqlmesh_physical'])}")
    print(f"  - Virtual (*__env): {len(categories['sqlmesh_virtual'])}")
    print(f"Source schemas (raw): {len(categories['source'])}")
    print(f"Other schemas: {len(categories['other'])}")

    # Cleanup recommendations
    print("\n" + "=" * 60)
    print("CLEANUP RECOMMENDATIONS")
    print("=" * 60)

    if categories["sqlmesh_virtual"]:
        print("\nTo remove virtual environments:")
        for schema in categories["sqlmesh_virtual"]:
            env_name = schema.split("__")[-1] if "__" in schema else schema
            print(f"  sqlmesh --gateway databricks_dev invalidate_environment {env_name}")

    if categories["sqlmesh_physical"]:
        print("\nTo clean up unused physical tables:")
        print("  sqlmesh --gateway databricks_dev janitor")

    print("\nTo run full cleanup script:")
    print("  python scripts/cleanup_databricks_catalog.py --dry-run")
    print("  python scripts/cleanup_databricks_catalog.py --execute")

    cursor.close()
    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
