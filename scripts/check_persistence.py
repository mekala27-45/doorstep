"""The out of process check: make a check at the quarter before the latest one the server holds, score it
against the latest quarter, and read the rows back through a connection this process opens itself.

Two modes. `--start-server` migrates with alembic, starts the API in a child process against the
database URL, drives it over HTTP, then reads the check, its score and the audit row with a fresh
psycopg connection in this process. `--base-url` drives a live server (the Fly deployment) and reads
back through the API's own GET endpoints from this separate client, which is the verification the
README prints. In both modes the audit row must be observed at or before the response's served_at.

    python scripts/check_persistence.py --start-server
    python scripts/check_persistence.py --base-url https://doorstep-api.fly.dev --out results/deploy/verification.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
if __package__ in {None, ""}:
    sys.path.insert(0, str(ROOT))

from doorstep_core.statements import STATEMENT

NOTE = "persistence check"


def wait_for(base: str, seconds: float = 90.0) -> dict[str, Any]:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            response = httpx.get(f"{base}/v1/health", timeout=8.0)
            if response.status_code == 200:
                body: dict[str, Any] = response.json()
                return body
        except httpx.HTTPError:
            pass
        time.sleep(1.0)
    raise SystemExit(f"the API at {base} did not answer within {seconds:.0f} seconds")


def a_metro(base: str, metro: str | None) -> dict[str, Any]:
    listed = httpx.get(f"{base}/v1/metros", timeout=60.0)
    listed.raise_for_status()
    metros = listed.json()["metros"]
    if not metros:
        raise SystemExit("the server covers no metros")
    chosen = next((m for m in metros if m["cbsa_code"] == metro), metros[0]) if metro else metros[0]
    return {
        "cbsa_code": str(chosen["cbsa_code"]),
        "cbsa_title": str(chosen["cbsa_title"]),
        "median_income": float(chosen["median_income"]),
        "latest_period": str(chosen["latest_period"]),
    }


def previous_quarter(period: str) -> str:
    year, q = int(period[:4]), int(period[5])
    return f"{year}Q{q - 1}" if q > 1 else f"{year - 1}Q4"


def drive(base: str, token: str, metro: str | None) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    m = a_metro(base, metro)
    # The check rests on the quarter before the latest one, so the latest quarter is the one that scores it.
    quarter = previous_quarter(m["latest_period"])
    body = {
        "cbsa_code": m["cbsa_code"],
        "income": round(m["median_income"] / 1000.0) * 1000,
        "down_share": 0.10,
        "horizon_years": 30,
        "quarter": quarter,
        "note": NOTE,
    }
    created = httpx.post(f"{base}/v1/checks", json=body, headers=headers, timeout=120.0)
    created.raise_for_status()
    check = created.json()
    if check["statement"] != STATEMENT:
        raise SystemExit("the check response is missing the statement")
    scored = httpx.post(f"{base}/v1/score", json={"note": NOTE}, headers=headers, timeout=120.0)
    scored.raise_for_status()
    return {
        "check_id": str(check["check_id"]),
        "cbsa_code": m["cbsa_code"],
        "cbsa_title": m["cbsa_title"],
        "quarter": quarter,
        "income": int(check["income"]),
        "payment_share": float(check["payment_share"]),
        "affordable_price": float(check["affordable_price"]),
        "affordable_share": check["affordable_share"],
        "breakeven_years": check["breakeven_years"],
        "breakeven_low": check["breakeven_low"],
        "breakeven_high": check["breakeven_high"],
        "model_version": str(check["model_version"]),
        "served_at": datetime.fromisoformat(str(check["served_at"])),
        "scored_reported": int(scored.json()["scored"]),
        "unscored_share": float(scored.json()["unscored_share"]),
    }


def read_back_via_api(base: str, ids: dict[str, Any]) -> dict[str, Any]:
    check = httpx.get(f"{base}/v1/checks/{ids['check_id']}", timeout=60.0)
    check.raise_for_status()
    audit = httpx.get(f"{base}/v1/audit?limit=50", timeout=60.0)
    audit.raise_for_status()
    c = check.json()
    if c["statement"] != STATEMENT or audit.json()["statement"] != STATEMENT:
        raise SystemExit("a response is missing the statement")
    if abs(float(c["payment_share"]) - ids["payment_share"]) > 1e-12:
        raise SystemExit("the check did not come back with the payment share it was created with")
    entries = audit.json()["entries"]
    created = [x for x in entries if x["action"] == "create" and x["resource_id"] == ids["check_id"]]
    if not created:
        raise SystemExit("no audit row for the check")
    if datetime.fromisoformat(created[0]["at"]) > ids["served_at"]:
        raise SystemExit("the audit row was written after the response was served")
    return {
        "check": {
            k: c[k]
            for k in (
                "cbsa_code",
                "income",
                "down_share",
                "rate",
                "quarter",
                "payment_share",
                "affordable_price",
                "breakeven_years",
            )
        },
        "score": c["score"],
        "audit_entries": len(entries),
        "audit_before_response": True,
    }


def read_back_via_postgres(url: str, ids: dict[str, Any], schema: str) -> dict[str, Any]:
    import psycopg

    plain = url.replace("postgresql+psycopg://", "postgresql://")
    prefix = f'"{schema}".' if schema else ""
    with psycopg.connect(plain) as conn, conn.cursor() as cur:
        cur.execute(
            f"select payment_share, model_version from {prefix}checks where check_id = %s", (ids["check_id"],)
        )
        check = cur.fetchone()
        cur.execute(
            f"select count(*), max(scored_quarter) from {prefix}check_scores where check_id = %s",
            (ids["check_id"],),
        )
        scores = cur.fetchone()
        cur.execute(
            f"select at from {prefix}audit_log where action = 'create' and resource_id = %s",
            (ids["check_id"],),
        )
        audit = cur.fetchone()
    if (
        check is None
        or abs(float(check[0]) - ids["payment_share"]) > 1e-12
        or check[1] != ids["model_version"]
    ):
        raise SystemExit("the check row is missing from a fresh connection")
    if scores is None or int(scores[0]) != 1:
        raise SystemExit("the score row is missing from a fresh connection")
    if audit is None or audit[0] > ids["served_at"]:
        raise SystemExit("the audit row is missing or later than the response")
    return {
        "check": True,
        "scores": int(scores[0]),
        "scored_quarter": scores[1],
        "audit_before_response": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--start-server", action="store_true")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--metro", default=None)
    parser.add_argument("--out", default=None, help="write the observation as JSON here as well")
    args = parser.parse_args()
    token = os.environ.get("DOORSTEP_WRITE_TOKEN", "check-token")
    server: subprocess.Popen[bytes] | None = None
    base = args.base_url
    schema = os.environ.get("DOORSTEP_DB_SCHEMA", "").strip()
    try:
        if args.start_server:
            url = os.environ.get("DOORSTEP_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
            if not url:
                raise SystemExit("set DOORSTEP_TEST_DATABASE_URL or DATABASE_URL to start a server")
            env = {
                **os.environ,
                "DATABASE_URL": url,
                "DOORSTEP_WRITE_TOKEN": token,
                "DOORSTEP_ENV": "check",
            }
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "alembic",
                    "-c",
                    str(ROOT / "packages" / "api" / "alembic.ini"),
                    "upgrade",
                    "head",
                ],
                cwd=ROOT / "packages" / "api",
                env=env,
                check=True,
            )
            server = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "doorstep_api.main:app",
                    "--port",
                    str(args.port),
                    "--log-level",
                    "warning",
                ],
                cwd=ROOT,
                env=env,
            )
            base = f"http://127.0.0.1:{args.port}"
        if not base:
            raise SystemExit("give --base-url or --start-server")
        base = base.rstrip("/")
        health = wait_for(base)
        if not health.get("latest_period"):
            raise SystemExit("the server holds no quarter to score against")
        ids = drive(base, token, args.metro)
        if args.start_server:
            url = os.environ.get("DOORSTEP_TEST_DATABASE_URL") or os.environ["DATABASE_URL"]
            observed = read_back_via_postgres(url, ids, schema)
        else:
            observed = read_back_via_api(base, ids)
        report = {
            "base_url": base,
            "health": {
                k: health.get(k)
                for k in ("status", "database", "model_version", "metros", "latest_period", "rate_default")
            },
            "ids": {k: str(v) for k, v in ids.items()},
            "observed": observed,
        }
        print(json.dumps(report, indent=1))
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
        print(
            "persistence check: a check, its score and its audit row were read back from outside the server process"
        )
        return 0
    finally:
        if server is not None:
            server.terminate()
            server.wait(timeout=20)


if __name__ == "__main__":
    sys.exit(main())
