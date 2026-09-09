"""
Builds dw.fakta_rost from stg.votering.

Reads all six dimension tables once into in-memory lookup dicts, then
walks stg.votering (909k+ rows) resolving each row's foreign keys from
those dicts rather than querying the database per row a per row query
against 909k rows would mean millions of round trips.

No SCD-2 here: a vote is a historical fact, never revised after the fact.
A unique constraint on (votering_nyckel, ledamot_nyckel) makes re-runs
idempotent via ON CONFLICT DO NOTHING.
"""

from datetime import datetime

from sqlalchemy import text

from src.common.db import get_engine


def load_fakta_rost():
    """Main entry point. Loads all unprocessed rows from stg.votering into dw.fakta_rost."""
    engine = get_engine()

    with engine.begin() as conn:
        ledamot_lookup = _bygg_ledamot_lookup(conn)
        parti_lookup = _bygg_parti_lookup(conn)
        votering_lookup = _bygg_votering_lookup(conn)
        utskott_lookup = _bygg_utskott_lookup(conn)
        rost_lookup = _bygg_rost_lookup(conn)
        datum_lookup = _bygg_datum_lookup(conn)

        stg_roster = conn.execute(text("SELECT * FROM stg.votering")).mappings().all()

        rader_att_infoga = []
        antal_overhoppade = 0

        for rad in stg_roster:
            fakta_rad = _bygg_fakta_rad(
                rad,
                ledamot_lookup,
                parti_lookup,
                votering_lookup,
                utskott_lookup,
                rost_lookup,
                datum_lookup,
            )
            if fakta_rad is None:
                antal_overhoppade += 1
                continue
            rader_att_infoga.append(fakta_rad)

        antal_infogade = _infoga_fakta_rader(conn, rader_att_infoga)

    print(f"Rader inlästa från stg.votering: {len(stg_roster)}")
    print(f"Rader insatta/uppdaterade i fakta_rost: {antal_infogade}")
    print(f"Överhoppade (saknar obligatorisk koppling): {antal_overhoppade}")

    return antal_infogade


def _bygg_ledamot_lookup(conn):
    """intressent_id -> ledamot_nyckel, only for currently active dim_ledamot rows."""
    rader = (
        conn.execute(
            text("SELECT intressent_id, ledamot_nyckel FROM dw.dim_ledamot WHERE ar_aktuell = true")
        )
        .mappings()
        .all()
    )
    return {r["intressent_id"]: r["ledamot_nyckel"] for r in rader}


def _bygg_parti_lookup(conn):
    """partikod -> parti_nyckel."""
    rader = conn.execute(text("SELECT partikod, parti_nyckel FROM dw.dim_parti")).mappings().all()
    return {r["partikod"]: r["parti_nyckel"] for r in rader}


def _bygg_votering_lookup(conn):
    """votering_id (as string) -> votering_nyckel."""
    rader = (
        conn.execute(text("SELECT votering_id, votering_nyckel FROM dw.dim_votering"))
        .mappings()
        .all()
    )
    return {str(r["votering_id"]): r["votering_nyckel"] for r in rader}


def _bygg_utskott_lookup(conn):
    """utskott_kod -> utskott_nyckel."""
    rader = (
        conn.execute(text("SELECT utskott_kod, utskott_nyckel FROM dw.dim_utskott"))
        .mappings()
        .all()
    )
    return {r["utskott_kod"]: r["utskott_nyckel"] for r in rader}


def _bygg_rost_lookup(conn):
    """rostvarde -> rost_nyckel."""
    rader = conn.execute(text("SELECT rostvarde, rost_nyckel FROM dw.dim_rost")).mappings().all()
    return {r["rostvarde"]: r["rost_nyckel"] for r in rader}


def _bygg_datum_lookup(conn):
    """datum -> datum_nyckel."""
    rader = conn.execute(text("SELECT datum, datum_nyckel FROM dw.dim_datum")).mappings().all()
    return {r["datum"]: r["datum_nyckel"] for r in rader}


def _extrahera_utskottskod(beteckning):
    """
    Extracts the committee code from a beteckning like 'FiU22' -> 'FiU'.

    Strips trailing digits. Returns None if beteckning is missing or
    has no matching committee (e.g. an unrecognised or future code).
    """
    if not beteckning:
        return None
    kod = beteckning.rstrip("0123456789")
    return kod or None


def _bygg_fakta_rad(
    rad, ledamot_lookup, parti_lookup, votering_lookup, utskott_lookup, rost_lookup, datum_lookup
):
    """
    Resolves one stg.votering row into a fakta_rost row using the lookups.

    Returns None if a mandatory foreign key (ledamot, votering, rost) can't
    be resolved — these three are NOT NULL in fakta_rost, so a missing
    match makes the row unusable. parti/utskott/datum are optional
    (nullable columns), so a missed match there just leaves them NULL.
    """
    ledamot_nyckel = ledamot_lookup.get(rad["intressent_id"])
    votering_nyckel = votering_lookup.get(str(rad["votering_id"]))
    rost_nyckel = rost_lookup.get(rad["rost"])

    if ledamot_nyckel is None or votering_nyckel is None or rost_nyckel is None:
        return None

    parti_nyckel = parti_lookup.get(rad["parti"])

    utskottskod = _extrahera_utskottskod(rad.get("beteckning"))
    utskott_nyckel = utskott_lookup.get(utskottskod) if utskottskod else None

    datum_text = rad.get("datum")
    datum_nyckel = None
    if datum_text:
        datum_del = str(datum_text).split(" ")[0]
        datum_obj = datetime.strptime(datum_del, "%Y-%m-%d").date()
        datum_nyckel = datum_lookup.get(datum_obj)
    return {
        "ledamot_nyckel": ledamot_nyckel,
        "parti_nyckel": parti_nyckel,
        "votering_nyckel": votering_nyckel,
        "utskott_nyckel": utskott_nyckel,
        "rost_nyckel": rost_nyckel,
        "datum_nyckel": datum_nyckel,
        "votering_id": str(rad["votering_id"]),
    }


def _infoga_fakta_rader(conn, rader):
    """
    Bulk-inserts fakta_rost rows. ON CONFLICT DO NOTHING makes re-runs
    idempotent via the (votering_nyckel, ledamot_nyckel) unique constraint.
    """
    if not rader:
        return 0

    sql = text("""
        INSERT INTO dw.fakta_rost
            (ledamot_nyckel, parti_nyckel, votering_nyckel, utskott_nyckel,
            rost_nyckel, datum_nyckel, votering_id)
        VALUES
            (:ledamot_nyckel, :parti_nyckel, :votering_nyckel, :utskott_nyckel,
            :rost_nyckel, :datum_nyckel, :votering_id)
        ON CONFLICT (votering_nyckel, ledamot_nyckel) DO NOTHING
    """)

    result = conn.execute(sql, rader)
    return result.rowcount


def run(engine=None, korning_id=None):
    """Standard pipeline entry point. Returns rows written this run."""
    return load_fakta_rost()


if __name__ == "__main__":
    load_fakta_rost()
