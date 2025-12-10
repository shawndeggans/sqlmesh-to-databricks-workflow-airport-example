MODEL (
    name staging.stg_runway_ends,
    kind FULL,
    cron '@daily',
    grain (locid, runway_id),
    audits (
        NOT_NULL(columns = (locid, runway_id))
    )
);

-- Deduplicate runway records (source may have both ends as separate rows)
WITH deduplicated AS (
    SELECT
        TRIM(LOCID) AS locid,
        TRIM(RUNWAY_ID) AS runway_id,
        CAST(LENGTH AS INTEGER) AS length_ft,
        CAST(WIDTH AS INTEGER) AS width_ft,
        TRIM(SURFACE) AS surface_type,
        TRIM(PCN) AS pavement_classification,
        ROW_NUMBER() OVER (PARTITION BY TRIM(LOCID), TRIM(RUNWAY_ID) ORDER BY LENGTH DESC) AS rn
    FROM raw.runway_ends
    WHERE LOCID IS NOT NULL
        AND TRIM(LOCID) != ''
        AND RUNWAY_ID IS NOT NULL
)

SELECT
    locid,
    runway_id,
    length_ft,
    width_ft,
    surface_type,
    pavement_classification
FROM deduplicated
WHERE rn = 1
