AUDIT (
    name valid_longitude,
);

-- Returns rows where longitude is outside valid range (-180 to 180)
SELECT *
FROM @this_model
WHERE longitude IS NOT NULL
    AND (longitude < -180 OR longitude > 180)
