"""Integration tests — require a live Postgres.

Run locally with:

    pytest tests -m integration

Skipped automatically when no database is reachable, so `pytest` on a laptop
without Postgres running still passes. CI always has one, so these always run
there.

SCOPE NOTE: these currently assert idempotency of the *staging* layer and the
structural contract. The dw layer is not covered yet — dw.dim_ledamot is the
component most likely to have re-run bugs, because it is the only one that
reads its own previous output. Extend `test_dw_transform_is_idempotent` when
P3's transform passes.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import inspect, text

from src.common.db import check_connection, get_engine

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def engine():
    """Return an engine, or skip locally / fail in CI when there is no database.

    Skipping is right on a laptop with no Postgres running. It is WRONG in CI:
    pytest exits 0 when every test skips, so a misconfigured service container
    produces a green build that tested nothing. GitHub Actions always sets
    CI=true, so there we turn the skip into a hard failure.
    """
    if not check_connection():
        if os.environ.get("CI"):
            pytest.fail(
                "no database reachable in CI. The integration job must set "
                "PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD to match the "
                "postgres service container — these are what config.py reads."
            )
        pytest.skip("no database reachable locally — start Postgres to run these")
    return get_engine()


def test_required_schemas_exist(engine) -> None:
    """00_init.sql must have created all three schemas."""
    names = set(inspect(engine).get_schema_names())
    assert {"stg", "dw", "ops"} <= names


def test_load_log_is_writable(engine) -> None:
    """ops.load_log accepts a row and defaults status to RUNNING."""
    with engine.begin() as conn:
        load_id = conn.execute(
            text("""
                INSERT INTO ops.load_log (kalla, mallager, malltabell, korning_id)
                VALUES ('test', 'stg', 'testtabell', 'pytest')
                RETURNING load_id
            """)
        ).scalar_one()
        status = conn.execute(
            text("SELECT status FROM ops.load_log WHERE load_id = :i"), {"i": load_id}
        ).scalar_one()
        assert status == "RUNNING"
        conn.execute(text("DELETE FROM ops.load_log WHERE load_id = :i"), {"i": load_id})


def test_load_log_rejects_invalid_status(engine) -> None:
    """The CHECK constraint must reject a status outside the allowed set."""
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO ops.load_log (kalla, mallager, malltabell, status)
                    VALUES ('test', 'stg', 't', 'BANANA')
                """)
            )


def test_log_step_records_success(engine) -> None:
    """log_step writes an OK row with a row count and an end timestamp."""
    from src.common.pipeline import log_step

    with log_step(
        engine, kalla="pytest", mallager="stg", malltabell="t", korning_id="pytest-ok"
    ) as step:
        step.antal_rader = 42

    with engine.begin() as conn:
        row = (
            conn.execute(
                text("""
                SELECT status, antal_rader, avslutad IS NOT NULL AS klar
                FROM ops.load_log WHERE korning_id = 'pytest-ok'
            """)
            )
            .mappings()
            .one()
        )
        assert row["status"] == "OK"
        assert row["antal_rader"] == 42
        assert row["klar"]
        conn.execute(text("DELETE FROM ops.load_log WHERE korning_id = 'pytest-ok'"))


def test_log_step_records_failure_and_reraises(engine) -> None:
    """A failing step is logged as FAILED and the exception is not swallowed."""
    from src.common.pipeline import log_step

    with pytest.raises(ValueError):
        with log_step(
            engine, kalla="pytest", mallager="stg", malltabell="t", korning_id="pytest-fail"
        ):
            raise ValueError("boom")

    with engine.begin() as conn:
        row = (
            conn.execute(
                text("""
                SELECT status, meddelande FROM ops.load_log
                WHERE korning_id = 'pytest-fail'
            """)
            )
            .mappings()
            .one()
        )
        assert row["status"] == "FAILED"
        assert "boom" in row["meddelande"]
        conn.execute(text("DELETE FROM ops.load_log WHERE korning_id = 'pytest-fail'"))


EXPECTED_TABLES = {
    "stg": ("person", "person_uppdrag", "votering"),
    "dw": ("dim_ledamot",),
}


def test_expected_tables_exist(engine) -> None:
    """The committed DDL must actually create the tables we claim to test.

    Without this, every schema assertion below can pass vacuously: a test that
    iterates over tables finds nothing to complain about when the tables are
    missing, and reports success. A green build over an empty database is
    worse than a red one, because it manufactures confidence.
    """
    insp = inspect(engine)
    missing = []
    for schema, tables in EXPECTED_TABLES.items():
        present = set(insp.get_table_names(schema=schema))
        missing += [f"{schema}.{t}" for t in tables if t not in present]

    assert not missing, (
        "tables missing from the database — did the DDL in sql/ actually run? " + ", ".join(missing)
    )


def test_stg_columns_are_wide_enough(engine) -> None:
    """Guard against the varchar(10) class of bug.

    Any column holding an intressent_id or a valkrets must accept the real
    maximum lengths seen in the source: 13 chars for intressent_id, and at
    least 25 for valkrets ('Vastra Gotalands lans vastra').
    """
    minimum_widths = {"intressent_id": 13, "valkrets": 25}
    insp = inspect(engine)
    problems = []
    checked = 0

    for schema in ("stg", "dw"):
        for table in insp.get_table_names(schema=schema):
            for col in insp.get_columns(table, schema=schema):
                needed = minimum_widths.get(col["name"])
                if needed is None:
                    continue
                checked += 1
                length = getattr(col["type"], "length", None)
                if length is not None and length < needed:
                    problems.append(
                        f"{schema}.{table}.{col['name']} is varchar({length}), needs >= {needed}"
                    )

    assert checked > 0, (
        "no intressent_id or valkrets columns found anywhere in stg/dw — "
        "this test would have passed vacuously. Check that sql/ DDL ran."
    )
    assert not problems, "columns too narrow: " + "; ".join(problems)
