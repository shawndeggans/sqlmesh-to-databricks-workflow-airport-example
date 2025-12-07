# Airport Inventory & Classification Service — Implementation Plan

---

## Implementation Progress

### Completed

**Phase 1: Environment Setup** ✅
- [x] **1.1** Created repository with project structure
- [x] ~~**1.2** Configure devbox.json~~ — **SKIPPED**: Using GitHub Codespaces instead of DevBox
- [x] **1.3** Created requirements.txt with sqlmesh[duckdb,databricks], pandas, pyarrow, httpx, pytest
- [x] **1.4** Created .env.example with Databricks credentials template
- [x] **1.5** Updated .gitignore with data/, *.duckdb, .sqlmesh/, etc.
- [x] **1.6** Initialized SQLMesh project with `sqlmesh init duckdb`

**Phase 2: Data Ingestion** ✅
- [x] **2.1-2.3** Created `scripts/download_ntad_data.py` — fetches from BTS ArcGIS API with pagination, saves to parquet
- [x] **2.4** Created `scripts/load_raw_to_duckdb.py` — loads parquet into raw schema
- [x] **2.5** Created `scripts/generate_mock_data.py` — generates 500 airports + ~1,264 runways for CI/offline testing
- [x] **2.6** Verified data loads: mock data successfully loaded to `raw.aviation_facilities` and `raw.runway_ends`

### In Progress

**Phase 3: SQLMesh Configuration** — Next up
- Need to update config.yaml with proper database paths
- Need to add Databricks gateway configurations
- Will require Databricks credentials to test connectivity

### Decisions Made

| Decision | Rationale |
|----------|-----------|
| Skip DevBox | Using GitHub Codespaces which has Python pre-installed; devbox adds unnecessary complexity |
| Mock data first | Faster iteration than downloading real data; proves the pipeline works without network dependency |
| ArcGIS JSON format | The BTS API returns JSON (not GeoJSON); adjusted download script accordingly |
| 500 mock airports | Enough to test all scenarios without being too large for quick iteration |

### Current State

```
airport-inventory-service/
├── .env.example              ✅ Created
├── .gitignore                ✅ Updated
├── requirements.txt          ✅ Created + installed
├── sqlmesh_project/
│   ├── config.yaml           ⚠️  Default config (needs Databricks gateways)
│   ├── models/
│   │   ├── staging/          📁 Empty (Phase 4)
│   │   └── marts/            📁 Empty (Phase 5)
│   ├── seeds/                📁 Empty (Phase 7)
│   ├── audits/               📁 Empty (Phase 6)
│   └── tests/                📁 Empty (Phase 6)
├── scripts/
│   ├── download_ntad_data.py ✅ Created
│   ├── load_raw_to_duckdb.py ✅ Created
│   └── generate_mock_data.py ✅ Created
├── data/                     🚫 Gitignored
│   ├── raw/*.parquet         ✅ Generated (mock)
│   └── dev.duckdb            ✅ Created with raw schema
├── tests/unit/               📁 Empty (Phase 8)
├── docs/                     📁 Empty (Phase 10)
└── .github/workflows/        📁 Empty (Phase 8-9)
```

### Quick Start (for resuming work)

```bash
# If data directory is missing (it's gitignored), regenerate:
python scripts/generate_mock_data.py
python scripts/load_raw_to_duckdb.py

# Verify SQLMesh is working:
cd sqlmesh_project
sqlmesh info

# Query the raw data:
python -c "import duckdb; print(duckdb.connect('data/dev.duckdb').execute('SELECT COUNT(*) FROM raw.aviation_facilities').fetchone())"
```

---

## Project Overview

**Objective**: Build a modern data pipeline using SQLMesh and DuckDB for local development, with CI/CD promotion to Databricks dev and production environments. This project serves as a learning reference for local-first data development patterns.

**Data Product**: Airport Inventory & Classification Service
- Combines NTAD Aviation Facilities data with runway information
- Normalizes airport details (location, categorization, runway stats, congestion levels, service class)
- Use cases: planning analysis, regional infrastructure reports, logistical planning

**Source Data**: Bureau of Transportation Statistics (BTS) National Transportation Atlas Database (NTAD)
- Aviation Facilities: ~20,000 airports/heliports, updated every 28 days
- Runway Ends Table: Runway-level detail with dimensions and surface types

---

## Architecture Decisions

### Why SQLMesh (Not dbt)

