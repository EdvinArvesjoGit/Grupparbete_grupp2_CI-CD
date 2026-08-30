-- Check whether one rm + beteckning + punkt combination
-- can contain more than one voting event (votering_id).
--
-- Purpose:
-- rm + beteckning + punkt is used as the unit for fetching and
-- detecting new voting groups during ingestion. This check verifies
-- that it must not be treated as a unique identifier for a voting event.

SELECT
    rm,
    beteckning,
    punkt,
    COUNT(DISTINCT votering_id) AS votering_id_count,
    COUNT(*) AS row_count
FROM stg.votering
GROUP BY
    rm,
    beteckning,
    punkt
HAVING COUNT(DISTINCT votering_id) > 1
ORDER BY
    rm,
    beteckning,
    punkt;


/*
Conclusion
----------
A single rm + beteckning + punkt combination can contain multiple
votering_id values.

Therefore:

- rm + beteckning + punkt can be used as an ingestion group.
- It must not be used as the unique identifier of a voting event.
- votering_id identifies the individual voting event.
- (votering_id, intressent_id) identifies an individual member's vote.
*/