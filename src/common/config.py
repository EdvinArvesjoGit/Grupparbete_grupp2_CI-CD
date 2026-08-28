"""Central configuration. Reads .env once, exposes typed settings.

Every module imports settings from here rather than calling os.getenv itself,
so there is exactly one place where an env var name is spelled out.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Project root = two levels up from this file (src/common/config.py)
ROOT = Path(__file__).resolve().parents[2]

load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    """Runtime configuration, resolved from environment variables."""

    pghost: str = os.getenv("PGHOST", "localhost")
    pgport: int = int(os.getenv("PGPORT", "5432"))
    pgdatabase: str = os.getenv("PGDATABASE", "riksdag")
    pguser: str = os.getenv("PGUSER", "postgres")
    pgpassword: str = os.getenv("PGPASSWORD", "")
    data_dir: Path = field(default_factory=lambda: ROOT / os.getenv("DATA_DIR", "data/raw"))
    riksmoten: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            rm.strip()
            for rm in os.getenv("RIKSMOTEN", "2022/23,2023/24,2024/25,2025/26").split(",")
            if rm.strip()
        )
    )

    @property
    def sqlalchemy_url(self) -> str:
        """Connection URL for SQLAlchemy using the psycopg 3 driver."""
        return (
            f"postgresql+psycopg://{self.pguser}:{self.pgpassword}"
            f"@{self.pghost}:{self.pgport}/{self.pgdatabase}"
        )


settings = Settings()
