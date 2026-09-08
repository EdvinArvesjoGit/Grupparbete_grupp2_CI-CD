"""
Builds dw.dim_votering from stg.votering.

stg.votering has one row per member per vote (349 rows per votering_id,
one per sitting ledamot). dim_votering needs one row per unique voting
event, so we deduplicate on votering_id, every duplicate row carries
identical votering level fields (rm, beteckning, punkt, avser, datum),
so any one of the 349 rows for a given votering_id works as the source.
"""

from sqlalchemy import text

from src.common.db import get_engine


def load_dim_votering():
    """
    Main entry point. Reads unique voting events from stg.votering and
    inserts any not already present in dw.dim_votering.

    Unlike dim_ledamot, this uses no SCD-2: a voting event is a historical
    fact that never changes after it happened, so there is nothing to
    version — just insert once, skip if already present.
    """
    engine = get_engine()

    with engine.begin() as conn:
        stg_voteringar = (
            conn.execute(
                text("""
                    SELECT DISTINCT ON (votering_id) *
                    FROM stg.votering
                    ORDER BY votering_id, _laddad_tidpunkt DESC
                """)
            )
            .mappings()
            .all()
        )

        antal_nya = 0
        antal_overhoppade = 0

        for raw_votering in stg_voteringar:
            votering = _rensa_votering(raw_votering)
            if votering is None:
                antal_overhoppade += 1
                continue

            befintlig = (
                conn.execute(
                    text("""
                    SELECT votering_nyckel FROM dw.dim_votering
                    WHERE votering_id = :votering_id
                """),
                    {"votering_id": votering["votering_id"]},
                )
                .mappings()
                .first()
            )

            if befintlig is None:
                _infoga_votering(conn, votering)
                antal_nya += 1

    print(f"Nya voteringar tillagda: {antal_nya}")
    print(f"Överhoppade (ogiltig data): {antal_overhoppade}")


def _rensa_votering(votering):
    """
    Cleans and validates one voting event before it is inserted.

    Returns None if votering_id is missing, or if datum cannot be parsed,
    both are conditions that make the row unusable for dw.dim_votering.

    datum arrives from stg as TEXT (e.g. '2023-05-10 00:00:00'), so we
    take only the date part here; the time component is not needed for
    a voting-event-level dimension.
    """
    votering_id = votering.get("votering_id")
    if not votering_id:
        return None

    datum_text = votering.get("datum")
    datum = None
    if datum_text:
        datum = str(datum_text).split(" ")[0]

    return {
        "votering_id": votering_id,
        "rm": (votering.get("rm") or "").strip(),
        "beteckning": (votering.get("beteckning") or "").strip(),
        "punkt": (votering.get("punkt") or "").strip(),
        "avser": (votering.get("avser") or "").strip(),
        "datum": datum,
    }


def _infoga_votering(conn, votering):
    """Inserts a new voting event row into dw.dim_votering."""
    conn.execute(
        text("""
            INSERT INTO dw.dim_votering
                (votering_id, rm, beteckning, punkt, avser, datum)
            VALUES
                (:votering_id, :rm, :beteckning, :punkt, :avser, :datum)
        """),
        {
            "votering_id": votering["votering_id"],
            "rm": votering["rm"],
            "beteckning": votering["beteckning"],
            "punkt": votering["punkt"],
            "avser": votering["avser"],
            "datum": votering["datum"],
        },
    )


if __name__ == "__main__":
    load_dim_votering()
