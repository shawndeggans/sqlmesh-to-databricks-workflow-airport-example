MODEL (
    name marts.dim_airports,
    kind FULL,
    cron '@daily',
    grain airport_id,
    audits (
        UNIQUE_VALUES(columns = (airport_id)),
        NOT_NULL(columns = (airport_id, airport_name))
    )
);

SELECT
    -- Primary key
    locid AS airport_id,

    -- Airport details
    airport_name,
    city,
    state_code,
    county,

    -- Location
    latitude,
    longitude,
    elevation_ft,

    -- Classification with human-readable labels
    CASE airport_category
        WHEN 'A' THEN 'Large Hub'
        WHEN 'B' THEN 'Medium Hub'
        WHEN 'C' THEN 'Small Hub'
        WHEN 'D' THEN 'Non-Hub'
        ELSE 'Other'
    END AS airport_classification,

    service_type,
    owner_type,
    operational_status,
    congestion_level,

    -- Metrics
    total_enplanements,
    aircraft_operations,

    -- Dates
    activation_date

FROM staging.stg_aviation_facilities
