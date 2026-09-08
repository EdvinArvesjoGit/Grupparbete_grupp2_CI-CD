INSERT INTO dw.dim_rost (rostvarde) VALUES
    ('Ja'),
    ('Nej'),
    ('Avstår'),
    ('Frånvarande')
ON CONFLICT (rostvarde) DO NOTHING;
