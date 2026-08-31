-- Check whether one rm + beteckning + punkt combination
-- can contain more than one voting event (votering_id).
--
-- Purpose:
-- rm + beteckning + punkt represents a voting issue/group in the source data.
-- This check verifies whether the same issue can contain multiple
-- individual voting events.

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

- rm + beteckning + punkt represents an issue/group, not a single voting event.
- It must not be used as the unique identifier of a voting event.
- votering_id identifies the individual voting event.
- (votering_id, intressent_id) identifies an individual member's vote.
*/