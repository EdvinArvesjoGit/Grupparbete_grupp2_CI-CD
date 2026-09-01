CREATE TABLE IF NOT EXISTS dw.dim_ledamot (
    ledamot_nyckel      SERIAL PRIMARY KEY,
    intressent_id       VARCHAR(10) NOT NULL,
    fornamn             VARCHAR(100) NOT NULL,
    efternamn           VARCHAR(100) NOT NULL,
    parti               VARCHAR(10),
    fodd_ar             INTEGER,
    valkrets            VARCHAR(100),
    giltig_fran         DATE NOT NULL,
    giltig_till         DATE NOT NULL DEFAULT '9999-12-31',
    ar_aktuell          BOOLEAN NOT NULL DEFAULT true
);

-- One row per party
CREATE TABLE IF NOT EXISTS dw.dim_parti (
    parti_nyckel    SERIAL PRIMARY KEY,
    partikod        VARCHAR(10) NOT NULL UNIQUE,  -- for example 'S', 'M', 'C'
    partinamn       VARCHAR(100)
);

-- One row per unique  voting round
CREATE TABLE IF NOT EXISTS dw.dim_votering (
    votering_nyckel SERIAL PRIMARY KEY,
    votering_id     VARCHAR(20) NOT NULL UNIQUE,
    rm              VARCHAR(10),        -- parliamentary session (riksmöte), example '2024/25'
    beteckning      VARCHAR(20),
    punkt           VARCHAR(10),        -- important: same votering_id can have multiple points
    avser           TEXT,               -- what the vote is about
    datum           DATE
);

CREATE TABLE IF NOT EXISTS dw.dim_utskott (
    utskott_nyckel  SERIAL PRIMARY KEY,
    utskott_kod     VARCHAR(20) NOT NULL UNIQUE,
    utskott_namn    VARCHAR(200)
);

-- The four possible voting values
CREATE TABLE IF NOT EXISTS dw.dim_rost (
    rost_nyckel     SERIAL PRIMARY KEY,
    rostvarde       VARCHAR(20) NOT NULL UNIQUE    -- 'Ja', 'Nej', 'Avstår', 'Frånvarande'
);

CREATE TABLE IF NOT EXISTS dw.dim_datum (
    datum_nyckel    INTEGER PRIMARY KEY,   -- format ÅÅÅÅMMDD, example 20240615
    datum           DATE NOT NULL UNIQUE,
    ar              INTEGER NOT NULL,
    kvartal         INTEGER NOT NULL,
    manad           INTEGER NOT NULL,
    dag             INTEGER NOT NULL,
    veckodag        VARCHAR(20) NOT NULL
);