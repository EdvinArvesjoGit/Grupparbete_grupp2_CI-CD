-- Check for duplicate votes by voting event and member
SELECT
    votering_id,
    intressent_id,
    COUNT(*) AS row_count
FROM stg.votering
GROUP BY votering_id, intressent_id
HAVING COUNT(*) > 1;


-- Compare total rows with unique vote keys
SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT (votering_id, intressent_id)) AS unique_rows
FROM stg.votering;