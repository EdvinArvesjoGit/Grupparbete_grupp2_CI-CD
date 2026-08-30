-- Explore systemdatum to determine whether it can be used
-- for incremental voting data ingestion.


-- Check the range and number of distinct systemdatum values.
SELECT
    MIN(systemdatum) AS earliest_systemdatum,
    MAX(systemdatum) AS latest_systemdatum,
    COUNT(DISTINCT systemdatum) AS distinct_systemdatum
FROM stg.votering;


-- Check how systemdatum is distributed across voting events.
-- This helps determine whether multiple voting records or voting
-- events share the same system timestamp.
SELECT
    rm,
    beteckning,
    punkt,
    votering_id,
    systemdatum,
    COUNT(*) AS rows
FROM stg.votering
GROUP BY
    rm,
    beteckning,
    punkt,
    votering_id,
    systemdatum
ORDER BY systemdatum DESC
LIMIT 20;


-- Check whether a single votering_id has multiple systemdatum values.
-- If this query returns no rows, all member records belonging to the
-- same voting event share the same systemdatum in the loaded dataset.
SELECT
    votering_id,
    COUNT(DISTINCT systemdatum) AS systemdatum_count
FROM stg.votering
GROUP BY votering_id
HAVING COUNT(DISTINCT systemdatum) > 1;


/*
Findings
--------
The loaded voting data contains 909,145 rows but only 893 distinct
systemdatum values, ranging from 2022-10-26 16:04:44 to
2026-08-13 17:57:57.

The results show that systemdatum is shared by many voting records.
All 349 member records belonging to the same voting event have the
same systemdatum. Multiple voting events within the same beteckning
may also share the same systemdatum.

The third check returned no rows, confirming that no votering_id in
the loaded dataset has more than one systemdatum value.

Conclusion
----------
systemdatum appears to represent a system-level timestamp associated
with a voting event or a batch of voting data, rather than an
individual member vote timestamp.

However, these checks do not prove that systemdatum is updated when
existing voting data is later corrected or changed by the source.

Therefore, systemdatum should not currently be used as the sole
watermark for incremental ingestion.
*/

