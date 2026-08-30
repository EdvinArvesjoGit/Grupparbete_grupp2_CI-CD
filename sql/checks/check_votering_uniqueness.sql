-- Validate whether (votering_id, intressent_id) can be used
-- as a unique key for an individual member's vote.


-- Check for duplicate votes by voting event and member.
-- If this query returns no rows, no duplicate combinations of
-- votering_id and intressent_id exist in the loaded dataset.
SELECT
    votering_id,
    intressent_id,
    COUNT(*) AS row_count
FROM stg.votering
GROUP BY votering_id, intressent_id
HAVING COUNT(*) > 1;


-- Compare the total number of rows with the number of unique
-- (votering_id, intressent_id) combinations.
-- If both values are equal, every row has a unique vote key.
SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT (votering_id, intressent_id)) AS unique_rows
FROM stg.votering;


/*
Findings
--------
The loaded voting data contains 909,145 rows.

The duplicate check returned no rows, meaning that no duplicate
(votering_id, intressent_id) combinations were found.

The total number of rows and the number of unique vote keys were
both 909,145.

Conclusion
----------
Within the loaded voting data for riksmöten 2022/23–2025/26,
the combination of votering_id and intressent_id uniquely identifies
an individual member's vote in a specific voting event.

This combination can therefore be used as the candidate unique key
for detecting duplicate or already loaded voting records during
incremental ingestion.
*/