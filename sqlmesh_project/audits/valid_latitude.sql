AUDIT (
    name valid_latitude,
);

-- Returns rows where latitude is outside valid range (-90 to 90)
SELECT *
FROM @this_model
WHERE latitude IS NOT NULL
    AND (latitude < -90 OR latitude > 90)
