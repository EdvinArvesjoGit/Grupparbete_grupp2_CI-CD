CREATE TABLE IF NOT EXISTS stg.person_uppdrag (
    intressent_id TEXT,
    uppdrag_typ TEXT,
    uppdrag_organ TEXT,
    uppdrag_roll TEXT,
    uppdrag_roll_status TEXT,
    uppdrag_fran_datum TEXT,
    uppdrag_tom_datum TEXT,

    _laddad_tidpunkt TIMESTAMPTZ DEFAULT now(),
    _kalla TEXT,
    _korning_id TEXT
);