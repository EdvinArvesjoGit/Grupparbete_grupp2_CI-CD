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



-- Explore datum to determine whether it contains an actual
-- voting time or only represents the voting date.


-- Check the range and number of distinct datum values.
SELECT
    MIN(datum) AS earliest_datum,
    MAX(datum) AS latest_datum,
    COUNT(DISTINCT datum) AS distinct_datum
FROM stg.votering;


-- Check the distribution of the time component in datum.
-- This helps determine whether the source provides an actual
-- voting time or normally stores the value at midnight.
SELECT
    datum::timestamp::time AS time_of_day,
    COUNT(*) AS row_count
FROM stg.votering
WHERE datum IS NOT NULL
GROUP BY datum::timestamp::time
ORDER BY row_count DESC;


-- Check whether any datum contains a time other than midnight.
SELECT
    COUNT(*) AS rows_not_midnight
FROM stg.votering
WHERE datum IS NOT NULL
  AND datum::timestamp::time <> TIME '00:00:00';


-- Show examples if non-midnight values exist.
SELECT
    votering_id,
    rm,
    beteckning,
    punkt,
    datum
FROM stg.votering
WHERE datum IS NOT NULL
  AND datum::timestamp::time <> TIME '00:00:00'
ORDER BY datum::timestamp
LIMIT 20;


-- Check voting-event distribution by date.
SELECT
    datum::timestamp::date AS voting_date,
    COUNT(DISTINCT votering_id) AS voting_events,
    COUNT(*) AS vote_rows
FROM stg.votering
WHERE datum IS NOT NULL
GROUP BY datum::timestamp::date
ORDER BY voting_date;


/*
Findings
--------
The loaded voting data contains 909,145 rows.

datum
-----
There are 165 distinct datum values, ranging from
2022-10-26 00:00:00 to 2026-08-13 00:00:00.

All 909,145 rows have a time component of 00:00:00, and no rows
contain a non-midnight time value.

Multiple voting events can share the same datum. For example,
2024-06-18 contains 36 distinct voting events and 12,564 member
voting records.

This indicates that datum represents the voting date in the loaded
dataset. Although the source provides the value in a timestamp-like
format, the time component does not contain an actual voting time.

systemdatum
-----------
There are 893 distinct systemdatum values, ranging from
2022-10-26 16:04:44 to 2026-08-13 17:57:57.

systemdatum is shared by many voting records. All 349 member records
belonging to the same voting event have the same systemdatum.
Multiple voting events within the same beteckning may also share
the same systemdatum.

The check for multiple systemdatum values per votering_id returned
no rows, confirming that no votering_id in the loaded dataset has
more than one systemdatum value.

Conclusion
----------
datum represents the voting date in the loaded dataset. The source
stores it with a time component, but all observed time values are
00:00:00, so it should not be interpreted as the actual voting time.

systemdatum appears to represent a system-level timestamp associated
with a voting event or a batch of voting data, rather than an
individual member vote timestamp.

However, these checks do not prove that systemdatum is updated when
existing voting data is later corrected or changed by the source.

Therefore, systemdatum should not currently be used as the sole
watermark for incremental ingestion.
*/

