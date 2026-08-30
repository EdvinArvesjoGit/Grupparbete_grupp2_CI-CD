-- Validate the relationship between beteckning + punkt and votering_id.
--
-- A beteckning + punkt combination usually represents one voting item,
-- but it is not unique for a voting event. The same combination can have
-- more than one votering_id.


-- 1. Compare the number of voting items and voting events for each riksmöte.
SELECT
    rm,
    COUNT(
        DISTINCT CONCAT_WS('|', beteckning, punkt)
    ) AS bet_punkt_count,
    COUNT(DISTINCT votering_id) AS votering_id_count,
    COUNT(DISTINCT votering_id)
        - COUNT(DISTINCT CONCAT_WS('|', beteckning, punkt)) AS difference
FROM stg.votering
GROUP BY rm
ORDER BY rm;


-- 2. Find beteckning + punkt combinations associated with
-- more than one voting event.
SELECT
    rm,
    beteckning,
    punkt,
    COUNT(DISTINCT votering_id) AS votering_count
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


-- Conclusion:
-- A beteckning + punkt combination can be associated with
-- more than one votering_id.
-- Each votering_id represents an individual voting event.
-- Both the number of beteckning + punkt groups and votering_id values
-- per riksmöte are well below the API limit of 10,000 results.