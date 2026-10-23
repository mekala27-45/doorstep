"""The Census Building Permits Survey, county annual files.

One text file per year with three header lines and then one row per permit issuing county: the
buildings, units and value permitted in structures of one unit, two units, three and four units and
five or more, with and without imputation for places that did not report every month. The county grain
is the one that maps to every delineation vintage, which is why the metro files are not used. The
current year to date file is carried beside the annual ones and labeled as partial.
"""

from __future__ import annotations

import re
from pathlib import Path

import polars as pl

from doorstep_contracts.common import ContractError, Rule, apply_rules, contract_digest

FIELDS = (
    "year",
    "partial_through_month",
    "county_fips",
    "county_name",
    "units_1",
    "units_2",
    "units_3_4",
    "units_5_plus",
    "units_total",
    "buildings_total",
    "value_total",
    "units_total_reported",
)

RULES = (
    Rule("negative_units", "a negative unit count", lambda f: pl.col("units_total") < 0),
    Rule(
        "imputed_share_high",
        "the imputed total exceeds the reported total by more than half",
        lambda f: (pl.col("units_total_reported") > 0) & (pl.col("units_total") > 1.5 * pl.col("units_total_reported")),
    ),
    Rule("malformed_fips", "a county code that is not five digits", lambda f: pl.col("county_fips").str.len_chars() != 5),
)

DIGEST = contract_digest("permits", FIELDS, RULES, {"grain": "county annual plus the current year to date"})

_ANNUAL = re.compile(r"co(\d{4})a\.txt$")
_YTD = re.compile(r"co(\d{2})(\d{2})y\.txt$")


def _read(path: Path, year: int, month: int | None) -> pl.DataFrame:
    lines = path.read_text(encoding="latin-1").splitlines()
    body = [ln for ln in lines[3:] if ln.strip()]
    if not body:
        raise ContractError(f"{path.name} has no data rows")
    rows: list[dict[str, object]] = []
    for ln in body:
        parts = [p.strip() for p in ln.split(",")]
        if len(parts) < 30:
            continue
        try:
            values = [int(p) if p else 0 for p in parts[6:30]]
        except ValueError:
            continue
        # columns 6..17: estimates with imputation (bldgs, units, value) x 4 structure sizes; 18..29: reported only
        rows.append(
            {
                "year": year,
                "partial_through_month": month,
                "county_fips": parts[1].zfill(2) + parts[2].zfill(3),
                "county_name": parts[5],
                "units_1": values[1],
                "units_2": values[4],
                "units_3_4": values[7],
                "units_5_plus": values[10],
                "units_total": values[1] + values[4] + values[7] + values[10],
                "buildings_total": values[0] + values[3] + values[6] + values[9],
                "value_total": values[2] + values[5] + values[8] + values[11],
                "units_total_reported": values[13] + values[16] + values[19] + values[22],
            }
        )
    if not rows:
        raise ContractError(f"{path.name} parsed to no rows")
    return pl.DataFrame(rows, schema_overrides={"partial_through_month": pl.Int64})


def parse(external: Path) -> pl.DataFrame:
    folder = external / "bps"
    frames: list[pl.DataFrame] = []
    for path in sorted(folder.glob("co*.txt")):
        annual = _ANNUAL.search(path.name)
        ytd = _YTD.search(path.name)
        if annual:
            frames.append(_read(path, int(annual.group(1)), None))
        elif ytd:
            frames.append(_read(path, 2000 + int(ytd.group(1)), int(ytd.group(2))))
    if not frames:
        raise ContractError(f"no permit files under {folder}")
    return pl.concat(frames).sort(["year", "county_fips"])


def quarantine(frame: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    flagged, report = apply_rules(frame, RULES, "bps", "year")
    return flagged.select([*FIELDS, *[c for c in flagged.columns if c.startswith("q_")], "quarantined"]), report.frame()