| Capability | Benefit for This Project |
|------------|-------------------------|
| Virtual environments | Instant environment creation via views, not full rebuilds |
| Plan/apply workflow | See exactly what will change before applying (like Terraform) |
| SQLGlot transpilation | Write DuckDB SQL locally, auto-converts to Spark SQL for Databricks |
| Built-in audits | Data quality checks without external tools |
| State tracking | Knows which models need rebuilding based on actual changes |

### Why DuckDB for Local Development

- Executes analytical SQL faster than most cloud warehouses for small-medium data
- Same SQL syntax works locally and in production (via transpilation)
- Zero cloud cost during development iteration
- Unit tests run in milliseconds, not minutes

### Why NOT Including (Yet)

| Excluded | Reason |
|----------|--------|
| Dagster | SQLMesh handles orchestration for transformation-only pipelines; add when needing sensors, schedules, or non-SQL assets |
| Apache Iceberg | Delta Lake on Databricks is sufficient; Iceberg adds complexity for multi-platform scenarios not present here |
| Data contracts | Add when external consumers need schema guarantees |
| LakeFS/Nessie | Git-like data branching is overkill for single-developer learning |

---

## Project Structure

```
airport-inventory-service/
├── devbox.json                    # DevBox environment configuration
├── devbox.lock
├── requirements.txt               # Python dependencies
├── .envrc                         # Local secrets (gitignored)
├── .env.example                   # Template for required environment variables
├── .gitignore
├── README.md
│
├── sqlmesh_project/               # SQLMesh transformation layer
│   ├── config.yaml                # Multi-gateway configuration
│   ├── models/
│   │   ├── _sources.yaml          # Source definitions (optional but recommended)
│   │   ├── staging/
│   │   │   ├── stg_aviation_facilities.sql
│   │   │   └── stg_runway_ends.sql
│   │   └── marts/
│   │       ├── dim_airports.sql
│   │       ├── dim_runways.sql
│   │       └── fct_airport_metrics.sql
│   ├── seeds/
│   │   ├── seed_faa_regions.csv
│   │   └── seed_airport_categories.csv
│   ├── audits/
│   │   └── custom_audits.sql
│   └── tests/
│       └── test_dim_airports.yaml
│
├── scripts/
│   ├── download_ntad_data.py      # Fetch source data from BTS
│   ├── load_raw_to_duckdb.py      # Load parquet into DuckDB raw schema
│   └── generate_mock_data.py      # Create synthetic data for offline testing
│
├── data/                          # Local data (gitignored)
│   ├── raw/                       # Downloaded source files
│   │   ├── aviation_facilities.parquet
│   │   └── runway_ends.parquet
│   ├── dev.duckdb                 # Local development database
│   └── state.duckdb               # SQLMesh state tracking
│
├── .github/
│   └── workflows/
│       ├── ci.yml                 # PR validation
│       └── deploy.yml             # Deployment to Databricks
│
├── tests/
│   └── unit/
│       └── test_download_script.py
│
└── docs/
    ├── SETUP.md                   # Developer onboarding instructions
    ├── WORKFLOW.md                # Day-to-day development process
    └── ARCHITECTURE.md            # Design decisions and rationale
```

---

## Data Model Design

### Layer 1: Raw (Bronze)
External data loaded as-is. Schema matches source.

**raw.aviation_facilities**
| Column | Type | Description |
|--------|------|-------------|
| LOCID | VARCHAR | FAA Location Identifier (primary key) |
| ARPT_NAME | VARCHAR | Airport name |
| CITY | VARCHAR | City |
| STATE_ABBR | VARCHAR | State code |
| COUNTY | VARCHAR | County name |
| LATITUDE | DOUBLE | Decimal degrees |
| LONGITUDE | DOUBLE | Decimal degrees |
| ELEVATION | INT | Field elevation in feet |
| ARPT_CAT | VARCHAR | FAA category code (A/B/C/D) |
| SERV_TYPE | VARCHAR | Service type |
| OWNER_TYPE | VARCHAR | Ownership type |
| OPERSTATUS | VARCHAR | Operational status |
| CONESSION | VARCHAR | Congestion level |
| TOT_ENP | BIGINT | Total annual enplanements |
| AC_OPNS | INT | Aircraft operations count |
| ACT_DATE | DATE | Activation date |

