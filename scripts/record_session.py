"""Record an API session for the site's fallback.

Starts the API in a child process against a local Postgres (or drives a running server with
--base-url), walks the flow the planner performs (health, the metros, the breakeven curve for the
largest metros at their median income, a check saved for each of them, the scoring pass) and writes
every response, labelled recorded, to web/public/data/recorded_session.json. When the live API is
asleep the planner serves these responses and says so on the page. Every check the recording makes
carries the note the reset step deletes by.

    DOORSTEP_TEST_DATABASE_URL=postgresql+psycopg://... python scripts/record_session.py --start-server
    python scripts/record_session.py --base-url https://doorstep-housing-api.fly.dev --token ...
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "public" / "data" / "recorded_session.json"
NOTE = "recorded session"
METROS_RECORDED = 12
DOWN_SHARE = 0.1
HORIZON_YEARS = 30


def wait_for(base: str, seconds: float = 120.0) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            if httpx.get(f"{base}/v1/health", timeout=8.0).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1.0)
    raise SystemExit(f"the API at {base} did not answer within {seconds:.0f} seconds")


def round_income(value: float) -> int:
    """The planner offers incomes to the thousand; the recording uses the same grid."""
    return max(int(round(value / 1000.0)) * 1000, 1000)


def curve_name(inputs: dict[str, Any]) -> str:
    rate = "default" if inputs.get("rate") is None else str(inputs["rate"])
    return f"curve_{inputs['cbsa_code']}_{inputs['income']}_{inputs['down_share']}_{rate}_{inputs['horizon_years']}"


def curve_query(inputs: dict[str, Any]) -> str:
    """The query the site builds in curvePath: the same keys in the same order, the rate only when given."""
    pairs = [
        ("cbsa_code", inputs["cbsa_code"]),
        ("income", str(inputs["income"])),
        ("down_share", str(inputs["down_share"])),
        ("horizon_years", str(inputs["horizon_years"])),
    ]
    if inputs.get("rate") is not None:
        pairs.append(("rate", str(inputs["rate"])))
    return urlencode(pairs)


def record(base: str, token: str, *, metros_recorded: int = METROS_RECORDED) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    responses: dict[str, Any] = {}

    def get(name: str, path: str) -> dict[str, Any]:
        r = httpx.get(f"{base}{path}", timeout=120.0)
        responses[name] = {"method": "GET", "path": path, "status": r.status_code, "body": r.json()}
        return dict(r.json())

    get("health", "/v1/health")
    metros = get("metros", "/v1/metros")["metros"]
    inputs_recorded: list[dict[str, Any]] = []
    for m in metros[:metros_recorded]:
        # The largest metros at their own median income, the default rate, a ten percent down payment
        # and the thirty year horizon: the inputs the planner opens on.
        inputs = {
            "cbsa_code": str(m["cbsa_code"]),
            "income": round_income(float(m["median_income"])),
            "down_share": DOWN_SHARE,
            "rate": None,
            "horizon_years": HORIZON_YEARS,
        }
        path = f"/v1/curve?{curve_query(inputs)}"
        curve = httpx.get(f"{base}{path}", timeout=120.0)
        if curve.status_code != 200:
            continue
        responses[curve_name(inputs)] = {"method": "GET", "path": path, "status": 200, "body": curve.json()}
        saved = httpx.post(
            f"{base}/v1/checks",
            json={
                "cbsa_code": inputs["cbsa_code"],
                "income": inputs["income"],
                "down_share": inputs["down_share"],
                "horizon_years": inputs["horizon_years"],
                "note": NOTE,
            },
            headers=headers,
            timeout=120.0,
        )
        saved.raise_for_status()
        responses[f"check_{inputs['cbsa_code']}"] = {
            "method": "POST",
            "path": "/v1/checks",
            "status": saved.status_code,
            "body": saved.json(),
        }
        inputs_recorded.append(inputs)
    score = httpx.post(f"{base}/v1/score", json={"note": NOTE}, headers=headers, timeout=180.0)
    responses["score"] = {
        "method": "POST",
        "path": "/v1/score",
        "status": score.status_code,
        "body": score.json(),
    }
    get("scorecard", "/v1/scorecard")
    return {
        "recorded": True,
        "recorded_at": datetime.now(UTC).isoformat(),
        "base_url": base,
        "note": NOTE,
        "inputs": inputs_recorded,
        "responses": responses,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--start-server", action="store_true")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--token", default=os.environ.get("DOORSTEP_WRITE_TOKEN", "record-token"))
    parser.add_argument("--metros", type=int, default=METROS_RECORDED)
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args()
    server: subprocess.Popen[bytes] | None = None
    base = args.base_url
    try:
        if args.start_server:
            url = os.environ.get("DOORSTEP_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
            if not url:
                raise SystemExit("set DOORSTEP_TEST_DATABASE_URL or DATABASE_URL to start a server")
            env = {
                **os.environ,
                "DATABASE_URL": url,
                "DOORSTEP_WRITE_TOKEN": args.token,
                "DOORSTEP_ENV": "recording",
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
        wait_for(base)
        session = record(base, args.token, metros_recorded=args.metros)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(session, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"recorded {len(session['responses'])} responses for {len(session['inputs'])} metros to {out}")
        return 0
    finally:
        if server is not None:
            server.terminate()
            server.wait(timeout=20)


if __name__ == "__main__":
    sys.exit(main())
