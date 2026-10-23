"""The load test against a running API, when one is named: p50 and p99 of POST /v1/checks over a stated number
of requests and a burst of concurrent checks, written to results/latency/local.json for the documents. CI
starts the API on the committed marts and sets DOORSTEP_LOADTEST_BASE; elsewhere the test skips by name."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts import load_test  # noqa: E402
from tests._deps import need  # noqa: E402


def test_the_calculator_answers_a_stated_load() -> None:
    base = os.environ.get("DOORSTEP_LOADTEST_BASE", "").rstrip("/")
    need("loadtest", bool(base), "DOORSTEP_LOADTEST_BASE names no running API")
    token = os.environ.get("DOORSTEP_WRITE_TOKEN", "ci-token")
    result = asyncio.run(load_test.run(base, token, 40, 6))
    assert result["errors"] == 0
    assert result["requests"] == 40
    assert result["check"]["p50_ms"] <= result["check"]["p99_ms"]
    assert result["check"]["p99_ms"] < 5000.0
    assert result["burst_check_max_ms"] < 10000.0
    out = ROOT / "results" / "latency" / "local.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
