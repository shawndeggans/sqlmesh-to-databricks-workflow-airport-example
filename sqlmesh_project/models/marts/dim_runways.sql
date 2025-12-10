MODEL (
    name marts.dim_runways,
    kind FULL,
    cron '@daily',
    grain runway_key,
    audits (
        NOT_NULL(columns = (runway_key, airport_id))
    )
);

SELECT
    -- Surrogate key
    locid || '_' || runway_id AS runway_key,

    -- Foreign key
    locid AS airport_id,

    -- Runway identification
    runway_id,

    -- Dimensions
    length_ft,
    width_ft,

    -- Surface with normalized descriptions
    surface_type,
    CASE surface_type
        WHEN 'ASPH' THEN 'Asphalt'
        WHEN 'CONC' THEN 'Concrete'
        WHEN 'TURF' THEN 'Turf/Grass'
        WHEN 'GRVL' THEN 'Gravel'
        WHEN 'DIRT' THEN 'Dirt'
        WHEN 'WATER' THEN 'Water'
        ELSE surface_type
    END AS surface_description,

    -- Pavement strength
    pavement_classification

FROM staging.stg_runway_ends
