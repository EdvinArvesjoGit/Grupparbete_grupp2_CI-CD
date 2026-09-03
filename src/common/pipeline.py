"""Pipeline run bookkeeping: run ids, logging setup and ops.load_log writes.

Every ingest and transform step wraps its work in `log_step`, which writes one
row to ops.load_log with timing, row count and outcome. That row is what makes
a failed nightly run diagnosable, and what gives the Streamlit reports an
honest "data as of" timestamp.

Usage inside a module's run() function:

    from src.common.pipeline import log_step

    def run(engine, korning_id=None) -> int:
        with log_step(engine, kalla="personlista", mallager="stg",
                      malltabell="person", korning_id=korning_id) as step:
            rows = _load_everything(engine)
            step.antal_rader = rows
            return rows

If the body raises, the row is marked FAILED with the exception text and the
exception is re-raised. Nothing is swallowed.
"""

from __future__ import annotations

import logging
import sys
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import Engine, text

LOGGER_NAME = "riksdag"

_INSERT = text("""
    INSERT INTO ops.load_log
        (kalla, mallager, malltabell, riksmote, korning_id, status)
    VALUES
        (:kalla, :mallager, :malltabell, :riksmote, :korning_id, 'RUNNING')
    RETURNING load_id
""")

_FINISH = text("""
    UPDATE ops.load_log
       SET avslutad    = now(),
           status      = :status,
           antal_rader = :antal_rader,
           meddelande  = :meddelande
     WHERE load_id     = :load_id
""")


def new_korning_id() -> str:
    """Return an id shared by every step in one pipeline run."""
    return uuid.uuid4().hex[:12]


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure one stdout handler for the whole pipeline. Safe to call twice."""
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s  %(levelname)-7s  %(name)s  %(message)s")
        )
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


@dataclass
class StepHandle:
    """Mutable handle yielded by log_step. Set `antal_rader` before exiting."""

    load_id: int
    antal_rader: int | None = None


@contextmanager
def log_step(
    engine: Engine,
    *,
    kalla: str,
    mallager: str,
    malltabell: str,
    riksmote: str | None = None,
    korning_id: str | None = None,
) -> Iterator[StepHandle]:
    """Record one load step in ops.load_log, including failures."""
    logger = setup_logging()
    label = f"{mallager}.{malltabell}"

    with engine.begin() as conn:
        load_id = conn.execute(
            _INSERT,
            {
                "kalla": kalla,
                "mallager": mallager,
                "malltabell": malltabell,
                "riksmote": riksmote,
                "korning_id": korning_id,
            },
        ).scalar_one()

    handle = StepHandle(load_id=load_id)
    logger.info("START  %s  (kalla=%s)", label, kalla)

    try:
        yield handle
    except Exception as exc:
        with engine.begin() as conn:
            conn.execute(
                _FINISH,
                {
                    "load_id": load_id,
                    "status": "FAILED",
                    "antal_rader": handle.antal_rader,
                    "meddelande": f"{type(exc).__name__}: {exc}"[:2000],
                },
            )
        logger.exception("FAILED %s", label)
        raise
    else:
        with engine.begin() as conn:
            conn.execute(
                _FINISH,
                {
                    "load_id": load_id,
                    "status": "OK",
                    "antal_rader": handle.antal_rader,
                    "meddelande": None,
                },
            )
        logger.info("OK     %s  rader=%s", label, handle.antal_rader)
