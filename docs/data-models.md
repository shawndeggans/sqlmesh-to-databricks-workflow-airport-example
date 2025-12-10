# Data Models

This document describes all data models in the Airport Inventory Service pipeline.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          RAW LAYER                                   │
│  ┌─────────────────────┐    ┌─────────────────────┐                 │
│  │ raw.aviation_       │    │ raw.runway_ends     │                 │
│  │ facilities          │    │                     │                 │
│  │ (500 records)       │    │ (1,264 records)     │                 │
│  └──────────┬──────────┘    └──────────┬──────────┘                 │
└─────────────┼──────────────────────────┼────────────────────────────┘
              │                          │
              ▼                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        STAGING LAYER                                 │
│  ┌─────────────────────┐    ┌─────────────────────┐                 │
│  │ stg_aviation_       │    │ stg_runway_ends     │                 │
│  │ facilities          │    │                     │                 │
│  │ - Data cleansing    │    │ - Deduplication     │                 │
│  │ - Type casting      │    │ - Type casting      │                 │
│  │ - Null handling     │    │ - Null handling     │                 │
│  └──────────┬──────────┘    └──────────┬──────────┘                 │
└─────────────┼──────────────────────────┼────────────────────────────┘
              │                          │
              ▼                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          MARTS LAYER                                 │
│  ┌─────────────────────┐    ┌─────────────────────┐                 │
│  │ dim_airports        │    │ dim_runways         │                 │
│  │ (500 records)       │    │ (1,230 records)     │                 │
│  └──────────┬──────────┘    └──────────┬──────────┘                 │
│             │                          │                             │
│             └────────────┬─────────────┘                             │
│                          ▼                                           │
│             ┌─────────────────────────┐                             │
│             │ fct_airport_metrics     │                             │
│             │ (500 records)           │                             │
│             └─────────────────────────┘                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Staging Models

### stg_aviation_facilities

**Source**: `raw.aviation_facilities`
**Grain**: `locid` (Airport Location ID)
**Schedule**: Daily

Cleanses and standardizes FAA aviation facility records.

| Column | Type | Description |
|--------|------|-------------|
| locid | STRING | Primary key - FAA Location Identifier |
| airport_name | STRING | Official airport name |
| city | STRING | City location |
| state_code | STRING | 2-letter state code |
| county | STRING | County name |
| latitude | DOUBLE | Latitude coordinate |
| longitude | DOUBLE | Longitude coordinate |
| elevation_ft | INTEGER | Field elevation in feet |
| airport_category | STRING | FAA category code (A/B/C/D) |
| service_type | STRING | Type of service offered |
| owner_type | STRING | Ownership classification |
| operational_status | STRING | Current operational status |
| congestion_level | STRING | Congestion indicator |
| total_enplanements | INTEGER | Annual passenger boardings |
| aircraft_operations | INTEGER | Annual aircraft movements |
| activation_date | DATE | Date airport became active |

**Audits Applied**:
- `UNIQUE_VALUES(locid)`
- `NOT_NULL(locid)`
- `valid_latitude` - Ensures latitude is between -90 and 90
- `valid_longitude` - Ensures longitude is between -180 and 180

---

### stg_runway_ends

**Source**: `raw.runway_ends`
**Grain**: `(locid, runway_id)`
**Schedule**: Daily

Deduplicates and cleanses runway physical characteristics.

| Column | Type | Description |
|--------|------|-------------|
| locid | STRING | Airport Location Identifier (FK) |
| runway_id | STRING | Runway designation (e.g., "09/27") |
| length_ft | INTEGER | Runway length in feet |
| width_ft | INTEGER | Runway width in feet |
| surface_type | STRING | Surface material code |
| pavement_classification | STRING | Pavement strength (PCN) |

**Audits Applied**:
- `NOT_NULL(locid, runway_id)`

**Note**: Source data may contain both ends of a runway as separate records. This model deduplicates by keeping the record with the longest length per runway.

---

## Mart Models

### dim_airports

**Source**: `staging.stg_aviation_facilities`
**Grain**: `airport_id`
**Schedule**: Daily

Dimension table containing airport master data with business-friendly transformations.