**raw.runway_ends**
| Column | Type | Description |
|--------|------|-------------|
| LOCID | VARCHAR | FAA Location Identifier (FK to aviation_facilities) |
| RUNWAY_ID | VARCHAR | Runway identifier (e.g., "09/27") |
| LENGTH | INT | Runway length in feet |
| WIDTH | INT | Runway width in feet |
| SURFACE | VARCHAR | Surface type code |
| PCN | VARCHAR | Pavement Classification Number |

### Layer 2: Staging (Silver)
Cleaned, typed, deduplicated. Business-agnostic transformations.

**staging.stg_aviation_facilities**
- Lowercase/normalize column names
- Cast to appropriate types
- Filter out invalid records (null LOCID)
- Trim whitespace from strings

**staging.stg_runway_ends**
- Join validation against facilities
- Parse runway dimensions
- Normalize surface type codes

### Layer 3: Marts (Gold)
Business-ready dimensions and facts.

**marts.dim_airports**
| Column | Type | Description |
|--------|------|-------------|
| airport_id | VARCHAR | Primary key (LOCID) |
| airport_name | VARCHAR | Full name |
| city | VARCHAR | City |
| state_code | VARCHAR | Two-letter state code |
| county | VARCHAR | County name |
| latitude | DOUBLE | Decimal degrees |
| longitude | DOUBLE | Decimal degrees |
| elevation_ft | INT | Field elevation |
| airport_classification | VARCHAR | Human-readable category |
| service_type | VARCHAR | Type of service |
| owner_type | VARCHAR | Public/private/military |
| operational_status | VARCHAR | Active/closed/etc |
| congestion_level | VARCHAR | FAA congestion designation |
| total_enplanements | BIGINT | Annual passenger count |
| aircraft_operations | INT | Annual operations |
| activation_date | DATE | When airport was activated |

**marts.dim_runways**
| Column | Type | Description |
|--------|------|-------------|
| runway_key | VARCHAR | Surrogate key (LOCID + RUNWAY_ID) |
| airport_id | VARCHAR | FK to dim_airports |
| runway_id | VARCHAR | Runway designation |
| length_ft | INT | Length in feet |
| width_ft | INT | Width in feet |
| surface_type | VARCHAR | Normalized surface description |
| pavement_strength | VARCHAR | PCN interpretation |

**marts.fct_airport_metrics**
| Column | Type | Description |
|--------|------|-------------|
| airport_id | VARCHAR | FK to dim_airports |
| runway_count | INT | Number of runways |
| max_runway_length_ft | INT | Longest runway |
| total_runway_area_sqft | BIGINT | Sum of runway areas |
| has_commercial_service | BOOLEAN | Based on enplanements > 0 |
| size_category | VARCHAR | Small/Medium/Large/Hub based on enplanements |

---

## Implementation Tasks

### Phase 1: Environment Setup ✅

- [x] **1.1** Create repository with project structure
- [x] ~~**1.2** Configure devbox.json~~ — SKIPPED (using GitHub Codespaces)
- [x] **1.3** Create requirements.txt with sqlmesh[duckdb,databricks], pandas, pyarrow, httpx, pytest
- [x] **1.4** Set up .env.example with Databricks credentials template
- [x] **1.5** Add comprehensive .gitignore (data/, *.duckdb, .envrc, __pycache__, .venv/)
- [x] **1.6** Initialize SQLMesh project: `cd sqlmesh_project && sqlmesh init duckdb`

### Phase 2: Data Ingestion ✅

- [x] **2.1** Write download_ntad_data.py to fetch Aviation Facilities from BTS ArcGIS API
- [x] **2.2** Write download_ntad_data.py to fetch Runway Ends data
- [x] **2.3** Convert to Parquet format for efficient local processing
- [x] **2.4** Write load_raw_to_duckdb.py to create raw schema and load parquet files
- [x] **2.5** Create generate_mock_data.py for offline/CI testing without network access
- [x] **2.6** Verify data loads correctly (tested with mock data)

### Phase 3: SQLMesh Configuration

- [ ] **3.1** Configure config.yaml with three gateways: local, databricks_dev, databricks_prod
- [ ] **3.2** Set default_gateway to local
- [ ] **3.3** Set model_defaults.dialect to duckdb
- [ ] **3.4** Verify local gateway works: `sqlmesh info`
- [ ] **3.5** Test Databricks connectivity: `sqlmesh --gateway databricks_dev info`

### Phase 4: Staging Models

