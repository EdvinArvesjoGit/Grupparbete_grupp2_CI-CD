from __future__ import annotations

from sqlalchemy import text

from src.common.db import get_engine


FILTER_OPTIONS_SQL = text(
    """
    SELECT
        COALESCE((SELECT array_agg(DISTINCT rm ORDER BY rm DESC)
                  FROM dw.dim_votering WHERE rm IS NOT NULL), ARRAY[]::text[]) AS riksmoten,
        COALESCE((SELECT array_agg(DISTINCT parti ORDER BY parti)
                  FROM dw.dim_ledamot WHERE parti IS NOT NULL AND parti <> ''), ARRAY[]::text[]) AS partier,
        COALESCE((SELECT array_agg(DISTINCT valkrets ORDER BY valkrets)
                  FROM dw.dim_ledamot WHERE valkrets IS NOT NULL AND valkrets <> ''), ARRAY[]::text[]) AS valkretsar,
        COALESCE((SELECT array_agg(DISTINCT rostvarde ORDER BY rostvarde)
                  FROM dw.dim_rost), ARRAY[]::text[]) AS roster,
        COALESCE((SELECT array_agg(DISTINCT full_name ORDER BY full_name)
                  FROM (
                      SELECT CONCAT(fornamn, ' ', efternamn) AS full_name
                      FROM dw.dim_ledamot
                      WHERE fornamn IS NOT NULL OR efternamn IS NOT NULL
                  ) names), ARRAY[]::text[]) AS ledamoter,
        COALESCE((SELECT array_agg(DISTINCT beteckning ORDER BY beteckning)
                  FROM dw.dim_votering WHERE beteckning IS NOT NULL AND beteckning <> ''), ARRAY[]::text[]) AS beteckningar
    """
)

RESULTS_SQL = text(
    """
    SELECT
        v.rm AS riksmote,
        v.beteckning,
        v.punkt,
        v.avser,
        v.datum,
        CONCAT(l.fornamn, ' ', l.efternamn) AS ledamot,
        l.parti,
        l.valkrets,
        r.rostvarde AS rost,
        f.votering_id
    FROM dw.fakta_rost f
    JOIN dw.dim_ledamot l ON l.ledamot_nyckel = f.ledamot_nyckel
    JOIN dw.dim_votering v ON v.votering_nyckel = f.votering_nyckel
    JOIN dw.dim_rost r ON r.rost_nyckel = f.rost_nyckel
    WHERE (:riksmote = '' OR v.rm = :riksmote)
      AND (:beteckning = '' OR v.beteckning ILIKE :beteckning_pattern)
      AND (:punkt = '' OR v.punkt = :punkt)
      AND (:parti = '' OR l.parti = :parti)
      AND (:valkrets = '' OR l.valkrets = :valkrets)
      AND (:rost = '' OR r.rostvarde = :rost)
      AND (:ledamot = '' OR CONCAT(l.fornamn, ' ', l.efternamn) = :ledamot)
    ORDER BY v.datum DESC NULLS LAST, v.rm DESC, v.beteckning, v.punkt, ledamot
    LIMIT :limit
    """
)


SUMMARY_SQL = text(
    """
    SELECT r.rostvarde AS rost, COUNT(*) AS antal
    FROM dw.fakta_rost f
    JOIN dw.dim_ledamot l ON l.ledamot_nyckel = f.ledamot_nyckel
    JOIN dw.dim_votering v ON v.votering_nyckel = f.votering_nyckel
    JOIN dw.dim_rost r ON r.rost_nyckel = f.rost_nyckel
    WHERE (:riksmote = '' OR v.rm = :riksmote)
      AND (:beteckning = '' OR v.beteckning ILIKE :beteckning_pattern)
      AND (:punkt = '' OR v.punkt = :punkt)
      AND (:parti = '' OR l.parti = :parti)
      AND (:valkrets = '' OR l.valkrets = :valkrets)
      AND (:rost = '' OR r.rostvarde = :rost)
      AND (:ledamot = '' OR CONCAT(l.fornamn, ' ', l.efternamn) = :ledamot)
    GROUP BY r.rostvarde
    ORDER BY antal DESC
    """
)


def _params(filters: dict[str, str], limit: int = 500) -> dict[str, object]:
    beteckning = filters.get("beteckning", "").strip()
    return {
        "riksmote": filters.get("riksmote", ""),
        "beteckning": beteckning,
        "beteckning_pattern": f"%{beteckning}%",
        "punkt": filters.get("punkt", ""),
        "parti": filters.get("parti", ""),
        "valkrets": filters.get("valkrets", ""),
        "rost": filters.get("rost", ""),
        "ledamot": filters.get("ledamot", ""),
        "limit": limit,
    }


def get_filter_options() -> dict[str, list[str]]:
    """Return values available in the project's DW for report filters."""
    with get_engine().connect() as conn:
        row = conn.execute(FILTER_OPTIONS_SQL).mappings().one()
    return {key: list(value or []) for key, value in row.items()}


def get_voteringar(filters: dict[str, str], limit: int = 500):
    """Return voting rows matching the selected filters."""
    import pandas as pd

    with get_engine().connect() as conn:
        return pd.read_sql(RESULTS_SQL, conn, params=_params(filters, limit))


def get_summary(filters: dict[str, str]):
    """Return vote counts by vote value for the selected filters."""
    import pandas as pd

    with get_engine().connect() as conn:
        return pd.read_sql(SUMMARY_SQL, conn, params=_params(filters))
