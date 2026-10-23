"""The American Community Survey one year release, one JSON file per table and year.

The fetch script asks api.census.gov for explicit variables (estimates and margins of error) at the
metropolitan and micropolitan geography and, on a slow night, Census Reporter's mirror of the same
tables. Both shapes land here and become one long frame: year, area code, table, variable, estimate,
margin. Every margin is kept beside its estimate because the ranking's intervals are built from them.

The census publishes jam values for suppressed or inapplicable cells (large negative numbers such as
-666666666) and leaves out the 2020 one year release altogether; both are quarantine rules, not
silent fixes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import polars as pl
from doorstep_core.scalars import num

from doorstep_contracts.common import ContractError, Rule, apply_rules, contract_digest

FIELDS = ("year", "cbsa_code", "name", "table", "variable", "estimate", "moe", "source", "is_national")

TABLES = {
    "B19013": "median household income",
    "B19001": "households by income bracket",
    "B25064": "median gross rent",
    "B25077": "median value of owner occupied units",
    "B25070": "gross rent as a percentage of household income",
    "B25071": "median gross rent as a percentage of household income",
    "B25074": "gross rent as a percentage of household income by household income",
    "B25091": "selected monthly owner costs as a percentage of income by mortgage status",
    "B25106": "tenure by housing costs as a percentage of household income",
    "B25003": "tenure",
    "B25007": "tenure by age of householder",
    "B25118": "tenure by household income",
    "B25119": "median household income by tenure",
    "B11001": "household type",
    "B25001": "housing units",
    "B25002": "occupancy status",
    "B25004": "vacancy status",
    "B25024": "units in structure",
    "B25103": "mortgage status by median real estate taxes paid",
}

JAM_THRESHOLD = -1_000_000

RULES = (
    Rule(
        "jam_value",
        "a census jam value standing in for a suppressed or inapplicable estimate",
        lambda f: pl.col("estimate") < JAM_THRESHOLD,
    ),
    Rule(
        "moe_exceeds_estimate",
        "a margin of error larger than the estimate it qualifies",
        lambda f: (pl.col("moe") > pl.col("estimate").abs()) & (pl.col("estimate") > 0),
    ),
    Rule(
        "negative_moe",
        "a negative margin of error that is not a jam value",
        lambda f: (pl.col("moe") < 0) & (pl.col("moe") > JAM_THRESHOLD),
    ),
)

DIGEST = contract_digest("acs", FIELDS, RULES, {"tables": sorted(TABLES)})

_VAR = re.compile(r"^(B\d{5}[A-Z]?)_?(\d{3})([EM])$")
_REPORTER_VAR = re.compile(r"^(B\d{5}[A-Z]?)(\d{3})$")


def _number(value: object) -> float | None:
    if value is None or value == "" or value == "null":
        return None
    try:
        return num(value)
    except (TypeError, ValueError):
        return None


def _parse_census(
    payload: list[list[object]], year: int, table: str, is_national: bool
) -> list[dict[str, object]]:
    header = [str(h) for h in payload[0]]
    # The geography column is found by name, not position: a table fetched in several requests may carry the
    # column in the middle once the requests are joined, and the last column is then an estimate.
    geo_index = len(header) - 1
    for i, h in enumerate(header):
        if h == "us" or "statistical area" in h.lower():
            geo_index = i
            break
    name_index = header.index("NAME") if "NAME" in header else None
    rows: list[dict[str, object]] = []
    for record in payload[1:]:
        estimates: dict[str, float | None] = {}
        margins: dict[str, float | None] = {}
        for h, v in zip(header, record, strict=False):
            m = _VAR.match(h)
            if not m:
                continue
            key = f"{m.group(1)}_{m.group(2)}"
            if m.group(3) == "E":
                estimates[key] = _number(v)
            else:
                margins[key] = _number(v)
        code = "US" if is_national else str(record[geo_index])
        name = str(record[name_index]) if name_index is not None else code
        for key, est in estimates.items():
            rows.append(
                {
                    "year": year,
                    "cbsa_code": code,
                    "name": name,
                    "table": table,
                    "variable": key,
                    "estimate": est,
                    "moe": margins.get(key),
                    "source": "census",
                    "is_national": is_national,
                }
            )
    return rows


def _parse_reporter(payload: dict[str, object], year: int, table: str) -> list[dict[str, object]]:
    data = payload.get("data")
    geography = payload.get("geography", {})
    if not isinstance(data, dict):
        raise ContractError(f"Census Reporter payload for {table} {year} has no data block")
    rows: list[dict[str, object]] = []
    for geoid, tables in data.items():
        code = str(geoid).split("US")[-1]
        name = str(geography.get(geoid, {}).get("name", code)) if isinstance(geography, dict) else code
        block = tables.get(table, {}) if isinstance(tables, dict) else {}
        estimates = block.get("estimate", {}) if isinstance(block, dict) else {}
        errors = block.get("error", {}) if isinstance(block, dict) else {}
        for var, est in estimates.items():
            m = _REPORTER_VAR.match(var)
            if not m:
                continue
            key = f"{m.group(1)}_{m.group(2)}"
            rows.append(
                {
                    "year": year,
                    "cbsa_code": code,
                    "name": name,
                    "table": table,
                    "variable": key,
                    "estimate": _number(est),
                    "moe": _number(errors.get(var)),
                    "source": "reporter",
                    "is_national": False,
                }
            )
    return rows


def parse(external: Path) -> pl.DataFrame:
    folder = external / "acs"
    rows: list[dict[str, object]] = []
    files_read = 0
    for year_dir in sorted(folder.glob("[12][0-9][0-9][0-9]")):
        year = int(year_dir.name)
        for path in sorted(year_dir.glob("*.json")):
            stem = path.stem
            is_national = stem.endswith("_us")
            table = stem.replace("_us", "")
            if table not in TABLES:
                continue
            text = path.read_text(encoding="utf-8-sig")
            if not text.strip():
                continue
            payload = json.loads(text)
            if isinstance(payload, dict) and isinstance(payload.get("value"), list) and "Count" in payload:
                # PowerShell's ConvertTo-Json wraps an array it was handed by name as {value, Count}.
                payload = payload["value"]
            if isinstance(payload, list):
                rows.extend(_parse_census(payload, year, table, is_national))
            elif isinstance(payload, dict):
                rows.extend(_parse_reporter(payload, year, table))
            files_read += 1
    if not rows:
        raise ContractError(f"no ACS files under {folder}; run deploy/fetch-data.ps1 acs")
    frame = pl.DataFrame(
        rows, schema_overrides={"estimate": pl.Float64, "moe": pl.Float64, "cbsa_code": pl.Utf8}
    )
    return frame.sort(["year", "table", "cbsa_code", "variable"])


def quarantine(frame: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    flagged, report = apply_rules(frame, RULES, "acs", "year")
    return flagged, report.frame()


GAP_YEAR = 2020
"""The one year release that does not exist; a row claiming it is a planted error, never a fill."""


def years_present(frame: pl.DataFrame) -> list[int]:
    return sorted(int(y) for y in frame["year"].unique().to_list())


def refuse_gap_year(frame: pl.DataFrame) -> None:
    """The gap is carried as a gap: a row for the missing release is refused rather than carried."""
    if frame.filter(pl.col("year") == GAP_YEAR).height:
        raise ContractError(f"the {GAP_YEAR} one year release does not exist; a row claiming it was planted")


def coverage(frame: pl.DataFrame) -> pl.DataFrame:
    """Tables by year with the number of areas each one covers, for the data page."""
    return (
        frame.filter(~pl.col("is_national"))
        .group_by(["year", "table", "source"])
        .agg(pl.col("cbsa_code").n_unique().alias("areas"))
        .sort(["year", "table"])
    )
