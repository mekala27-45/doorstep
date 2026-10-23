"""The check log observed independently: every row the API says it wrote is read back through a second,
independently opened connection, the audit row precedes the response, and writes without the token are
refused. The calculator itself is held to the finance engine's arithmetic."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path

import httpx
import pytest
from doorstep_api.app import create_app
from doorstep_api.calculator import Calculator
from doorstep_api.db import AuditEntry, Check, CheckScore, create_all, ensure_schema, make_engine
from doorstep_api.settings import Settings
from doorstep_core.config import POLICY
from doorstep_core.statements import STATEMENT
from doorstep_finance.mortgage import affordable_price, payment_on_price
from sqlmodel import Session, select

pytestmark = pytest.mark.anyio

TOKEN = "test-token"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="module")
def schema_name() -> str:
    return f"t_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def settings(postgres_url: str, calculator_marts: Path, schema_name: str) -> Settings:
    ensure_schema(postgres_url, schema_name)
    engine = make_engine(postgres_url, schema_name)
    create_all(engine)
    engine.dispose()
    return Settings(
        database_url=postgres_url,
        write_token=TOKEN,
        marts=calculator_marts,
        environment="test",
        schema=schema_name,
    )


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


def independent(settings: Settings) -> Session:
    """A second engine, a second connection: what another process would see."""
    return Session(make_engine(settings.database_url, settings.schema))


def first_metro(settings: Settings) -> tuple[str, str, str]:
    calc = Calculator(settings.marts)
    code = calc.largest(1)[0]
    quarters = calc.quarters_of(code)
    return code, quarters[-1], quarters[-2]


async def test_health_carries_the_statement_and_the_marts(client: httpx.AsyncClient) -> None:
    r = await client.get("/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["database"] == "ok"
    assert body["model_version"].startswith("marts-") and body["metros"] > 0
    assert body["statement"] == STATEMENT and "Freddie Mac" in body["rate_attribution"]


async def test_writes_without_the_token_are_refused(client: httpx.AsyncClient, settings: Settings) -> None:
    code, _, _ = first_metro(settings)
    r = await client.post("/v1/checks", json={"cbsa_code": code, "income": 80_000})
    assert r.status_code == 401
    r = await client.post("/v1/score", json={})
    assert r.status_code == 401


async def test_check_is_committed(client: httpx.AsyncClient, settings: Settings) -> None:
    code, latest, _ = first_metro(settings)
    r = await client.post(
        "/v1/checks",
        json={
            "cbsa_code": code,
            "income": 81_499,
            "down_share": 0.10,
            "rate": 6.5,
            "horizon_years": 30,
            "note": "persistence check",
        },
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["income"] == 81_000, "the income is stored rounded to the nearest thousand"
    assert body["quarter"] == latest
    with independent(settings) as session:
        row = session.exec(select(Check).where(Check.check_id == body["check_id"])).one()
        assert row.income == 81_000 and row.cbsa_code == code and row.note == "persistence check"
        # the arithmetic is the finance engine's
        pay = payment_on_price(row.median_home, 6.5, 0.10, POLICY.loan_term_years)
        assert row.payment == pytest.approx(pay)
        assert row.payment_share == pytest.approx(12.0 * pay / 81_000)
        assert row.affordable_price == pytest.approx(
            affordable_price(81_000, 6.5, 0.10, POLICY.loan_term_years, POLICY.affordable_line)
        )
        assert row.expected_next_payment_share == pytest.approx(row.payment_share)
        assert (
            row.breakeven_years is not None
            and row.breakeven_low is not None
            and row.breakeven_high is not None
        )
        assert row.breakeven_low <= row.breakeven_years <= row.breakeven_high
    read = await client.get(f"/v1/checks/{body['check_id']}")
    assert read.status_code == 200 and read.json()["score"] is None


async def test_audit_precedes_response(client: httpx.AsyncClient, settings: Settings) -> None:
    code, _, _ = first_metro(settings)
    r = await client.post(
        "/v1/checks",
        json={"cbsa_code": code, "income": 60_000, "note": "persistence check"},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert r.status_code == 201
    body = r.json()
    served = datetime.fromisoformat(body["served_at"])
    with independent(settings) as session:
        entry = session.exec(select(AuditEntry).where(AuditEntry.resource_id == body["check_id"])).one()
        assert entry.action == "create" and entry.actor == "token"
        assert entry.at <= served


async def test_score_is_committed(client: httpx.AsyncClient, settings: Settings) -> None:
    code, latest, previous = first_metro(settings)
    r = await client.post(
        "/v1/checks",
        json={"cbsa_code": code, "income": 90_000, "quarter": previous, "note": "persistence check"},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert r.status_code == 201, r.text
    check_id = r.json()["check_id"]
    s = await client.post(
        "/v1/score", json={"note": "persistence check"}, headers={"Authorization": f"Bearer {TOKEN}"}
    )
    assert s.status_code == 200, s.text
    assert s.json()["scored"] >= 1
    with independent(settings) as session:
        score = session.exec(select(CheckScore).where(CheckScore.check_id == check_id)).one()
        assert score.scored_quarter == latest
        assert score.absolute_error >= 0.0
        check = session.exec(select(Check).where(Check.check_id == check_id)).one()
        assert score.absolute_error == pytest.approx(
            abs(score.realized_payment_share - check.expected_next_payment_share)
        )
    read = await client.get(f"/v1/checks/{check_id}")
    assert read.json()["score"]["scored_quarter"] == latest
    card = await client.get("/v1/scorecard")
    assert card.json()["scored"] >= 1


async def test_unknown_metro_and_quarter_are_404(client: httpx.AsyncClient, settings: Settings) -> None:
    r = await client.post(
        "/v1/checks",
        json={"cbsa_code": "99999", "income": 50_000},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert r.status_code == 404
    code, _, _ = first_metro(settings)
    r = await client.post(
        "/v1/checks",
        json={"cbsa_code": code, "income": 50_000, "quarter": "1999Q1"},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert r.status_code == 404
    r = await client.post(
        "/v1/checks",
        json={"cbsa_code": code, "income": 50_000, "note": "Name: Jane"},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert r.status_code == 422


async def test_curve_and_metros(client: httpx.AsyncClient, settings: Settings) -> None:
    code, _, _ = first_metro(settings)
    r = await client.get("/v1/curve", params={"cbsa_code": code, "income": 75_000, "horizon_years": 10})
    assert r.status_code == 200
    body = r.json()
    assert len(body["points"]) == 10 and body["payment_share"] > 0
    m = await client.get("/v1/metros")
    assert m.status_code == 200 and m.json()["metros"][0]["cbsa_code"] == code


async def test_every_route_carries_the_statement(client: httpx.AsyncClient, settings: Settings) -> None:
    code, _, _ = first_metro(settings)
    for path in (
        "/v1/health",
        "/v1/metros",
        "/v1/checks",
        "/v1/scorecard",
        "/v1/audit",
        f"/v1/curve?cbsa_code={code}&income=70000",
    ):
        r = await client.get(path)
        assert r.status_code == 200, path
        assert r.json()["statement"] == STATEMENT
    r = await client.get("/v1/checks/does-not-exist")
    assert r.status_code == 404 and r.json()["statement"] == STATEMENT
