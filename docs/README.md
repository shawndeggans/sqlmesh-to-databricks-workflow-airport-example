# Airport Inventory Service - SQLMesh Project

A data pipeline project that transforms FAA aviation facility data using SQLMesh with dual deployment targets: local DuckDB for development and Databricks for cloud deployment.

## Overview

This project demonstrates a production-ready SQLMesh implementation featuring:

- **Medallion Architecture**: Raw -> Staging -> Marts data layers
- **Dual Gateway Configuration**: Local DuckDB and Databricks
- **Data Quality**: Custom audits for geographic and business rule validation
- **CI/CD**: GitHub Actions workflows for testing and deployment

## Quick Start

### Prerequisites

- Python 3.10+
- SQLMesh (`pip install sqlmesh`)
- Databricks workspace (for cloud deployment)

### Local Development

```bash
# Navigate to project
cd sqlmesh_project

# Run local pipeline
sqlmesh plan dev --no-prompts --auto-apply

# View data
sqlmesh fetchdf "SELECT * FROM marts.dim_airports LIMIT 10"
```

### Databricks Deployment

```bash
# Set environment variables
export DATABRICKS_HOST=your-workspace.cloud.databricks.com
export DATABRICKS_TOKEN=dapi_your_token

# Deploy to Databricks
sqlmesh --gateway databricks_dev plan dev --no-prompts --auto-apply
```

## Project Structure

```
sqlmesh_project/
├── config.yaml                 # Gateway and model configuration
├── models/
│   ├── staging/                # Data cleansing layer
│   │   ├── stg_aviation_facilities.sql
│   │   └── stg_runway_ends.sql
│   ├── marts/                  # Business-ready tables
│   │   ├── dim_airports.sql
│   │   ├── dim_runways.sql
│   │   └── fct_airport_metrics.sql
│   └── seeds/                  # Reference data loaders
│       ├── seed_faa_regions.sql
│       └── seed_airport_categories.sql
├── seeds/                      # CSV reference data
│   ├── seed_faa_regions.csv
│   └── seed_airport_categories.csv
├── audits/                     # Custom data quality checks
│   ├── valid_latitude.sql
│   ├── valid_longitude.sql
│   └── valid_runway_count.sql
└── tests/                      # Unit tests
    ├── test_dim_airports.yaml
    └── test_full_model.yaml

scripts/
├── download_ntad_data.py       # Download FAA source data
└── load_raw_to_duckdb.py       # Load raw data locally

.github/workflows/
├── ci.yml                      # PR validation
└── deploy.yml                  # Databricks deployment
```

## Data Sources

| Source | Description | Records |
|--------|-------------|---------|
| FAA Aviation Facilities | Airport master records | 500 |
| FAA Runway Ends | Runway physical characteristics | 1,264 |

Data is sourced from the National Transportation Atlas Database (NTAD).

## Documentation

- [Data Models](./data-models.md) - Detailed model specifications
- [Deployment Guide](./deployment.md) - Operations and deployment procedures
