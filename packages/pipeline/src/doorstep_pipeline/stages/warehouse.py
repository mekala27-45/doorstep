"""Stage two: dbt builds and tests the warehouse over the derived parquet, then the shipped marts are exported.

dbt runs from warehouse/ so the sources' relative paths resolve to the repository's data folder. Its
run results are read back for the counts the README prints (models, tests, failures), and a failing
test fails the stage. The marts the site, the workbook and the BI extracts read are copied to
results/marts as parquet, sorted by their keys so the files are byte for byte the same on a rerun.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from doorstep_core.manifest import Manifest, Scribe
from doorstep_core.paths import Paths

from doorstep_pipeline.common import new_partial, save_partial

SHIPPED: dict[str, tuple[str, ...]] = {
    "mart_metro_year": ("cbsa_code", "year"),
    "mart_metro_quarter": ("cbsa_code", "year", "quarter"),
    "mart_income_brackets": ("year", "cbsa_code", "bracket"),
    "mart_rent_burden_by_income": ("year", "cbsa_code", "group_order"),
    "mart_national_year": ("year",),
    "mart_quarantine": ("source", "rule", "year"),
    "fct_metro_year": ("cbsa_code", "year"),
    "grain_acs": ("year", "cbsa_code", "\"table\"", "variable"),
    "grain_counties": ("year", "county_fips"),
    "grain_loans": ("year", "cbsa_code", "loan_purpose", "interest_rate"),
}


class WarehouseError(RuntimeError):
    pass


def dbt_executable() -> str:
    candidate = Path(sys.executable).with_name("dbt")
    return str(candidate) if candidate.exists() else "dbt"


def run_dbt(p: Paths, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.setdefault("DOORSTEP_WAREHOUSE_PATH", str(p.warehouse_db))
    env.setdefault("DOORSTEP_DATA_DIR", str(p.data))
    env.setdefault("DOORSTEP_RESULTS_DIR", str(p.results))
    env.setdefault("DOORSTEP_DUCKDB_TMP", str(p.scratch / "duckdb_tmp"))
    p.scratch.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [dbt_executable(), *args, "--profiles-dir", "."],
        cwd=p.warehouse,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def summarise_results(path: Path) -> dict[str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    counts = {"models": 0, "tests": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0, "warned": 0}
    for result in payload.get("results", []):
        unique_id = str(result.get("unique_id", ""))
        status = str(result.get("status", ""))
        if unique_id.startswith("model."):
            counts["models"] += 1
            if status == "error":
                counts["errors"] += 1
        elif unique_id.startswith("test."):
            counts["tests"] += 1
            counts["passed"] += status == "pass"
            counts["failed"] += status == "fail"
            counts["errors"] += status == "error"
            counts["warned"] += status == "warn"
        counts["skipped"] += status == "skipped"
    return counts


def export_marts(p: Paths) -> dict[str, int]:
    import duckdb

    p.marts.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(p.warehouse_db), read_only=True)
    con.execute("set enable_progress_bar = false")
    rows: dict[str, int] = {}
    for name, keys in SHIPPED.items():
        out = p.marts / f"{name}.parquet"
        con.execute(
            f"copy (select * from {name} order by {', '.join(keys)}) to '{out.as_posix()}' "
            "(format parquet, compression zstd, row_group_size 100000)"
        )
        count = con.execute(f"select count(*) from {name}").fetchone()
        rows[name] = int(count[0]) if count else 0
    con.close()
    return rows


def run(p: Paths) -> Manifest:
    built = run_dbt(p, "build")
    results_file = p.warehouse / "target" / "run_results.json"
    counts = summarise_results(results_file) if results_file.exists() else {}
    if built.returncode != 0:
        raise WarehouseError("dbt build failed:\n" + built.stdout[-4000:] + built.stderr[-2000:])
    rows = export_marts(p)
    out = p.results / "warehouse"
    out.mkdir(parents=True, exist_ok=True)
    (out / "build_summary.json").write_text(
        json.dumps({"counts": counts, "mart_rows": rows}, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )

    manifest = new_partial("warehouse")
    s = Scribe(
        manifest,
        source="mixed",
        population="the dbt warehouse over every metro and year in the window",
        origin="stages/warehouse.py",
    )
    s.put("warehouse.models", counts.get("models", 0), "int")
    s.put("warehouse.tests", counts.get("tests", 0), "int")
    s.put("warehouse.tests_passed", counts.get("passed", 0), "int")
    s.put("warehouse.tests_failed", counts.get("failed", 0) + counts.get("errors", 0), "int")
    for name, n in rows.items():
        s.put(f"warehouse.rows.{name}", n, "int")
    save_partial(p, "warehouse", manifest)
    return manifest
