# Databricks Catalog Management Guide

This document covers everything needed to deploy, manage, and clean up SQLMesh models in Databricks, including critical troubleshooting knowledge learned through implementation.

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [Understanding SQLMesh Naming in Databricks](#understanding-sqlmesh-naming-in-databricks)
3. [Deployment Commands](#deployment-commands)
4. [Catalog Inspection](#catalog-inspection)
5. [Cleanup Procedures](#cleanup-procedures)
6. [Troubleshooting](#troubleshooting)
7. [Configuration Reference](#configuration-reference)

---

## Environment Setup

### Critical: Loading Environment Variables

The `.env` file contains Databricks credentials but **must be loaded correctly** for SQLMesh to connect.

**WRONG - Does not export variables:**
```bash
source .env  # Variables are set but NOT exported to child processes
```

**CORRECT - Exports variables properly:**
```bash
set -a && source .env && set +a
```

The `set -a` command enables "auto-export" mode, which automatically exports any variable that is subsequently set or modified. This is essential because:
- SQLMesh runs as a child process
- Child processes only inherit exported environment variables
- Without `set -a`, the variables exist in the shell but SQLMesh can't see them

**Alternative for Python scripts:**
Python scripts using `python-dotenv` handle this automatically:
```python
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)  # Automatically loads and exports variables
```

### .env File Format

```bash
# Databricks Credentials
# Workspace: https://dbc-7dc1a76e-5a0e.cloud.databricks.com/

DATABRICKS_HOST=dbc-7dc1a76e-5a0e.cloud.databricks.com
DATABRICKS_TOKEN=dapi_your_token_here
```

**Important:** The `config.yaml` expects `DATABRICKS_HOST` and `DATABRICKS_TOKEN` (not `DATABRICKS_DEV_HOST`).

### Verifying Connection

Test Databricks connectivity before running SQLMesh:

```bash
set -a && source .env && set +a && python -c "
from databricks import sql
import os

conn = sql.connect(
    server_hostname=os.environ['DATABRICKS_HOST'],
    http_path='/sql/1.0/warehouses/5f2a600257bdb5b8',
    access_token=os.environ['DATABRICKS_TOKEN']
)
cursor = conn.cursor()
cursor.execute('SELECT 1 as test')
print('Connection successful:', cursor.fetchone())
cursor.close()
conn.close()
"
```

---

## Understanding SQLMesh Naming in Databricks

### Default SQLMesh Behavior (Before Configuration)

Without custom configuration, SQLMesh creates a complex schema structure:

```
airport_inventory_dev/
├── raw/                                    # Source data (manual)
├── sqlmesh__staging/                       # Physical tables
│   ├── staging__stg_aviation_facilities__3426020202
│   └── staging__stg_runway_ends__2675832369
├── sqlmesh__marts/                         # Physical tables
│   ├── marts__dim_airports__593710103
│   └── ...
├── staging__dev/                           # Virtual views
│   ├── stg_aviation_facilities
│   └── stg_runway_ends
├── marts__dev/                             # Virtual views
│   ├── dim_airports
│   └── ...
```

**Problems with default naming:**
1. `sqlmesh__` prefix on schemas - meaningless to data consumers
2. Hash suffixes on physical tables - confusing
3. `__dev` suffix on virtual schemas - creates schema proliferation
4. Duplicate representation of the same data

### Configured SQLMesh Behavior (After Clean Naming)

With `physical_schema_mapping` and `environment_suffix_target: table`:

```
airport_inventory_dev/
├── raw/
│   ├── aviation_facilities
│   └── runway_ends
├── staging/
│   ├── stg_aviation_facilities__dev        (virtual view)
│   ├── stg_runway_ends__dev                (virtual view)
│   ├── staging__stg_aviation_facilities__2861950214  (physical)
│   └── staging__stg_runway_ends__1187371852          (physical)
├── marts/
│   ├── dim_airports__dev                   (virtual view)
│   ├── dim_runways__dev                    (virtual view)
│   ├── fct_airport_metrics__dev            (virtual view)
│   ├── marts__dim_airports__1360708165     (physical)
│   └── ...
└── seeds/
    ├── airport_categories__dev             (virtual view)
    ├── faa_regions__dev                    (virtual view)
    └── ...
```

**Improvements:**
- No more `sqlmesh__` prefix on schemas
- All related tables in clean `staging`, `marts`, `seeds` schemas
- Environment suffix (`__dev`) on table names, not schema names
- Users query clean paths like `marts.dim_airports__dev`

### Why SQLMesh Creates Two Layers

SQLMesh maintains two layers for good reasons:

1. **Physical Tables (with hash suffixes):**
   - Contain the actual data
   - Hash identifies the specific version/snapshot
   - Enables zero-downtime deployments
   - Allows rollback to previous versions

2. **Virtual Views (with environment suffix):**
   - Point to the correct physical table for each environment
   - Allow `dev`, `staging`, `prod` to coexist
   - Enable instant environment switching
   - No data duplication between environments

**For querying data, always use the virtual views:**
```sql
SELECT * FROM marts.dim_airports__dev;  -- Use this
-- NOT: SELECT * FROM marts.marts__dim_airports__1360708165;
```

---

## Deployment Commands

### Full Deployment Workflow

```bash
# 1. Load environment variables (CRITICAL)
set -a && source .env && set +a

# 2. Navigate to SQLMesh project
cd sqlmesh_project

# 3. Deploy to Databricks dev environment
sqlmesh --gateway databricks_dev plan dev --no-prompts --auto-apply
```

### One-liner for Deployment

```bash
set -a && source .env && set +a && cd sqlmesh_project && sqlmesh --gateway databricks_dev plan dev --no-prompts --auto-apply
```

### Deployment Output Explained

Successful deployment shows:
```
[1/1] seeds.airport_categories__dev          [insert seed file]                 6.52s
[1/1] seeds.faa_regions__dev                 [insert seed file]                 3.32s
[1/1] staging.stg_aviation_facilities__dev   [full refresh, audits passed 4]    12.86s
[1/1] staging.stg_runway_ends__dev           [full refresh, audits passed 1]    4.95s
[1/1] marts.dim_airports__dev                [full refresh, audits passed 2]    10.78s
[1/1] marts.dim_runways__dev                 [full refresh, audits passed 1]    8.09s
[1/1] marts.fct_airport_metrics__dev         [full refresh, audits passed 3]    8.40s
Executing model batches ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100.0% • 7/7 • 0:00:56
```

**Key indicators:**
- `[insert seed file]` - Seed data loaded successfully
- `[full refresh, audits passed X]` - Model built and X audits passed
- Progress bar showing completion
- Time per model in seconds

### Deployment Hangs - Common Causes

If deployment shows the plan but doesn't progress:

1. **Warehouse not running** - Start it in Databricks UI
2. **Environment variables not exported** - Use `set -a && source .env && set +a`
3. **Network issues** - Test connection with Python script above
4. **Invalid credentials** - Verify token hasn't expired

---

## Catalog Inspection

### Using the Inspection Script

```bash
# Basic inspection
python scripts/inspect_databricks_catalog.py

# Verbose (shows all tables/views)
python scripts/inspect_databricks_catalog.py --verbose

# Different catalog
python scripts/inspect_databricks_catalog.py --catalog airport_inventory_prod
```

### Sample Output

```
============================================================
Found 6 schemas:

Source Data (raw):
----------------------------------------
  raw: 2 tables, 0 views
    - [TABLE] aviation_facilities
    - [TABLE] runway_ends

Other Schemas:
----------------------------------------
  marts: 6 tables, 0 views
    - [TABLE] dim_airports__dev
    - [TABLE] dim_runways__dev
    - [TABLE] fct_airport_metrics__dev
    - [TABLE] marts__dim_airports__1360708165
    - [TABLE] marts__dim_runways__2156208747
    - [TABLE] marts__fct_airport_metrics__1355960145
  seeds: 4 tables, 0 views
    - [TABLE] airport_categories__dev
    - [TABLE] faa_regions__dev
    - [TABLE] seeds__airport_categories__2328272730
    - [TABLE] seeds__faa_regions__631155794
  staging: 4 tables, 0 views
    - [TABLE] staging__stg_aviation_facilities__2861950214
    - [TABLE] staging__stg_runway_ends__1187371852
    - [TABLE] stg_aviation_facilities__dev
    - [TABLE] stg_runway_ends__dev
```

### Interpreting the Output

| Pattern | Type | Purpose |
|---------|------|---------|
| `dim_airports__dev` | Virtual view | Query this for dev data |
| `marts__dim_airports__1360708165` | Physical table | SQLMesh version tracking |
| `aviation_facilities` | Raw table | Source data |

---

## Cleanup Procedures

### When to Clean Up

- After major config changes (like adding `physical_schema_mapping`)
- To remove stale/unused snapshots
- To reset a broken deployment
- To remove example/test schemas

### Full Reset Procedure

```bash
# 1. Drop all SQLMesh schemas (preserves raw data)
python scripts/cleanup_databricks_catalog.py --execute

# 2. Delete local state
rm -f data/databricks_dev_state.duckdb

# 3. Redeploy
set -a && source .env && set +a && cd sqlmesh_project && sqlmesh --gateway databricks_dev plan dev --no-prompts --auto-apply
```

### Cleanup Script Options

```bash
# Preview what would be deleted (always do this first!)
python scripts/cleanup_databricks_catalog.py --dry-run

# Execute cleanup
python scripts/cleanup_databricks_catalog.py --execute

# Delete specific schema only
python scripts/cleanup_databricks_catalog.py --execute --schema sqlmesh_example__dev

# Include raw data in cleanup (DANGEROUS!)
python scripts/cleanup_databricks_catalog.py --execute --include-raw
```

### SQLMesh Native Cleanup Commands

```bash
# List environments
sqlmesh --gateway databricks_dev environments

# Remove virtual views for an environment (keeps physical tables)
sqlmesh --gateway databricks_dev invalidate_environment dev

# Clean up old/unused physical table snapshots
sqlmesh --gateway databricks_dev janitor
```

---

## Troubleshooting

### Issue: Deployment Hangs After Showing Plan

**Symptoms:**
- SQLMesh shows "Models needing backfill" but never progresses
- No error messages
- Process appears stuck

**Root Cause:**
Environment variables not exported to child processes.

**Solution:**
```bash
# Use set -a to auto-export variables
set -a && source .env && set +a && cd sqlmesh_project && sqlmesh --gateway databricks_dev plan dev --no-prompts --auto-apply
```

**Verification:**
```bash
set -a && source .env && set +a && echo "DATABRICKS_HOST=$DATABRICKS_HOST"
# Should print the actual hostname, not empty
```

### Issue: "DATABRICKS_HOST not set" Error

**Symptoms:**
```
Error: DATABRICKS_HOST and DATABRICKS_TOKEN must be set
```

**Causes:**
1. `.env` file missing or in wrong location
2. Variables not exported (see above)
3. Wrong variable names in `.env`

**Solution:**
Verify `.env` file exists and has correct format:
```bash
cat .env | head -5
# Should show:
# DATABRICKS_HOST=your-workspace.cloud.databricks.com
# DATABRICKS_TOKEN=dapi_xxx
```

### Issue: Warehouse Connection Timeout

**Symptoms:**
- Connection test hangs indefinitely
- "Warehouse not found" or timeout errors

**Solution:**
1. Log into Databricks UI
2. Go to SQL Warehouses
3. Ensure warehouse `5f2a600257bdb5b8` is running (or start it)
4. Wait for "Running" status before retrying

### Issue: Schema/Table Already Exists Errors

**Symptoms:**
```
Schema 'staging' already exists
```

**Solution:**
Run cleanup before redeploying:
```bash
python scripts/cleanup_databricks_catalog.py --execute
rm -f data/databricks_dev_state.duckdb
```

### Issue: Audits Failing

**Symptoms:**
```
[full refresh, audits failed]
```

**Solution:**
1. Check audit definitions in `sqlmesh_project/audits/`
2. Verify source data meets audit requirements
3. Run locally first to debug:
   ```bash
   cd sqlmesh_project && sqlmesh audit
   ```

---

## Configuration Reference

### config.yaml - Full Annotated Version

```yaml
# SQLMesh Configuration for Airport Inventory Service

gateways:
  # Local development gateway using DuckDB
  local:
    connection:
      type: duckdb
      database: ../data/dev.duckdb
    state_connection:
      type: duckdb
      database: ../data/state.duckdb

  # Databricks development gateway
  databricks_dev:
    connection:
      type: databricks
      # Uses Jinja templating - env_var() reads from environment
      server_hostname: "{{ env_var('DATABRICKS_HOST') }}"
      http_path: /sql/1.0/warehouses/5f2a600257bdb5b8
      access_token: "{{ env_var('DATABRICKS_TOKEN') }}"
      catalog: airport_inventory_dev
    # State stored locally in DuckDB (Databricks not optimized for this)
    state_connection:
      type: duckdb
      database: ../data/databricks_dev_state.duckdb

# Default to local development
default_gateway: local

model_defaults:
  dialect: duckdb  # SQLMesh transpiles to Spark SQL for Databricks
  start: '2024-01-01'

# CLEAN NAMING CONFIGURATION
# Map model schemas directly to physical schemas (removes sqlmesh__ prefix)
physical_schema_mapping:
  staging: staging
  marts: marts
  seeds: seeds

# Put environment suffix on table name, not schema name
# Without this: staging__dev schema with stg_aviation_facilities table
# With this: staging schema with stg_aviation_facilities__dev table
environment_suffix_target: table

# SQL linting rules
linter:
  enabled: true
  rules:
    - ambiguousorinvalidcolumn
    - invalidselectstarexpansion
    - noambiguousprojections
```

### Key Configuration Options Explained

#### physical_schema_mapping

Maps model schema names to physical schema names in Databricks.

```yaml
physical_schema_mapping:
  staging: staging  # staging.* models → staging schema (not sqlmesh__staging)
  marts: marts      # marts.* models → marts schema
  seeds: seeds      # seeds.* models → seeds schema
```

**Without this setting:** Physical tables go to `sqlmesh__staging`, `sqlmesh__marts`, etc.

**With this setting:** Physical tables go to `staging`, `marts`, `seeds` directly.

#### environment_suffix_target

Controls where the environment name (`dev`, `prod`) is appended.

| Value | Result |
|-------|--------|
| `schema` (default) | `staging__dev.stg_aviation_facilities` |
| `table` | `staging.stg_aviation_facilities__dev` |
| `catalog` | `airport_inventory_dev.staging.stg_aviation_facilities` |

We use `table` to keep schemas clean and put the environment identifier on table names.

---

## Quick Reference Commands

```bash
# Load env and deploy
set -a && source .env && set +a && cd sqlmesh_project && sqlmesh --gateway databricks_dev plan dev --no-prompts --auto-apply

# Inspect catalog
python scripts/inspect_databricks_catalog.py --verbose

# Cleanup (preview)
python scripts/cleanup_databricks_catalog.py --dry-run

# Cleanup (execute)
python scripts/cleanup_databricks_catalog.py --execute

# Full reset
python scripts/cleanup_databricks_catalog.py --execute && rm -f data/databricks_dev_state.duckdb

# Test connection
set -a && source .env && set +a && python -c "from databricks import sql; import os; c=sql.connect(server_hostname=os.environ['DATABRICKS_HOST'],http_path='/sql/1.0/warehouses/5f2a600257bdb5b8',access_token=os.environ['DATABRICKS_TOKEN']); print('OK')"
```

---

## Appendix: Expected Final Catalog Structure

After successful deployment with clean naming configuration:

```
airport_inventory_dev/
├── raw/                              # Source data (2 tables)
│   ├── aviation_facilities           # ~500 airports
│   └── runway_ends                   # ~1,264 runways
│
├── staging/                          # Staging layer (4 objects)
│   ├── stg_aviation_facilities__dev  # Virtual view (query this)
│   ├── stg_runway_ends__dev          # Virtual view (query this)
│   ├── staging__stg_aviation_facilities__<hash>  # Physical table
│   └── staging__stg_runway_ends__<hash>          # Physical table
│
├── marts/                            # Mart layer (6 objects)
│   ├── dim_airports__dev             # Virtual view (query this)
│   ├── dim_runways__dev              # Virtual view (query this)
│   ├── fct_airport_metrics__dev      # Virtual view (query this)
│   ├── marts__dim_airports__<hash>   # Physical table
│   ├── marts__dim_runways__<hash>    # Physical table
│   └── marts__fct_airport_metrics__<hash>  # Physical table
│
├── seeds/                            # Reference data (4 objects)
│   ├── airport_categories__dev       # Virtual view (query this)
│   ├── faa_regions__dev              # Virtual view (query this)
│   ├── seeds__airport_categories__<hash>  # Physical table
│   └── seeds__faa_regions__<hash>         # Physical table
│
├── default/                          # System schema (empty)
└── information_schema/               # System schema (28 tables)
```

**For data consumers:** Always query the `*__dev` views, not the hash-suffixed physical tables.