| Column | Type | Description |
|--------|------|-------------|
| airport_id | STRING | Primary key (from locid) |
| airport_name | STRING | Official airport name |
| city | STRING | City location |
| state_code | STRING | 2-letter state code |
| county | STRING | County name |
| latitude | DOUBLE | Latitude coordinate |
| longitude | DOUBLE | Longitude coordinate |
| elevation_ft | INTEGER | Field elevation in feet |
| airport_classification | STRING | Human-readable hub classification |
| service_type | STRING | Type of service offered |
| owner_type | STRING | Ownership classification |
| operational_status | STRING | Current operational status |
| congestion_level | STRING | Congestion indicator |
| total_enplanements | INTEGER | Annual passenger boardings |
| aircraft_operations | INTEGER | Annual aircraft movements |
| activation_date | DATE | Date airport became active |

**Airport Classification Mapping**:
| Code | Classification |
|------|----------------|
| A | Large Hub |
| B | Medium Hub |
| C | Small Hub |
| D | Non-Hub |
| Other | Other |

**Audits Applied**:
- `UNIQUE_VALUES(airport_id)`
- `NOT_NULL(airport_id, airport_name)`

---

### dim_runways

**Source**: `staging.stg_runway_ends`
**Grain**: `runway_key`
**Schedule**: Daily

Dimension table for runway physical characteristics with normalized surface descriptions.

| Column | Type | Description |
|--------|------|-------------|
| runway_key | STRING | Surrogate key (locid + runway_id) |
| airport_id | STRING | Foreign key to dim_airports |
| runway_id | STRING | Runway designation |
| length_ft | INTEGER | Runway length in feet |
| width_ft | INTEGER | Runway width in feet |
| surface_type | STRING | Surface material code |
| surface_description | STRING | Human-readable surface type |
| pavement_classification | STRING | Pavement strength (PCN) |

**Surface Type Mapping**:
| Code | Description |
|------|-------------|
| ASPH | Asphalt |
| CONC | Concrete |
| TURF | Turf/Grass |
| GRVL | Gravel |
| DIRT | Dirt |
| WATER | Water |

**Audits Applied**:
- `NOT_NULL(runway_key, airport_id)`

---

### fct_airport_metrics

**Source**: `marts.dim_airports`, `marts.dim_runways`
**Grain**: `airport_id`
**Schedule**: Daily

Fact table aggregating airport operational metrics and runway statistics.

| Column | Type | Description |
|--------|------|-------------|
| airport_id | STRING | Primary key (FK to dim_airports) |
| runway_count | INTEGER | Number of runways at airport |
| max_runway_length_ft | INTEGER | Longest runway in feet |
| total_runway_area_sqft | INTEGER | Total runway surface area |
| has_commercial_service | BOOLEAN | Whether airport has scheduled service |
| size_category | STRING | FAA-based size classification |

**Size Category Thresholds** (based on annual enplanements):
| Enplanements | Category |
|--------------|----------|
| >= 10,000,000 | Large Hub |
| >= 2,500,000 | Medium Hub |
| >= 500,000 | Small Hub |
| >= 10,000 | Non-Hub Primary |
| > 0 | Non-Hub Commercial |
| 0 | General Aviation |

**Audits Applied**:
- `UNIQUE_VALUES(airport_id)`
- `NOT_NULL(airport_id)`
- `valid_runway_count` - Ensures runway_count is non-negative

---

## Seed Models

### seeds.faa_regions

Reference data for FAA regional boundaries.

| Column | Type | Description |
|--------|------|-------------|
| region_code | STRING | FAA region code |
| region_name | STRING | Full region name |
| headquarters_city | STRING | Regional HQ location |

### seeds.airport_categories

Reference data for airport category definitions.

| Column | Type | Description |
|--------|------|-------------|
| category_code | STRING | Category code |
| category_name | STRING | Category description |
| min_enplanements | INTEGER | Minimum threshold |
| max_enplanements | INTEGER | Maximum threshold |

---

## Custom Audits

### valid_latitude
Validates that latitude values fall within valid geographic range (-90 to 90 degrees).

### valid_longitude
Validates that longitude values fall within valid geographic range (-180 to 180 degrees).

### valid_runway_count
Validates that runway counts are non-negative integers.

---

## Data Lineage

```
raw.aviation_facilities ──► stg_aviation_facilities ──► dim_airports ──┐
                                                                        ├──► fct_airport_metrics
raw.runway_ends ──────────► stg_runway_ends ─────────► dim_runways ────┘
```
