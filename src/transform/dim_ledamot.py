"""
Builds dw.dim_ledamot using SCD-2: preserves history instead of
overwriting when a person's data (e.g. party) changes.

Reads from stg.person (P1's raw data) and writes to dw.dim_ledamot.
"""

from datetime import date

from sqlalchemy import text

from src.common.db import get_engine


def load_dim_ledamot():
    """
    Main entry point. Walks through all current rows in stg.person and
    makes sure dw.dim_ledamot reflects them correctly, with history preserved.
    """
    engine = get_engine()

    # engine.begin() opens a transaction: if the whole block succeeds it is
    # committed automatically at the end; if anything raises, it rolls back.
    with engine.begin() as conn:
        # Fetch all people from the raw data, once.
        # .mappings() makes each row behave like a dict (person["parti"])
        # instead of an anonymous tuple.
        stg_personer = conn.execute(text("SELECT * FROM stg.person")).mappings().all()

        for raw_person in stg_personer:
            # Clean and validate BEFORE comparing or inserting anything.
            # This is the step that was previously missing — _rensa_person
            # existed but was never actually called.
            person = _rensa_person(raw_person)

            # Does an ACTIVE version of this person already exist in
            # dim_ledamot? (ar_aktuell = true means "current version")
            befintlig = (
                conn.execute(
                    text("""
                    SELECT * FROM dw.dim_ledamot
                    WHERE intressent_id = :intressent_id
                    AND ar_aktuell = true
                """),
                    {"intressent_id": person["intressent_id"]},
                )
                .mappings()
                .first()
            )

            if befintlig is None:
                # Case 1: brand new person, never existed in dim_ledamot.
                # Insert the first version of them.
                _infoga_ny_version(conn, person)

            elif _har_andrats(befintlig, person):
                # Case 2: person already exists, but something meaningful
                # (party, constituency) has changed since last run.
                # Close the old row and insert a new one.
                _stang_gammal_version(conn, befintlig["ledamot_nyckel"])
                _infoga_ny_version(conn, person)

            # Case 3 (otherwise): nothing changed, do nothing. Loop continues.


def _rensa_person(person):
    """
    Cleans and validates a person's raw data before it is used further.

    Raises ValueError if the person is missing intressent_id (we cannot
    work without it). "-" in the parti field means "no party" according
    to the source, not missing data, and is normalised to a clear value.
    """
    intressent_id = person.get("intressent_id")
    if not intressent_id:
        raise ValueError(f"Person is missing intressent_id: {person}")

    parti_ra = (person.get("parti") or "").strip()
    if parti_ra in ("", "-"):
        parti = "Partilös"
    else:
        parti = parti_ra

    return {
        "intressent_id": intressent_id.strip(),
        "fornamn": (person.get("tilltalsnamn") or "").strip(),
        "efternamn": (person.get("efternamn") or "").strip(),
        "parti": parti,
        "fodd_ar": _sakert_heltal(person.get("fodd_ar")),
        "valkrets": (person.get("valkrets") or "Okänd").strip(),
    }


def _sakert_heltal(varde):
    """
    Tries to convert a value to an integer. If that fails (e.g. empty
    string, unexpected text from the source), return None instead of
    crashing the whole row over a single bad field.
    """
    try:
        return int(varde)
    except (ValueError, TypeError):
        return None


def _har_andrats(befintlig, ny):
    """
    Decides whether a new SCD-2 version is needed.

    Only compares the fields that count as a "real" change for us.
    Note: fornamn/efternamn are NOT compared here — a spelling fix
    would not trigger a new history row with this logic.
    """
    return befintlig["parti"] != ny["parti"] or befintlig["valkrets"] != ny["valkrets"]


def _stang_gammal_version(conn, ledamot_nyckel):
    """
    Marks an existing row as no longer current.

    giltig_till is set to today's date, ar_aktuell to false.
    The row's data (party, constituency at that time) is NOT touched —
    that is the whole point, the history must remain unchanged.
    """
    conn.execute(
        text("""
            UPDATE dw.dim_ledamot
            SET giltig_till = :idag, ar_aktuell = false
            WHERE ledamot_nyckel = :ledamot_nyckel
        """),
        {"idag": date.today(), "ledamot_nyckel": ledamot_nyckel},
    )


def _infoga_ny_version(conn, person):
    """
    Inserts a new, current row for a person.

    giltig_till and ar_aktuell are NOT set explicitly here — they get
    their DEFAULT values from the table definition ('9999-12-31' and
    true), since this is by definition the latest version right now.
    """
    conn.execute(
        text("""
            INSERT INTO dw.dim_ledamot
                (intressent_id, fornamn, efternamn, parti, fodd_ar, valkrets, giltig_fran)
            VALUES
                (:intressent_id, :fornamn, :efternamn, :parti, :fodd_ar, :valkrets, :idag)
        """),
        {
            "intressent_id": person["intressent_id"],
            "fornamn": person["fornamn"],
            "efternamn": person["efternamn"],
            "parti": person["parti"],
            "fodd_ar": person["fodd_ar"],
            "valkrets": person["valkrets"],
            "idag": date.today(),
        },
    )
