"""Runtime settings, read from the environment once."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str
    write_token: str
    marts: Path
    environment: str
    cors_origins: tuple[str, ...] = ()
    schema: str = ""
    """A Postgres schema for the tables, so the API shares the one free Neon database with the other
    projects' tables; empty means the default search path."""

    @property
    def token_required(self) -> bool:
        return bool(self.write_token)


def normalize_database_url(url: str) -> str:
    """The connection string as a host hands it over (`postgres://` or `postgresql://`, which is what
    Neon and Vercel show) becomes the SQLAlchemy form with the psycopg driver named, so nobody has to
    edit a secret by hand to deploy; a URL that already names a driver is returned unchanged."""
    url = url.strip()
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def load_settings() -> Settings:
    root = Path(os.environ.get("DOORSTEP_ROOT", Path(__file__).resolve().parents[4]))
    return Settings(
        database_url=normalize_database_url(
            os.environ.get("DATABASE_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/doorstep")
        ),
        write_token=os.environ.get("DOORSTEP_WRITE_TOKEN", ""),
        marts=Path(os.environ.get("DOORSTEP_MARTS", root / "results" / "marts")),
        environment=os.environ.get("DOORSTEP_ENV", "development"),
        cors_origins=tuple(
            o.strip() for o in os.environ.get("DOORSTEP_CORS_ORIGINS", "*").split(",") if o.strip()
        ),
        schema=os.environ.get("DOORSTEP_DB_SCHEMA", "").strip(),
    )
