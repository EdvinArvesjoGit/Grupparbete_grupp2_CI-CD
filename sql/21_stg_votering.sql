-- Staging table for voting data from Riksdagens öppna data API.
--
-- Source endpoint:
-- https://data.riksdagen.se/votering/{votering_id}
--
-- The table mirrors the fields in the XML response as closely as possible.
-- Most source fields are stored as VARCHAR in staging to avoid unnecessary
-- type conversion or loss of source information during ingestion.
--
-- One row represents one member's record in one voting event.

CREATE TABLE IF NOT EXISTS stg.votering (
    dok_id              VARCHAR(50),
    votering_id         UUID NOT NULL,   -- Voting event identifier

    punkt               VARCHAR(20),
    punkttyp            VARCHAR(50),

    namn                VARCHAR(200),
    intressent_id       VARCHAR(30) NOT NULL,   -- Member identifier

    parti               VARCHAR(20),
    valkrets            VARCHAR(200),
    valkretsnummer      VARCHAR(20),
    iort                VARCHAR(100),

    rost                VARCHAR(30),            -- Ja, Nej, Avstår, Frånvarande
    avser               VARCHAR(100),           -- e.g. sakfrågan
    votering            VARCHAR(100),           -- e.g. huvud

    banknummer          VARCHAR(20),
    fornamn             VARCHAR(100),
    efternamn           VARCHAR(100),
    kon                 VARCHAR(20),
    fodd                VARCHAR(10),

    rm                  VARCHAR(10),            -- Riksmöte, e.g. 2025/26
    beteckning          VARCHAR(20),

    kalla               VARCHAR(100),           -- XML field <källa>, e.g. RIM-vot

    datum               VARCHAR(30),            -- Source value, e.g. 2026-03-04 00:00:00
    systemdatum         VARCHAR(30),            -- Source system timestamp

    -- Audit / ingestion metadata
    _laddad_tidpunkt    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    _kalla              TEXT,                   -- API endpoint used to load the row
                                                -- e.g. https://data.riksdagen.se/votering/{votering_id}
    _korning_id         TEXT,

    CONSTRAINT uq_votering_member
        UNIQUE (votering_id, intressent_id)
);