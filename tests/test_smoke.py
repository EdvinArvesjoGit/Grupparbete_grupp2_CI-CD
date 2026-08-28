"""Smoke tests that run without a database.

These exist so CI has something to execute from day one — pytest exits with
code 5 (and fails the build) when it collects no tests at all.
"""

from src.common.config import settings


def test_settings_load() -> None:
    """Configuration resolves without raising."""
    assert settings.pgdatabase
    assert settings.pgport > 0


def test_riksmoten_scope_parsed() -> None:
    """Riksmoten parse into a non-empty tuple of 'YYYY/YY' strings."""
    assert len(settings.riksmoten) >= 1
    for rm in settings.riksmoten:
        assert "/" in rm


def test_sqlalchemy_url_uses_psycopg() -> None:
    """The engine URL targets the psycopg 3 driver, not psycopg2."""
    assert settings.sqlalchemy_url.startswith("postgresql+psycopg://")
