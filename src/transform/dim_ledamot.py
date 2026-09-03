"""
Builds dw.dim_ledamot using SCD-2: preserves history instead of
overwriting when a person's data (e.g. party) changes.

Reads from stg.person (P1's raw data) and writes to dw.dim_ledamot.
"""

from datetime import date

from sqlalchemy import text

from src.common.db import get_engine

SCOPE_START = date(2022, 9, 1)


def load_dim_ledamot():
    """
    Main entry point. Walks through all current rows in stg.person and
    makes sure dw.dim_ledamot reflects them correctly, with history preserved.
    """
    engine = get_engine()

    with engine.begin() as conn:
        relevanta_id = _hamta_relevanta_id(conn)
        stg_personer = (
            conn.execute(
                text("""
                    SELECT DISTINCT ON (intressent_id) *
                    FROM stg.person
                    ORDER BY intressent_id, (valkrets is NULL OR valkrets = '') ASC, _laddad_tidpunkt DESC
                """)  # noqa: E501
            )
            .mappings()
            .all()
        )

        antal_nya = 0
        antal_uppdaterade = 0
        antal_overhoppade = 0

        for raw_person in stg_personer:
            if raw_person["intressent_id"] not in relevanta_id:
                antal_overhoppade += 1
                continue

            person = _rensa_person(raw_person)
            if person is None:
                antal_overhoppade += 1
                continue

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
                _infoga_ny_version(conn, person)
                antal_nya += 1
            elif _har_andrats(befintlig, person):
                _stang_gammal_version(conn, befintlig["ledamot_nyckel"])
                _infoga_ny_version(conn, person)
                antal_uppdaterade += 1

    print(f"Nya personer tillagda: {antal_nya}")
    print(f"Befintliga personer uppdaterade (SCD-2): {antal_uppdaterade}")
    print(f"Överhoppade (utanför scope eller saknar id): {antal_overhoppade}")


def _hamta_relevanta_id(conn):
    """
    Returns the set of intressent_id for people who have at least one uppdrag(mission)
    overlapping the project scope (riksmöte 2022/2023 onwards).

    tom_datum is stored as TEXT in stg (per the "no type cleverness in staging" rule),
    so we cast it explicity here in transform step. NULLIF(tom_datum, '')
    treats an empty string the same as NULL
    both mean "no end date set", i.e. the uppdrag is still ongoing.
    """
    rader = (
        conn.execute(
            text("""
            SELECT DISTINCT intressent_id
            FROM stg.person_uppdrag
            WHERE NULLIF(tom_datum, '') IS NULL
                OR NULLIF(tom_datum, '')::timestamptz >= :scope_start
        """),
            {"scope_start": SCOPE_START},
        )
        .mappings()
        .all()
    )

    return {rad["intressent_id"] for rad in rader}


def _rensa_person(person):
    """
    Cleans and validates a person's raw data before it is used further.

    Raises ValueError if the person is missing intressent_id (we cannot
    work without it). "-" in the parti field means "no party" according
    to the source, not missing data, and is normalised to a clear value.
    """
    intressent_id = person.get("intressent_id")
    if not intressent_id:
        return None

    parti_ra = (person.get("parti") or "").strip()
    if parti_ra in ("", "-"):
        parti = "Partilös"
    else:
        parti = parti_ra
    # stg.person uses the source field name 'tilltalsnamn'; we rename it to 'fornamn'
    # here per dw naming convention
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


if __name__ == "__main__":
    load_dim_ledamot()
