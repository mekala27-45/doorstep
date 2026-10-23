"""What the calculator persists across a request boundary: the checks, their scores and the audit
log. Every table is observed from an independently opened connection in the tests, because a test
that shares the application's session cannot see a missing commit (Day 5 of this series found
exactly that bug). No table has a column for a person: a check is a metro code, an income rounded to
the nearest thousand, a down payment share, a rate and a horizon, and the planted identifier scan
holds the log to that."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import Field, Session, SQLModel, create_engine, select


def now() -> datetime:
    return datetime.now(UTC)


class Check(SQLModel, table=True):
    __tablename__ = "checks"
    id: int | None = Field(default=None, primary_key=True)
    check_id: str = Field(index=True, unique=True)
    cbsa_code: str = Field(index=True)
    income: int
    """Annual household income rounded to the nearest thousand dollars."""
    down_share: float
    rate: float
    horizon_years: int
    quarter: str = Field(index=True)
    """The quarter of prices the check rests on."""
    median_home: float
    payment: float
    payment_share: float
    affordable_price: float
    affordable_share: float | None
    breakeven_years: float | None
    breakeven_low: float | None
    breakeven_high: float | None
    expected_next_payment_share: float
    """The payment share next quarter if prices and rates do not move: the carry forward expectation."""
    model_version: str
    note: str = ""
    created_at: datetime = Field(default_factory=now)


class CheckScore(SQLModel, table=True):
    __tablename__ = "check_scores"
    id: int | None = Field(default=None, primary_key=True)
    check_id: str = Field(foreign_key="checks.check_id", index=True, unique=True)
    scored_quarter: str
    realized_payment_share: float
    absolute_error: float
    """Realized payment share less the carry forward expectation, in absolute value."""
    price_moved: float
    rate_moved: float
    scored_at: datetime = Field(default_factory=now)


class AuditEntry(SQLModel, table=True):
    __tablename__ = "audit_log"
    id: int | None = Field(default=None, primary_key=True)
    at: datetime = Field(default_factory=now, index=True)
    actor: str
    action: str
    resource: str
    resource_id: str = ""
    detail: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


def schema_options(schema: str = "") -> dict[str, Any]:
    """With a schema, every table name the engine emits is qualified with it, so the tables live
    there whatever the connection's search path says (the hosted database's proxy drops a search
    path set through the startup options, which Day 13's first deploy found)."""
    if not schema:
        return {}
    return {"schema_translate_map": {None: schema}}


def make_async_engine(url: str, schema: str = "") -> AsyncEngine:
    engine = create_async_engine(url, pool_pre_ping=True)
    return engine.execution_options(**schema_options(schema)) if schema else engine


def make_engine(url: str, schema: str = "") -> Any:
    engine = create_engine(url, pool_pre_ping=True)
    return engine.execution_options(**schema_options(schema)) if schema else engine


def ensure_schema(url: str, schema: str) -> None:
    if not schema:
        return
    engine = create_engine(url, pool_pre_ping=True)
    with engine.begin() as connection:
        connection.execute(text(f'create schema if not exists "{schema}"'))
    engine.dispose()


def create_all(engine: Any) -> None:
    SQLModel.metadata.create_all(engine)


# The notes the demo recording, the checks and the load test write on their rows. The reset deletes
# these and nothing else: the demo queue's "demo queue" rows stay so the log is never empty.
RECORDING_NOTES: tuple[str, ...] = (
    "demo recording",
    "recorded session",
    "persistence check",
    "verification from a separate client",
    "load test",
)


def reset_notes(engine: Any, notes: tuple[str, ...] = RECORDING_NOTES) -> dict[str, int]:
    """Delete the checks the demo recording and the persistence checks made, by their stated notes,
    with their scores; the audit log is left alone, so the deletion itself stays on the record."""
    counts = {"checks": 0, "scores": 0}
    with Session(engine) as session:
        checks = session.exec(select(Check).where(Check.note.in_(notes))).all()  # type: ignore[attr-defined]
        for c in checks:
            for score in session.exec(select(CheckScore).where(CheckScore.check_id == c.check_id)).all():
                session.delete(score)
                counts["scores"] += 1
            session.delete(c)
            counts["checks"] += 1
        session.add(
            AuditEntry(
                actor="operator", action="reset", resource="check", detail={"notes": list(notes), **counts}
            )
        )
        session.commit()
    return counts
