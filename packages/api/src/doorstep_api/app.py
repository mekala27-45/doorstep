"""The doorstep API: the affordability calculator and its check log.

``POST /v1/checks`` takes a metro code, an annual income, a down payment share, an optional rate (the
latest PMMS week when absent) and a horizon in years, returns the payment share, the affordable price,
the share of households in that metro that can afford the median home, the breakeven horizon with its
interval and the quarter of prices it rests on, writes the check row, then the audit row, then returns
the id. The check also stores the carry forward expectation: the payment share next quarter if prices
and rates do not move. ``GET /v1/checks/{id}`` returns the check with its score if any. ``POST /v1/score``
scores stored checks whose next quarter has now published, against the realized payment share in that
metro, and reports the share still unscored. ``GET /v1/curve`` is the rent or buy curve for the planner.
Writes need the token; this is a demonstration and the README says so. The income is stored rounded to
the nearest thousand; nothing else about the person is stored. Every response body carries the statement.
Every write goes: the row, then the audit row, then commit, then the response.
"""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated, Any

from doorstep_core.config import POLICY
from doorstep_core.statements import RATE_ATTRIBUTION, STATEMENT
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.exceptions import HTTPException as StarletteHTTPException

from doorstep_api.calculator import Answer, Calculator, UnknownMetro, UnknownQuarter
from doorstep_api.db import AuditEntry, Check, CheckScore, make_async_engine
from doorstep_api.settings import Settings, load_settings

log = logging.getLogger("doorstep_api")
# Real metros are five digit CBSA codes; the simulator's are S plus three digits, and the tests drive the API with them.
METRO = re.compile(r"^(\d{5}|S\d{3})$")
QUARTER = re.compile(r"^(19|20)\d{2}Q[1-4]$")


def envelope(data: dict[str, Any]) -> dict[str, Any]:
    return {
        **data,
        "statement": STATEMENT,
        "rate_attribution": RATE_ATTRIBUTION,
        "served_at": datetime.now(UTC).isoformat(),
    }