- [ ] **4.1** Create stg_aviation_facilities.sql with FULL kind, grain on locid
- [ ] **4.2** Add UNIQUE_VALUES and NOT_NULL audits to stg_aviation_facilities
- [ ] **4.3** Create stg_runway_ends.sql with FULL kind
- [ ] **4.4** Run `sqlmesh plan dev` and verify change detection
- [ ] **4.5** Run `sqlmesh apply dev` to materialize locally
- [ ] **4.6** Validate with `sqlmesh fetchdf "SELECT * FROM staging__dev.stg_aviation_facilities LIMIT 10"`

### Phase 5: Mart Models

- [ ] **5.1** Create dim_airports.sql with category normalization logic
- [ ] **5.2** Create dim_runways.sql with surrogate key generation
- [ ] **5.3** Create fct_airport_metrics.sql with aggregations from runways
- [ ] **5.4** Add audits for referential integrity between facts and dimensions
- [ ] **5.5** Run full plan/apply cycle locally
- [ ] **5.6** Verify lineage: `sqlmesh dag`

### Phase 6: Data Quality

- [ ] **6.1** Create custom_audits.sql with project-specific validation rules
- [ ] **6.2** Add audit: latitude between -90 and 90
- [ ] **6.3** Add audit: longitude between -180 and 180
- [ ] **6.4** Add audit: runway_count > 0 for all airports in fct_airport_metrics
- [ ] **6.5** Create unit test YAML for dim_airports with fixture data
- [ ] **6.6** Run `sqlmesh test` and verify all pass

### Phase 7: Seed Data

- [ ] **7.1** Create seed_faa_regions.csv with FAA region codes and names
- [ ] **7.2** Create seed_airport_categories.csv with category code mappings
- [ ] **7.3** Reference seeds in models where needed
- [ ] **7.4** Verify seeds load: `sqlmesh plan dev` should show seed changes

### Phase 8: CI Pipeline

- [ ] **8.1** Create .github/workflows/ci.yml
- [ ] **8.2** Add step: checkout code
- [ ] **8.3** Add step: setup Python 3.11
- [ ] **8.4** Add step: install dependencies with uv
- [ ] **8.5** Add step: generate mock data (for CI without network)
- [ ] **8.6** Add step: load mock data to DuckDB
- [ ] **8.7** Add step: `sqlmesh plan dev --no-prompts --skip-tests` (validate SQL compiles)
- [ ] **8.8** Add step: `sqlmesh test` (run unit tests)
- [ ] **8.9** Add step: pytest tests/unit
- [ ] **8.10** Create PR and verify CI runs successfully

### Phase 9: Databricks Deployment

- [ ] **9.1** Create GitHub secrets: DATABRICKS_DEV_HOST, DATABRICKS_DEV_HTTP_PATH, DATABRICKS_DEV_TOKEN
- [ ] **9.2** Create GitHub secrets: DATABRICKS_PROD_HOST, DATABRICKS_PROD_HTTP_PATH, DATABRICKS_PROD_TOKEN
- [ ] **9.3** Create .github/workflows/deploy.yml with dev deployment on merge to main
- [ ] **9.4** Add manual workflow_dispatch for prod deployment
- [ ] **9.5** Test dev deployment: merge PR, verify models appear in Databricks dev catalog
- [ ] **9.6** Test prod deployment: trigger manual workflow, verify models in prod catalog
- [ ] **9.7** Verify SQLMesh virtual environments work in Databricks (check for __dev suffix views)

### Phase 10: Documentation

- [ ] **10.1** Write README.md with project overview and quickstart
- [ ] **10.2** Write docs/SETUP.md with detailed environment setup instructions
- [ ] **10.3** Write docs/WORKFLOW.md with day-to-day development process
- [ ] **10.4** Write docs/ARCHITECTURE.md with design decisions
- [ ] **10.5** Add inline comments to complex SQL transformations
- [ ] **10.6** Document SQLMesh commands cheat sheet in WORKFLOW.md

---

## SQLMesh Commands Reference

### Local Development
```bash
# Initialize project (first time only)
sqlmesh init duckdb

# See project info and gateway configuration
sqlmesh info

# Plan changes (shows what will happen, runs tests)
sqlmesh plan dev

# Apply changes to local DuckDB
sqlmesh apply dev

# Run unit tests only
sqlmesh test

# Query results
sqlmesh fetchdf "SELECT * FROM marts__dev.dim_airports LIMIT 10"

# View DAG/lineage
sqlmesh dag

# Render SQL for a specific model (see transpiled output)
sqlmesh render marts.dim_airports

# Diff between environments
sqlmesh diff dev prod
```

