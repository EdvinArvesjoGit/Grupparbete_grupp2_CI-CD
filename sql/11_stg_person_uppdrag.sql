CREATE TABLE IF NOT EXISTS stg.person_uppdrag (
    organ_kod TEXT,
    roll_kod TEXT,
    ordningsnummer TEXT,
    status TEXT,
    typ TEXT,
    fran_datum TEXT,
    tom_datum TEXT,
    uppgift TEXT,
    intressent_id TEXT,
    hangar_id TEXT,
    sortering TEXT,
    organ_sortering TEXT,
    uppdrag_rollsortering TEXT,
    uppdrag_statussortering TEXT,

    _laddad_tidpunkt TIMESTAMPTZ DEFAULT now(),
    _kalla TEXT,
    _korning_id TEXT
);