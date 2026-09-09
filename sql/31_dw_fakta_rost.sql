CREATE TABLE IF NOT EXISTS dw.fakta_rost (
    fakta_rost_nyckel   BIGSERIAL PRIMARY KEY,
    ledamot_nyckel      INTEGER NOT NULL REFERENCES dw.dim_ledamot(ledamot_nyckel),
    parti_nyckel        INTEGER REFERENCES dw.dim_parti(parti_nyckel),
    votering_nyckel     INTEGER NOT NULL REFERENCES dw.dim_votering(votering_nyckel),
    utskott_nyckel      INTEGER REFERENCES dw.dim_utskott(utskott_nyckel),
    rost_nyckel         INTEGER NOT NULL REFERENCES dw.dim_rost(rost_nyckel),
    datum_nyckel        INTEGER REFERENCES dw.dim_datum(datum_nyckel),
    votering_id         UUID NOT NULL,
    CONSTRAINT fakta_rost_votering_ledamot_unique UNIQUE (votering_nyckel, ledamot_nyckel)
);
