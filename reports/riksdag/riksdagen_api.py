from fastapi import FastAPI
from sqlalchemy import text

import reports.riksdag.schemas as schemas
from src.common.db import get_engine

app = FastAPI()


@app.get("/riksdagen/mandat")
async def get_mandat():
    query = text("""
        SELECT
            partikod,
            partinamn,
            mandat_2022
        FROM dw.dim_parti
        ORDER BY mandat_2022 DESC
    """)

    engine = get_engine()

    with engine.connect() as conn:
        result = conn.execute(query)

        mandat = [dict(row._mapping) for row in result]

    return {"mandat": mandat}


@app.get("/riksdagen/ledamoter")
async def get_ledamoter(
    parti: schemas.Parti | None = None,
):
    query = text("""
    SELECT
        intressent_id,
        parti,
        kon,
        fodd_ar,
        valkrets
    FROM dw.dim_ledamot
    WHERE (
        CAST(:parti AS VARCHAR) IS NULL
        OR parti = CAST(:parti AS VARCHAR)
    )
    ORDER BY parti
    """)

    engine = get_engine()

    with engine.connect() as conn:
        result = conn.execute(
            query,
            {
                "parti": (parti.value if parti is not None else None),
            },
        )

        ledamoter = [dict(row._mapping) for row in result]

    return {
        "antal_ledamoter": len(ledamoter),
        "ledamoter": ledamoter,
    }


@app.get("/riksdagen/statistik")
async def get_statistik(
    parti: schemas.Parti | None = None,
):
    query = text("""
    SELECT
        COUNT(*) AS antal_ledamoter,
        COUNT(*) FILTER (
            WHERE kon = 'kvinna'
        ) AS antal_kvinnor,
        COUNT(*) FILTER (
            WHERE kon = 'man'
        ) AS antal_man,
        PERCENTILE_CONT(0.5)
        WITHIN GROUP (
            ORDER BY 2022 - fodd_ar
        ) AS medianalder
    FROM dw.dim_ledamot
    WHERE ar_aktuell = TRUE
    AND (CAST(:parti AS VARCHAR) IS NULL
    OR parti = CAST(:parti AS VARCHAR))
""")

    engine = get_engine()

    with engine.connect() as conn:
        result = conn.execute(
            query,
            {
                "parti": (parti.value if parti else None),
            },
        )

        row = result.fetchone()

    return {
        "antal_ledamoter": row.antal_ledamoter,
        "antal_kvinnor": row.antal_kvinnor,
        "antal_man": row.antal_man,
        "medianalder": row.medianalder,
    }


@app.get("/riksdagen/aldersfördelning")
async def get_aldersfördelning(
    parti: schemas.Parti | None = None,
):
    query = text("""
        SELECT
            CASE
                WHEN 2022 - fodd_ar < 30 THEN '20–29'
                WHEN 2022 - fodd_ar < 40 THEN '30–39'
                WHEN 2022 - fodd_ar < 50 THEN '40–49'
                WHEN 2022 - fodd_ar < 60 THEN '50–59'
                WHEN 2022 - fodd_ar < 70 THEN '60–69'
                ELSE '70+'
            END as aldersgrupp,
            COUNT(*) AS antal
        FROM dw.dim_ledamot
        WHERE ar_aktuell = TRUE
        AND (CAST(:parti AS VARCHAR) IS NULL
        OR parti = CAST(:parti AS VARCHAR)
        )
        AND fodd_ar IS NOT NULL
        GROUP BY aldersgrupp
        ORDER BY MIN(2022 - fodd_ar)
    """)

    engine = get_engine()

    with engine.connect() as conn:
        result = conn.execute(
            query,
            {"parti": parti.value if parti else None},
        )

        aldersgrupper = [dict(row._mapping) for row in result]

    return {"aldersfordelning": aldersgrupper}
