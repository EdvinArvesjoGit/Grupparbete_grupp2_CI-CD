INSERT INTO dw.dim_datum (datum_nyckel, datum, ar, kvartal, manad, dag, veckodag)
SELECT
    TO_CHAR(d, 'YYYYMMDD')::INTEGER AS datum_nyckel,
    d AS datum,
    EXTRACT(YEAR FROM d)::INTEGER AS ar,
    EXTRACT(QUARTER FROM d)::INTEGER AS kvartal,
    EXTRACT(MONTH FROM d)::INTEGER AS manad,
    EXTRACT(DAY FROM d)::INTEGER AS dag,
    CASE EXTRACT(ISODOW FROM d)
        WHEN 1 THEN 'Måndag'
        WHEN 2 THEN 'Tisdag'
        WHEN 3 THEN 'Onsdag'
        WHEN 4 THEN 'Torsdag'
        WHEN 5 THEN 'Fredag'
        WHEN 6 THEN 'Lördag'
        WHEN 7 THEN 'Söndag'
    END AS veckodag
FROM generate_series('2022-09-01'::DATE, '2026-09-30'::DATE, '1 day'::INTERVAL) AS d
ON CONFLICT (datum_nyckel) DO NOTHING;
