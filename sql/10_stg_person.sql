CREATE TABLE IF NOT EXISTS stg.person (
    hangar_guid TEXT,
    sourceid TEXT,
    intressent_id TEXT,
    hangar_id TEXT,
    fodd_ar TEXT,
    kon TEXT,
    efternamn TEXT,
    tilltalsnamn TEXT,
    sorteringsnamn TEXT,
    iort TEXT,
    parti TEXT,
    valkrets TEXT,
    status TEXT,
    person_url_xml TEXT,
    bild_url_80 TEXT,
    bild_url_192 TEXT,
    bild_url_max TEXT,

    _laddad_tidpunkt TIMESTAMPTZ DEFAULT now(),
    _kalla TEXT,
    _korning_id TEXT
);