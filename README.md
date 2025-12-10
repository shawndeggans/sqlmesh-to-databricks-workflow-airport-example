# Airport Inventory & Classification Service

A SQLMesh data pipeline that transforms FAA aviation facility data using the medallion architecture. Runs locally with DuckDB and deploys to Databricks.

## What This Project Does

Transforms raw FAA airport and runway data into analytics-ready dimensional models:

- **Input**: Aviation facilities (airports) and runway endpoints from the National Transportation Atlas Database
- **Output**: Cleaned dimensions (`dim_airports`, `dim_runways`) and aggregated facts (`fct_airport_metrics`)

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Raw      │────▶│   Staging   │────▶│    Marts    │
│  (Bronze)   │     │  (Silver)   │     │   (Gold)    │
└─────────────┘     └─────────────┘     └─────────────┘
 aviation_           stg_aviation_       dim_airports
 facilities          facilities          dim_runways
 runway_ends         stg_runway_ends     fct_airport_metrics
```

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) or pip

### Setup

```bash
# Clone and enter project
git clone https://github.com/shawndeggans/sqlmesh-to-databricks-workflow-airport-example.git
cd sqlmesh-to-databricks-workflow-airport-example

# Install dependencies
pip install -r requirements.txt

# Generate sample data and load to DuckDB
python scripts/generate_mock_data.py
python scripts/load_raw_to_duckdb.py
```

### Run Locally

```bash
cd sqlmesh_project

# Plan and apply changes
sqlmesh plan dev --no-prompts --auto-apply

# Query results
sqlmesh fetchdf "SELECT * FROM marts.dim_airports LIMIT 10"

# Run tests
sqlmesh test
```

### Deploy to Databricks

```bash
# Create .env file with your credentials
cp .env.example .env
# Edit .env with your DATABRICKS_HOST and DATABRICKS_TOKEN

# Load environment variables (IMPORTANT: must use set -a)
set -a && source .env && set +a

# Deploy
cd sqlmesh_project
sqlmesh --gateway databricks_dev plan dev --no-prompts --auto-apply
```

See [Databricks Catalog Management](docs/databricks-catalog-management.md) for detailed deployment instructions and troubleshooting.

## Project Structure

```
.
├── sqlmesh_project/
│   ├── config.yaml              # SQLMesh configuration (gateways, defaults)
│   ├── models/
│   │   ├── staging/             # Data cleansing models
│   │   │   ├── stg_aviation_facilities.sql
│   │   │   └── stg_runway_ends.sql
│   │   ├── marts/               # Business-ready models
│   │   │   ├── dim_airports.sql
│   │   │   ├── dim_runways.sql
│   │   │   └── fct_airport_metrics.sql
│   │   └── seeds/               # Reference data loaders
│   │       ├── seed_airport_categories.sql
│   │       └── seed_faa_regions.sql
│   ├── seeds/                   # CSV reference data
│   ├── audits/                  # Data quality checks
│   └── tests/                   # Unit tests
├── scripts/
│   ├── generate_mock_data.py    # Create sample data for CI
│   ├── download_ntad_data.py    # Fetch real FAA data
│   ├── load_raw_to_duckdb.py    # Load parquet to DuckDB
│   ├── inspect_databricks_catalog.py   # View Databricks catalog
│   └── cleanup_databricks_catalog.py   # Clean SQLMesh objects
├── data/                        # Local data files (gitignored)
├── docs/                        # Documentation
└── .github/workflows/           # CI/CD pipelines
```

## Data Models

| Model | Type | Description |
|-------|------|-------------|
| `stg_aviation_facilities` | Staging | Cleansed airport records with standardized fields |
| `stg_runway_ends` | Staging | Deduplicated runway data |
| `dim_airports` | Dimension | Airport master with classification and region |
| `dim_runways` | Dimension | Runway characteristics by airport |
| `fct_airport_metrics` | Fact | Aggregated runway statistics per airport |

## Gateways

| Gateway | Engine | Purpose |
|---------|--------|---------|
| `local` (default) | DuckDB | Local development |
| `databricks_dev` | Databricks | Cloud development |

## Documentation

- [START_HERE.md](START_HERE.md) - Detailed setup and usage guide
- [docs/data-models.md](docs/data-models.md) - Model specifications
- [docs/deployment.md](docs/deployment.md) - Deployment procedures
- [docs/databricks-catalog-management.md](docs/databricks-catalog-management.md) - Databricks catalog cleanup and troubleshooting

## License

MIT
