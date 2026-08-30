-- Staging table for voting data from Riksdagens öppna data API.

CREATE TABLE IF NOT EXISTS stg.votering (
    hangar_id           BIGINT,          -- Source row identifier
    rm                  VARCHAR(10),     -- Riksmöte, e.g. 2025/26
    beteckning          VARCHAR(20),
    punkt               VARCHAR(20),
    punkttyp            VARCHAR(50),

    votering_id         UUID NOT NULL,   -- Voting event identifier
    intressent_id       VARCHAR(20) NOT NULL, -- Member identifier

    namn                VARCHAR(200),
    fornamn             VARCHAR(100),
    efternamn           VARCHAR(100),
    valkrets            VARCHAR(200),
    iort                VARCHAR(100),
    parti               VARCHAR(20),

    banknummer          VARCHAR(20),
    kon                 VARCHAR(20),
    fodd                SMALLINT,

    rost                VARCHAR(30),     -- Ja, Nej, Avstår, Frånvarande
    avser               VARCHAR(100),
    votering            VARCHAR(100),

    votering_url_xml    VARCHAR(500),
    dok_id              VARCHAR(50),
    systemdatum         TIMESTAMP,       -- Timestamp from source API

    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP

    CONSTRAINT uq_votering_member
        UNIQUE (votering_id, intressent_id)
);