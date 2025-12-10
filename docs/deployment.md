# Deployment & Operations Guide

This guide covers deployment procedures, environment configuration, and operational tasks.

## Environment Configuration

### Gateways

The project supports two deployment targets configured in `config.yaml`:

| Gateway | Engine | Purpose |
|---------|--------|---------|
| `local` | DuckDB | Local development and testing |
| `databricks_dev` | Databricks | Cloud development environment |

### Environment Variables

For Databricks deployment, set these environment variables:

```bash
# Required for Databricks gateway
export DATABRICKS_HOST=your-workspace.cloud.databricks.com
export DATABRICKS_TOKEN=dapi_your_token_here
```

### Configuration File

The `config.yaml` uses Jinja templating for environment variables:

```yaml
gateways:
  local:
    connection:
      type: duckdb
      database: ../data/dev.duckdb
    state_connection:
      type: duckdb
      database: ../data/state.duckdb

  databricks_dev:
    connection:
      type: databricks
      server_hostname: "{{ env_var('DATABRICKS_HOST') }}"
      http_path: /sql/1.0/warehouses/5f2a600257bdb5b8
      access_token: "{{ env_var('DATABRICKS_TOKEN') }}"
      catalog: airport_inventory_dev
    state_connection:
      type: duckdb
      database: ../data/databricks_dev_state.duckdb

default_gateway: local
```

---

## Local Development

### Initial Setup

```bash
# 1. Install dependencies
pip install sqlmesh duckdb pandas

# 2. Download source data
python scripts/download_ntad_data.py

# 3. Load raw data to DuckDB
python scripts/load_raw_to_duckdb.py

# 4. Run SQLMesh plan
cd sqlmesh_project
sqlmesh plan dev --no-prompts --auto-apply
```

### Common Commands

```bash
# View plan without applying
sqlmesh plan dev

# Apply changes to dev environment
sqlmesh plan dev --no-prompts --auto-apply

# Run audits only
sqlmesh audit

# Query data
sqlmesh fetchdf "SELECT * FROM marts.dim_airports LIMIT 10"

# View model DAG
sqlmesh dag

# Run tests
sqlmesh test
```

---

## Databricks Deployment

### Prerequisites

1. **Databricks Workspace** with SQL Warehouse
2. **Catalog** named `airport_inventory_dev`
3. **Environment variables** set for authentication

### Warehouse Configuration

The project uses SQL Warehouse ID: `5f2a600257bdb5b8`

To use a different warehouse, update `http_path` in `config.yaml`:
```yaml
http_path: /sql/1.0/warehouses/YOUR_WAREHOUSE_ID
```

### Initial Deployment

```bash
# 1. Ensure raw data exists in Databricks
# (Run data loading script if needed - see below)

# 2. Deploy models
cd sqlmesh_project
sqlmesh --gateway databricks_dev plan dev --no-prompts --auto-apply
```

### Loading Raw Data to Databricks

If raw tables don't exist, use Python to load them:

```python
import os
import pandas as pd
from databricks import sql

# Connection setup
connection = sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path="/sql/1.0/warehouses/YOUR_WAREHOUSE_ID",
    access_token=os.environ["DATABRICKS_TOKEN"]
)

# Create schema
cursor = connection.cursor()
cursor.execute("CREATE SCHEMA IF NOT EXISTS airport_inventory_dev.raw")

# Load parquet files and insert data
# (See scripts/load_raw_to_databricks.py for full implementation)
```

### Databricks Schema Structure

After deployment, Databricks will contain:

```
airport_inventory_dev/
├── raw/                          # Source data
│   ├── aviation_facilities
│   └── runway_ends
├── sqlmesh__staging/             # Physical staging tables
│   ├── staging__stg_aviation_facilities__<version>
│   └── staging__stg_runway_ends__<version>
├── sqlmesh__marts/               # Physical mart tables
│   ├── marts__dim_airports__<version>
│   ├── marts__dim_runways__<version>
│   └── marts__fct_airport_metrics__<version>
├── sqlmesh__seeds/               # Physical seed tables
│   ├── seeds__airport_categories__<version>
│   └── seeds__faa_regions__<version>
├── staging__dev/                 # Virtual layer views (dev)
├── marts__dev/                   # Virtual layer views (dev)
└── seeds__dev/                   # Virtual layer views (dev)
```

