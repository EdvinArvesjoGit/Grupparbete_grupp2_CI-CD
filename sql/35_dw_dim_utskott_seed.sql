INSERT INTO dw.dim_utskott (utskott_kod, utskott_namn) VALUES
    ('AU', 'Arbetsmarknadsutskottet'),
    ('CU', 'Civilutskottet'),
    ('FiU', 'Finansutskottet'),
    ('FöU', 'Försvarsutskottet'),
    ('JuU', 'Justitieutskottet'),
    ('KU', 'Konstitutionsutskottet'),
    ('KrU', 'Kulturutskottet'),
    ('MJU', 'Miljö- och jordbruksutskottet'),
    ('NU', 'Näringsutskottet'),
    ('SfU', 'Socialförsäkringsutskottet'),
    ('SkU', 'Skatteutskottet'),
    ('SoU', 'Socialutskottet'),
    ('TU', 'Trafikutskottet'),
    ('UbU', 'Utbildningsutskottet'),
    ('UFöU', 'Sammansatt utrikes- och försvarsutskott'),
    ('UU', 'Utrikesutskottet')
ON CONFLICT (utskott_kod) DO NOTHING;
