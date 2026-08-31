CREATE TABLE IF NOT EXISTS stg.person_uppgift (
    kod TEXT,
    uppgift TEXT,
    typ TEXT,
    intressent_id TEXT,
    hangar_id TEXT,

    _laddad_tidpunkt TIMESTAMPTZ DEFAULT now(),
    _kalla TEXT,
    _korning_id TEXT
);