-- One row per voting event.
-- Stores the aggregated voting result returned by the voteringlista API.
CREATE TABLE IF NOT EXISTS stg.votering_summary (
    votering_id         UUID PRIMARY KEY,       -- Voting event identifier
    rm                  VARCHAR(10) NOT NULL,   -- Riksmöte, e.g. 2025/26

    ja                  INTEGER,                -- Number of Ja votes
    nej                 INTEGER,                -- Number of Nej votes
    franvarande         INTEGER,                -- Number of absent members
    avstar              INTEGER,                -- Number of abstentions

    -- Audit / ingestion metadata
    _laddad_tidpunkt    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    _kalla              TEXT,                   -- API endpoint used to load the row
    _korning_id         TEXT
);