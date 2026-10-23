"""The connection string a host hands over is usable as handed over."""

from doorstep_api.settings import load_settings, normalize_database_url


def test_a_plain_postgres_url_gets_the_driver_named() -> None:
    assert (
        normalize_database_url("postgresql://u:p@host.neon.tech/db?sslmode=require")
        == "postgresql+psycopg://u:p@host.neon.tech/db?sslmode=require"
    )
    assert normalize_database_url("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"


def test_a_url_that_names_a_driver_is_left_alone() -> None:
    url = "postgresql+psycopg://u:p@host/db"
    assert normalize_database_url(url) == url


def test_load_settings_normalizes_the_environment(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host/db")
    assert load_settings().database_url == "postgresql+psycopg://u:p@host/db"
