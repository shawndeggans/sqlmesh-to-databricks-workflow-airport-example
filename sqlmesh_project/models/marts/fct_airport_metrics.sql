MODEL (
    name marts.fct_airport_metrics,
    kind FULL,
    cron '@daily',
    grain airport_id,
    audits (
        UNIQUE_VALUES(columns = (airport_id)),
        NOT_NULL(columns = (airport_id)),
        valid_runway_count
    )
);

WITH runway_stats AS (
    SELECT
        airport_id,
        COUNT(*) AS runway_count,
        MAX(length_ft) AS max_runway_length_ft,
        SUM(length_ft * width_ft) AS total_runway_area_sqft
    FROM marts.dim_runways
    GROUP BY airport_id
)

SELECT
    a.airport_id,

    -- Runway metrics
    COALESCE(r.runway_count, 0) AS runway_count,
    r.max_runway_length_ft,
    r.total_runway_area_sqft,

    -- Service indicators
    CASE WHEN a.total_enplanements > 0 THEN TRUE ELSE FALSE END AS has_commercial_service,

    -- Size categorization based on FAA hub classification thresholds
    CASE
        WHEN a.total_enplanements >= 10000000 THEN 'Large Hub'
        WHEN a.total_enplanements >= 2500000 THEN 'Medium Hub'
        WHEN a.total_enplanements >= 500000 THEN 'Small Hub'
        WHEN a.total_enplanements >= 10000 THEN 'Non-Hub Primary'
        WHEN a.total_enplanements > 0 THEN 'Non-Hub Commercial'
        ELSE 'General Aviation'
    END AS size_category

FROM marts.dim_airports a
LEFT JOIN runway_stats r ON a.airport_id = r.airport_id
