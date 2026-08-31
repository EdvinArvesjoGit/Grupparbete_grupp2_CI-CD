CREATE TABLE IF NOT EXISTS stg.person (
    tilltalsnamn TEXT,
    efternamn TEXT,
    iort TEXT,
    parti TEXT,
    intressent_id TEXT,
    kon TEXT,
    fodd_ar TEXT,
    valkrets TEXT,
    status TEXT,
    webbadress TEXT,
    epostadress TEXT,
    telefonnummer TEXT,
    titel TEXT,

    _laddad_tidpunkt TIMESTAMPTZ DEFAULT now(),
    _kalla TEXT,
    _korning_id TEXT
);