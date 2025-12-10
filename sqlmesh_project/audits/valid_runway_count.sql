AUDIT (
    name valid_runway_count,
);

-- Returns rows where runway_count is negative (should be >= 0)
SELECT *
FROM @this_model
WHERE runway_count < 0
