INSERT INTO dw.dim_parti (partikod, partinamn, mandat_2022) VALUES
    ('S', 'Socialdemokraterna', 107),
    ('SD', 'Sverigedemokraterna', 73),
    ('M', 'Moderaterna', 68),
    ('V', 'Vänsterpartiet', 24),
    ('C', 'Centerpartiet', 24),
    ('KD', 'Kristdemokraterna', 19),
    ('MP', 'Miljöpartiet', 18),
    ('L', 'Liberalerna', 16)
ON CONFLICT (partikod) DO UPDATE SET
    partinamn = EXCLUDED.partinamn,
    mandat_2022 = EXCLUDED.mandat_2022;