### Databricks Deployment
```bash
# Plan against Databricks dev (dry run)
sqlmesh --gateway databricks_dev plan dev

# Apply to Databricks dev
sqlmesh --gateway databricks_dev plan prod --auto-apply

# Apply to Databricks prod
sqlmesh --gateway databricks_prod plan prod --auto-apply
```

### Troubleshooting
```bash
# Validate SQL syntax without running
sqlmesh plan dev --no-prompts --skip-tests

# Force full refresh of a model
sqlmesh plan dev --restate-model marts.dim_airports

# Clear local state (nuclear option)
rm data/state.duckdb
```

---

## Environment Configuration

### devbox.json
```json
{
  "packages": [
    "python@3.11",
    "uv",
    "direnv"
  ],
  "shell": {
    "init_hook": [
      "uv venv --python 3.11 .venv",
      "source .venv/bin/activate",
      "uv pip install -r requirements.txt"
    ]
  },
  "env": {
    "PYTHONPATH": "."
  }
}
```

### requirements.txt
```
sqlmesh[duckdb,databricks]>=0.100.0
pandas>=2.0.0
pyarrow>=14.0.0
httpx>=0.25.0
pytest>=7.0.0
```

### .envrc
```bash
# Databricks Dev Workspace
export DATABRICKS_DEV_HOST="your-dev-workspace.cloud.databricks.com"
export DATABRICKS_DEV_HTTP_PATH="/sql/1.0/warehouses/your_warehouse_id"
export DATABRICKS_DEV_TOKEN="dapi_your_token_here"

# Databricks Prod Workspace
export DATABRICKS_PROD_HOST="your-prod-workspace.cloud.databricks.com"
export DATABRICKS_PROD_HTTP_PATH="/sql/1.0/warehouses/your_warehouse_id"
export DATABRICKS_PROD_TOKEN="dapi_your_token_here"
```

### .gitignore
```
# Python
__pycache__/
*.py[cod]
.venv/
venv/
*.egg-info/

# Data files
data/
*.duckdb
*.duckdb.wal
*.parquet

# Secrets
.envrc
.env

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db

# SQLMesh
.sqlmesh/
```

### SQLMesh config.yaml
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
      server_hostname: ${DATABRICKS_DEV_HOST}
      http_path: ${DATABRICKS_DEV_HTTP_PATH}
      access_token: ${DATABRICKS_DEV_TOKEN}
      catalog: airport_inventory_dev
    state_connection:
      type: databricks
      server_hostname: ${DATABRICKS_DEV_HOST}
      http_path: ${DATABRICKS_DEV_HTTP_PATH}
      access_token: ${DATABRICKS_DEV_TOKEN}
      catalog: airport_inventory_dev
      schema: _sqlmesh_state

  databricks_prod:
    connection:
      type: databricks
      server_hostname: ${DATABRICKS_PROD_HOST}
      http_path: ${DATABRICKS_PROD_HTTP_PATH}
      access_token: ${DATABRICKS_PROD_TOKEN}
      catalog: airport_inventory_prod
    state_connection:
      type: databricks
      server_hostname: ${DATABRICKS_PROD_HOST}
      http_path: ${DATABRICKS_PROD_HTTP_PATH}
      access_token: ${DATABRICKS_PROD_TOKEN}
      catalog: airport_inventory_prod
      schema: _sqlmesh_state

default_gateway: local

model_defaults:
  dialect: duckdb
  start: '2024-01-01'
```

---

## GitHub Actions Workflows

### .github/workflows/ci.yml
```yaml
name: CI

on:
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install uv
        run: pip install uv
      
      - name: Install dependencies
        run: uv pip install --system -r requirements.txt
      
      - name: Create data directories
        run: mkdir -p data/raw
      
      - name: Generate mock data
        run: python scripts/generate_mock_data.py
      
      - name: Load mock data to DuckDB
        run: python scripts/load_raw_to_duckdb.py
      
      - name: Validate SQLMesh models compile
        working-directory: sqlmesh_project
        run: sqlmesh plan dev --no-prompts --skip-tests
      
      - name: Run SQLMesh tests
        working-directory: sqlmesh_project
        run: sqlmesh test
      
      - name: Run Python unit tests
        run: pytest tests/unit -v