---

## CI/CD Pipelines

### Pull Request Validation (ci.yml)

Runs on every PR to validate changes:

```yaml
# .github/workflows/ci.yml
- Validates SQLMesh models compile
- Runs audits
- Executes unit tests
```

### Deployment (deploy.yml)

Deploys to Databricks on merge to main:

```yaml
# .github/workflows/deploy.yml
- Deploys to databricks_dev gateway
- Requires DATABRICKS_HOST and DATABRICKS_TOKEN secrets
```

### GitHub Secrets Required

| Secret | Description |
|--------|-------------|
| `DATABRICKS_HOST` | Workspace hostname |
| `DATABRICKS_TOKEN` | Personal access token |

---

## Operational Procedures

### Daily Operations

Models are configured to run daily (`cron '@daily'`). For manual runs:

```bash
# Run all models
sqlmesh --gateway databricks_dev run

# Run specific model
sqlmesh --gateway databricks_dev run marts.dim_airports
```

### Schema Changes

When modifying model schemas:

1. Update model SQL file
2. Run `sqlmesh plan dev` to see change impact
3. Review breaking vs non-breaking changes
4. Apply with `--no-prompts --auto-apply`

SQLMesh automatically handles:
- Version management
- Backfilling
- Virtual layer updates

### Backfilling Data

```bash
# Backfill all models from start date
sqlmesh --gateway databricks_dev plan dev --start 2024-01-01

# Backfill specific model
sqlmesh --gateway databricks_dev plan dev --select-model marts.dim_airports
```

### Troubleshooting

#### Connection Issues

```bash
# Test Databricks connectivity
python -c "
from databricks import sql
import os
conn = sql.connect(
    server_hostname=os.environ['DATABRICKS_HOST'],
    http_path='/sql/1.0/warehouses/5f2a600257bdb5b8',
    access_token=os.environ['DATABRICKS_TOKEN']
)
cursor = conn.cursor()
cursor.execute('SELECT 1')
print('Connection successful:', cursor.fetchone())
"
```

#### Environment Variable Issues

Ensure `config.yaml` uses Jinja syntax:
```yaml
# Correct
server_hostname: "{{ env_var('DATABRICKS_HOST') }}"

# Incorrect (won't resolve)
server_hostname: ${DATABRICKS_HOST}
```

#### Warehouse Not Running

If deployment hangs, ensure the SQL Warehouse is running:
```bash
# Check warehouse status via Databricks UI or CLI
databricks clusters get --cluster-id 5f2a600257bdb5b8
```

---

## Monitoring

### Data Quality

Audits run automatically during `plan` and `run`:

- `valid_latitude`: Geographic coordinate validation
- `valid_longitude`: Geographic coordinate validation
- `valid_runway_count`: Business rule validation
- Built-in `UNIQUE_VALUES` and `NOT_NULL` checks

### Viewing Audit Results

```bash
# Run audits with verbose output
sqlmesh audit --verbose
```

### State Database

SQLMesh maintains state in DuckDB files:
- `data/state.duckdb` - Local gateway state
- `data/databricks_dev_state.duckdb` - Databricks gateway state

These track:
- Snapshot versions
- Interval completions
- Environment configurations

---

## Adding New Environments

To add a production gateway:

```yaml
# config.yaml
gateways:
  # ... existing gateways ...

  databricks_prod:
    connection:
      type: databricks
      server_hostname: "{{ env_var('DATABRICKS_PROD_HOST') }}"
      http_path: /sql/1.0/warehouses/PROD_WAREHOUSE_ID
      access_token: "{{ env_var('DATABRICKS_PROD_TOKEN') }}"
      catalog: airport_inventory_prod
    state_connection:
      type: duckdb
      database: ../data/databricks_prod_state.duckdb
```

Then deploy:
```bash
sqlmesh --gateway databricks_prod plan prod --no-prompts --auto-apply
```
