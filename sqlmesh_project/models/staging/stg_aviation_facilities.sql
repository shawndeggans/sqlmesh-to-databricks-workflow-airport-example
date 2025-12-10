MODEL (
    name staging.stg_aviation_facilities,
    kind FULL,
    cron '@daily',
    grain locid,
    audits (
        UNIQUE_VALUES(columns = (locid)),
        NOT_NULL(columns = (locid)),
        valid_latitude,
        valid_longitude
    )
);

SELECT
    -- Primary key
    TRIM(LOCID) AS locid,

    -- Airport details
    TRIM(ARPT_NAME) AS airport_name,
    TRIM(CITY) AS city,
    TRIM(STATE_ABBR) AS state_code,
    TRIM(COUNTY) AS county,

    -- Location
    LATITUDE AS latitude,
    LONGITUDE AS longitude,
    CAST(ELEVATION AS INTEGER) AS elevation_ft,

    -- Classification
    TRIM(ARPT_CAT) AS airport_category,
    TRIM(SERV_TYPE) AS service_type,
    TRIM(OWNER_TYPE) AS owner_type,
    TRIM(OPERSTATUS) AS operational_status,
    TRIM(CONESSION) AS congestion_level,

    -- Metrics
    COALESCE(TOT_ENP, 0) AS total_enplanements,
    COALESCE(AC_OPNS, 0) AS aircraft_operations,

    -- Dates
    TRY_CAST(ACT_DATE AS DATE) AS activation_date

FROM raw.aviation_facilities
WHERE LOCID IS NOT NULL
    AND TRIM(LOCID) != ''