```

### .github/workflows/deploy.yml
```yaml
name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        default: 'dev'
        type: choice
        options:
          - dev
          - prod

env:
  DATABRICKS_DEV_HOST: ${{ secrets.DATABRICKS_DEV_HOST }}
  DATABRICKS_DEV_HTTP_PATH: ${{ secrets.DATABRICKS_DEV_HTTP_PATH }}
  DATABRICKS_DEV_TOKEN: ${{ secrets.DATABRICKS_DEV_TOKEN }}
  DATABRICKS_PROD_HOST: ${{ secrets.DATABRICKS_PROD_HOST }}
  DATABRICKS_PROD_HTTP_PATH: ${{ secrets.DATABRICKS_PROD_HTTP_PATH }}
  DATABRICKS_PROD_TOKEN: ${{ secrets.DATABRICKS_PROD_TOKEN }}

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment || 'dev' }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install uv
          uv pip install --system -r requirements.txt
      
      - name: Determine gateway
        id: gateway
        run: |
          ENV="${{ inputs.environment || 'dev' }}"
          echo "gateway=databricks_${ENV}" >> $GITHUB_OUTPUT
          echo "Deploying to databricks_${ENV}"
      
      - name: Deploy to Databricks
        working-directory: sqlmesh_project
        run: |
          sqlmesh --gateway ${{ steps.gateway.outputs.gateway }} plan prod --auto-apply
```

---

## Data Source URLs

### Aviation Facilities (Primary)
- **Catalog page**: https://catalog.data.gov/dataset/aviation-facilities1
- **GeoJSON API**: https://services.arcgis.com/xOi1kZaI0eWDREZC/arcgis/rest/services/Aviation_Facilities/FeatureServer/0/query?where=1%3D1&outFields=*&f=geojson
- **Data dictionary**: https://doi.org/10.21949/1529011
- **Update frequency**: Every 28 days

### Runway Ends Table
- **Catalog page**: https://catalog.data.gov/dataset/runway-ends-table
- **Update frequency**: Every 28 days

### Alternative: OurAirports (if BTS is unavailable)
- **URL**: https://ourairports.com/data/
- **Format**: CSV with UTF-8 encoding
- **Coverage**: Global airports (filter to US)

---

## Key Learning Objectives

By completing this project, you will understand:

1. **SQLMesh fundamentals**
   - MODEL declarations (kind, grain, audits)
   - Plan/apply workflow
   - Virtual environments and how they differ from dbt schemas
   - State tracking and incremental processing

2. **Local-first development**
   - DuckDB as a development database
   - SQL dialect transpilation via SQLGlot
   - Testing locally before cloud deployment

3. **CI/CD for data pipelines**
   - Validating SQL changes on PR
   - Automated deployment on merge
   - Environment promotion patterns

4. **Data modeling patterns**
   - Bronze/Silver/Gold medallion architecture
   - Dimension and fact table design
   - Data quality audits

---

## Success Criteria

The project is complete when:

- [ ] `sqlmesh plan dev` runs successfully with all models
- [ ] `sqlmesh test` passes all unit tests and audits
- [ ] CI pipeline validates PRs automatically
- [ ] Models deploy to Databricks dev on merge to main
- [ ] Models can be promoted to Databricks prod via manual trigger
- [ ] Documentation enables another developer to set up and contribute
- [ ] You can explain why each tool was chosen and how they interact

---

## Notes for Claude Code

When working on this project:

1. **Start with Phase 1-2** before writing any SQLMesh models. The environment must work first.

2. **Test incrementally**. After each model, run `sqlmesh plan dev` to verify it compiles.

3. **Use `sqlmesh fetchdf`** to validate data at each layer before moving to the next.

4. **Keep models simple**. This is a learning project. Avoid premature optimization.

5. **Document as you go**. Update WORKFLOW.md with commands that worked and gotchas you discovered.

6. **When stuck on SQLMesh**, check:
   - Is the dialect correct in config.yaml?
   - Is the gateway set correctly?
   - Does the raw data exist in DuckDB?
   - Run `sqlmesh render <model>` to see the generated SQL

7. **Databricks deployment issues** are usually:
   - Missing/wrong credentials in environment variables
   - Catalog doesn't exist (create it manually first)
   - Warehouse is stopped (ensure it's running)