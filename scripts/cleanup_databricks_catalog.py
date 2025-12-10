#!/usr/bin/env python3
"""
Cleanup Databricks Catalog

Removes SQLMesh-created schemas and objects from the airport_inventory_dev catalog.
Always run with --dry-run first to preview changes.

Usage:
    python scripts/cleanup_databricks_catalog.py --dry-run
    python scripts/cleanup_databricks_catalog.py --execute
    python scripts/cleanup_databricks_catalog.py --execute --include-raw  # Dangerous!

Options:
    --dry-run       Preview what would be deleted (default)
    --execute       Actually perform the deletion
    --include-raw   Also delete the raw schema (WARNING: deletes source data!)
    --schema NAME   Delete only a specific schema
    --catalog NAME  Target catalog (default: airport_inventory_dev)
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


def is_sqlmesh_schema(schema_name: str) -> bool:
    """Check if a schema was created by SQLMesh."""
    # Physical table schemas
    if schema_name.startswith("sqlmesh__"):
        return True
    # SQLMesh example schemas from init
    if schema_name.startswith("sqlmesh_example"):
        return True
    # Virtual environment schemas (staging__dev, marts__prod, etc.)
    if "__" in schema_name:
        parts = schema_name.split("__")
        # Check if it looks like a SQLMesh virtual schema
        if parts[0] in ("staging", "marts", "seeds", "raw"):
            return True
    return False


def is_protected_schema(schema_name: str, include_raw: bool = False) -> bool:
    """Check if a schema should be protected from deletion."""
    protected = {"default", "information_schema"}
    if not include_raw:
        protected.add("raw")
    return schema_name in protected


def drop_schema(cursor, catalog: str, schema: str, dry_run: bool = True) -> bool:
    """Drop a schema and all its contents."""
    sql = f"DROP SCHEMA IF EXISTS {catalog}.{schema} CASCADE"

    if dry_run:
        print(f"  [DRY-RUN] Would execute: {sql}")
        return True

    try:
        print(f"  Executing: {sql}")
        cursor.execute(sql)
        print(f"  Successfully dropped: {schema}")
        return True
    except Exception as e:
        print(f"  Error dropping {schema}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Clean up Databricks catalog",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Preview what would be deleted
    python scripts/cleanup_databricks_catalog.py --dry-run

    # Actually delete SQLMesh schemas
    python scripts/cleanup_databricks_catalog.py --execute

    # Delete a specific schema
    python scripts/cleanup_databricks_catalog.py --execute --schema staging__dev

    # Delete everything including raw data (DANGEROUS!)
    python scripts/cleanup_databricks_catalog.py --execute --include-raw
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview changes without executing (default)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform deletions",
    )
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help="Also delete raw schema (WARNING: deletes source data!)",
    )
    parser.add_argument(
        "--schema",
        help="Delete only a specific schema",
    )
    parser.add_argument(
        "--catalog",
        default="airport_inventory_dev",
        help="Target catalog (default: airport_inventory_dev)",
    )
    args = parser.parse_args()

    # --execute overrides --dry-run
    dry_run = not args.execute

    # Load environment variables from .env file
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded environment from {env_path}")

    print(f"\nConnecting to Databricks...")
    conn = get_connection()
    cursor = conn.cursor()

    print(f"Target catalog: {args.catalog}")
    print(f"Mode: {'DRY-RUN (no changes will be made)' if dry_run else 'EXECUTE (changes will be applied!)'}")

    if args.include_raw:
        print("\nWARNING: --include-raw is set. Raw source data will be deleted!")

    print("\n" + "=" * 60)

    # Get schemas to process
    if args.schema:
        # Delete specific schema
        schemas_to_delete = [args.schema]
        print(f"Targeting specific schema: {args.schema}")
    else:
        # Find all SQLMesh schemas
        all_schemas = list_schemas(cursor, args.catalog)
        schemas_to_delete = [
            s for s in all_schemas
            if is_sqlmesh_schema(s) and not is_protected_schema(s, args.include_raw)
        ]
        print(f"Found {len(schemas_to_delete)} SQLMesh schemas to clean up:")

    if not schemas_to_delete:
        print("\nNo schemas to delete.")
        cursor.close()
        conn.close()
        return

    # Show what will be deleted
    print("\nSchemas to delete:")
    for schema in sorted(schemas_to_delete):
        protected = is_protected_schema(schema, args.include_raw)
        if protected:
            print(f"  - {schema} [PROTECTED - will skip]")
        else:
            print(f"  - {schema}")

    # Confirmation for execute mode
    if not dry_run:
        print("\n" + "=" * 60)
        print("WARNING: This will permanently delete the above schemas!")
        print("=" * 60)
        response = input("\nType 'yes' to confirm deletion: ")
        if response.lower() != "yes":
            print("Aborted.")
            cursor.close()
            conn.close()
            return

    # Perform deletions
    print("\n" + "=" * 60)
    print("Processing deletions...")
    print("=" * 60 + "\n")

    success_count = 0
    error_count = 0

    for schema in sorted(schemas_to_delete):
        if is_protected_schema(schema, args.include_raw):
            print(f"  Skipping protected schema: {schema}")
            continue

        if drop_schema(cursor, args.catalog, schema, dry_run):
            success_count += 1
        else:
            error_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    if dry_run:
        print(f"Schemas that would be deleted: {success_count}")
        print("\nTo actually delete, run with --execute flag")
    else:
        print(f"Schemas deleted: {success_count}")
        print(f"Errors: {error_count}")

    # Remind about state cleanup
    if not dry_run and success_count > 0:
        print("\n" + "=" * 60)
        print("NEXT STEPS")
        print("=" * 60)
        print("After cleanup, you may also want to reset SQLMesh state:")
        print("  rm -f data/databricks_dev_state.duckdb")
        print("\nThen redeploy with:")
        print("  sqlmesh --gateway databricks_dev plan dev --no-prompts --auto-apply")

    cursor.close()
    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
