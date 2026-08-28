"""Shared database access.

Import `get_engine()` rather than building your own connection string, so that
a change to the connection logic happens in one place for the whole team.

Typical use in an ingest or transform job:

    from src.common.db import get_engine

    with get_engine().begin() as conn:
        conn.execute(text("TRUNCATE stg.person"))

Typical use in a Streamlit report:

    import pandas as pd
    from src.common.db import get_engine

    df = pd.read_sql("SELECT * FROM dw.dim_parti", get_engine())
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import Engine, create_engine, text

from src.common.config import settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return a process-wide SQLAlchemy engine.

    Cached, so repeated calls reuse the same connection pool.
    """
    return create_engine(settings.sqlalchemy_url, pool_pre_ping=True, future=True)


def check_connection() -> bool:
    """Return True if the database answers. Used by the setup smoke check."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