class CheckIn(BaseModel):
    cbsa_code: str = Field(min_length=4, max_length=5)
    income: float = Field(
        gt=0, le=10_000_000, description="annual household income in dollars; stored rounded to the thousand"
    )
    down_share: float = Field(default=POLICY.down_payment_share, ge=0.0, lt=0.9)
    rate: float | None = Field(
        default=None, ge=0.5, le=20.0, description="annual rate in percent; the latest PMMS week when absent"
    )
    horizon_years: int = Field(default=POLICY.breakeven_horizon_years, ge=1, le=40)
    quarter: str | None = Field(
        default=None,
        min_length=6,
        max_length=6,
        description="the quarter of prices to rest on; the latest when absent",
    )
    note: str = Field(default="", max_length=60)

    @field_validator("cbsa_code")
    @classmethod
    def metro(cls, value: str) -> str:
        value = value.strip().upper()
        if not METRO.match(value):
            raise ValueError("a metro is a five digit CBSA code")
        return value

    @field_validator("quarter")
    @classmethod
    def quarter_shape(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not QUARTER.match(value):
            raise ValueError("a quarter is YYYYQn")
        return value

    @field_validator("note")
    @classmethod
    def plain_note(cls, value: str) -> str:
        # A note labels where a check came from (demo, persistence check); it is not a place for a
        # name or an address, so it is held to a short word list of plain characters.
        if value and not re.fullmatch(r"[a-z ]{1,60}", value):
            raise ValueError("a note is lower case words")
        return value


class ScoreIn(BaseModel):
    note: str = Field(default="", max_length=60)


class AppState:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine: AsyncEngine = make_async_engine(settings.database_url, settings.schema)
        self.calculator = Calculator(settings.marts)


def state_of(request: Request) -> AppState:
    state: AppState = request.app.state.doorstep
    return state


async def session_of(request: Request) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(state_of(request).engine, expire_on_commit=False) as session:
        yield session


def actor_of(request: Request, authorization: Annotated[str | None, Header()] = None) -> str:
    settings = state_of(request).settings
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if settings.token_required and token == settings.write_token:
            return "token"
    return "anonymous"


SessionDep = Annotated[AsyncSession, Depends(session_of)]
ActorDep = Annotated[str, Depends(actor_of)]


def require_writer(actor: str) -> None:
    if actor != "token":
        raise HTTPException(status_code=401, detail="writes need the token")


def require_calculator(state: AppState) -> Calculator:
    if not state.calculator.ready:
        raise HTTPException(status_code=503, detail="the calculator marts are not on this server")
    return state.calculator


async def audit(
    session: AsyncSession,
    actor: str,
    action: str,
    resource: str,
    resource_id: str = "",
    detail: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditEntry(
            actor=actor, action=action, resource=resource, resource_id=resource_id, detail=detail or {}
        )
    )
    await session.commit()


def _answer(calc: Calculator, body: CheckIn) -> Answer:
    try:
        return calc.check(
            body.cbsa_code, body.income, body.down_share, body.rate, body.horizon_years, quarter=body.quarter
        )
    except UnknownMetro as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnknownQuarter as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.doorstep = AppState(settings)
        yield
        await app.state.doorstep.engine.dispose()

    app = FastAPI(title="doorstep", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins) or ["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=envelope({"error": str(exc.detail)}))

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
        problems = [
            {"field": ".".join(str(p) for p in e.get("loc", ())), "message": e.get("msg", "")}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422, content=envelope({"error": "invalid request", "detail": problems})
        )

    @app.get("/v1/health")
    async def health(request: Request, session: SessionDep) -> dict[str, Any]:
        state = state_of(request)
        database = "ok"
        try:
            await session.exec(select(Check.id).limit(1))
        except Exception as exc:  # the reason goes to the server log, never to the client
            log.warning("health: the database is unreachable: %s: %s", type(exc).__name__, exc)
            database = "unreachable"
        calc = state.calculator
        return envelope(
            {
                "status": "ok",
                "environment": state.settings.environment,
                "database": database,
                "model_version": calc.version,
                "metros": int(calc.metros.height) if calc.metros is not None else 0,
                "latest_period": calc.latest_period,
                "rate_default": calc.rate_default if calc.ready else None,
                "income_year": calc.meta.get("income_year"),
                "writes": "token gated",
            }
        )

    @app.get("/v1/metros")
    async def metros(request: Request) -> dict[str, Any]:
        state = state_of(request)
        calc = require_calculator(state)
        assert calc.metros is not None
        rows = calc.metros.sort("households", descending=True).select(
            "cbsa_code",
            "cbsa_title",
            "households",
            "median_income",
            "median_rent",
            "latest_period",
            "value_latest",
            "rate_latest",
            "income_year",
        )
        return envelope(
            {"metros": rows.to_dicts(), "rate_default": calc.rate_default, "model_version": calc.version}
        )

    @app.get("/v1/curve")
    async def curve(
        request: Request,
        cbsa_code: Annotated[str, Query(min_length=4, max_length=5)],
        income: Annotated[float, Query(gt=0)],
        down_share: Annotated[float, Query(ge=0.0, lt=0.9)] = POLICY.down_payment_share,
        rate: Annotated[float | None, Query(ge=0.5, le=20.0)] = None,
        horizon_years: Annotated[int, Query(ge=1, le=40)] = POLICY.breakeven_horizon_years,
    ) -> dict[str, Any]:
        state = state_of(request)
        calc = require_calculator(state)
        body = CheckIn(
            cbsa_code=cbsa_code, income=income, down_share=down_share, rate=rate, horizon_years=horizon_years
        )
        answer = _answer(calc, body)
        points = calc.curve(body.cbsa_code, income, down_share, rate, horizon_years)
        return envelope({**answer.payload(), "points": points, "model_version": calc.version})

    @app.post("/v1/checks", status_code=201)
    async def create_check(
        body: CheckIn, request: Request, session: SessionDep, actor: ActorDep
    ) -> dict[str, Any]:
        require_writer(actor)
        state = state_of(request)
        calc = require_calculator(state)
        a = _answer(calc, body)
        row = Check(
            check_id=str(uuid.uuid4()),
            cbsa_code=a.cbsa_code,
            income=a.income,
            down_share=a.down_share,
            rate=a.rate,
            horizon_years=a.horizon_years,
            quarter=a.quarter,
            median_home=a.median_home,
            payment=a.payment,
            payment_share=a.payment_share,
            affordable_price=a.affordable_price,
            affordable_share=a.affordable_share,
            breakeven_years=a.breakeven_years,
            breakeven_low=a.breakeven_low,
            breakeven_high=a.breakeven_high,
            expected_next_payment_share=a.expected_next_payment_share,
            model_version=calc.version,
            note=body.note,
        )
        session.add(row)
        await session.flush()
        await audit(
            session,
            actor,
            "create",
            "check",
            row.check_id,
            {"cbsa_code": row.cbsa_code, "quarter": row.quarter, "model_version": row.model_version},
        )
        return envelope(
            {
                "check_id": row.check_id,
                **_check_payload(row),
                "households_can_afford": a.households_can_afford,
                "never_share": a.never_share,
                "cbsa_title": a.cbsa_title,
            }
        )

    @app.get("/v1/checks")
    async def list_checks(
        session: SessionDep, cbsa_code: str | None = None, limit: int = 50
    ) -> dict[str, Any]:
        query = select(Check).order_by(col(Check.created_at).desc()).limit(min(max(limit, 1), 500))
        if cbsa_code:
            query = query.where(Check.cbsa_code == cbsa_code.upper())
        rows = (await session.exec(query)).all()
        return envelope({"checks": [_check_payload(r) for r in rows]})

    @app.get("/v1/checks/{check_id}")
    async def get_check(check_id: str, session: SessionDep) -> dict[str, Any]:
        row = (await session.exec(select(Check).where(Check.check_id == check_id))).first()
        if row is None:
            raise HTTPException(status_code=404, detail="no check with that id")
        score = (await session.exec(select(CheckScore).where(CheckScore.check_id == check_id))).first()
        return envelope({**_check_payload(row), "score": _score_payload(score) if score else None})

    @app.post("/v1/score")
    async def score(body: ScoreIn, request: Request, session: SessionDep, actor: ActorDep) -> dict[str, Any]:
        require_writer(actor)
        state = state_of(request)
        calc = require_calculator(state)
        checks = (await session.exec(select(Check))).all()
        scored_ids = {s.check_id for s in (await session.exec(select(CheckScore))).all()}
        added = 0
        waiting = 0
        for c in checks:
            if c.check_id in scored_ids:
                continue
            try:
                result = calc.realized(c.cbsa_code, c.quarter, c.income, c.down_share, c.rate, c.median_home)
            except (UnknownMetro, UnknownQuarter):
                result = None
            if result is None:
                waiting += 1
                continue
            session.add(
                CheckScore(
                    check_id=c.check_id,
                    scored_quarter=str(result["quarter"]),
                    realized_payment_share=float(result["payment_share"]),
                    absolute_error=abs(float(result["payment_share"]) - c.expected_next_payment_share),
                    price_moved=float(result["price_moved"]),
                    rate_moved=float(result["rate_moved"]),
                )
            )
            added += 1
        await session.flush()
        total = len(checks)
        scored = len(scored_ids) + added
        unscored_share = 1.0 - scored / total if total else 1.0
        await audit(
            session,
            actor,
            "score",
            "check",
            "",
            {
                "scored": added,
                "waiting": waiting,
                "latest_period": calc.latest_period,
                "unscored_share": unscored_share,
            },
        )
        return envelope(
            {
                "scored": added,
                "checks": total,
                "waiting_for_next_quarter": waiting,
                "latest_period": calc.latest_period,
                "unscored_share": unscored_share,
            }
        )

    @app.get("/v1/scorecard")
    async def scorecard(session: SessionDep) -> dict[str, Any]:
        checks = (await session.exec(select(Check))).all()
        scores = (await session.exec(select(CheckScore))).all()
        return envelope(
            {
                "checks": len(checks),
                "scored": len(scores),
                "unscored_share": 1.0 - len(scores) / len(checks) if checks else 1.0,
                "mean_absolute_error": sum(s.absolute_error for s in scores) / len(scores)
                if scores
                else None,
                "mean_price_move": sum(s.price_moved for s in scores) / len(scores) if scores else None,
                "mean_rate_move": sum(s.rate_moved for s in scores) / len(scores) if scores else None,
            }
        )

    @app.get("/v1/audit")
    async def audit_log(session: SessionDep, limit: int = 100) -> dict[str, Any]:
        rows = (
            await session.exec(
                select(AuditEntry).order_by(col(AuditEntry.at).desc()).limit(min(max(limit, 1), 500))
            )
        ).all()
        return envelope(
            {
                "entries": [
                    {
                        "at": r.at.isoformat(),
                        "actor": r.actor,
                        "action": r.action,
                        "resource": r.resource,
                        "resource_id": r.resource_id,
                        "detail": r.detail,
                    }
                    for r in rows
                ]
            }
        )

    return app


def _check_payload(row: Check) -> dict[str, Any]:
    return {
        "check_id": row.check_id,
        "cbsa_code": row.cbsa_code,
        "income": row.income,
        "down_share": row.down_share,
        "rate": row.rate,
        "horizon_years": row.horizon_years,
        "quarter": row.quarter,
        "median_home": row.median_home,
        "payment": row.payment,
        "payment_share": row.payment_share,
        "affordable_price": row.affordable_price,
        "affordable_share": row.affordable_share,
        "breakeven_years": row.breakeven_years,
        "breakeven_low": row.breakeven_low,
        "breakeven_high": row.breakeven_high,
        "expected_next_payment_share": row.expected_next_payment_share,
        "model_version": row.model_version,
        "note": row.note,
        "created_at": row.created_at.isoformat(),
    }


def _score_payload(s: CheckScore) -> dict[str, Any]:
    return {
        "scored_quarter": s.scored_quarter,
        "realized_payment_share": s.realized_payment_share,
        "absolute_error": s.absolute_error,
        "price_moved": s.price_moved,
        "rate_moved": s.rate_moved,
        "scored_at": s.scored_at.isoformat(),
    }
