"""The Census population estimates with the components of change, at the county grain.

Three releases cover the window: the 2000 to 2010 intercensal totals, the vintage 2019 file for 2010
to 2019 and the latest vintage for 2020 onward. Each vintage re-estimates its own years, so a year
that two vintages both cover is taken from the later one, and the number of such years is published
as a quarantine count rather than silently reconciled. The county grain maps to every delineation
vintage; the metro files are kept as a check on the roll up.
"""

from __future__ import annotations

import re
from pathlib import Path

import polars as pl

from doorstep_contracts.common import ContractError, Rule, apply_rules, contract_digest

FIELDS = (
    "county_fips",
    "year",
    "vintage",
    "population",
    "births",
    "deaths",
    "international_migration",
    "domestic_migration",
)

RULES = (
    Rule(
        "vintage_overlap",
        "a county year estimated by more than one vintage; the later vintage is used",
        lambda f: pl.col("vintages_for_year") > 1,
    ),
    Rule(
        "non_positive_population",
        "a population estimate at or below zero",
        lambda f: pl.col("population") <= 0,
    ),
)

DIGEST = contract_digest("population", FIELDS, RULES)


def _melt(frame: pl.DataFrame, vintage: int, fips_expr: pl.Expr) -> pl.DataFrame:
    years = sorted(
        {int(m.group(1)) for c in frame.columns for m in [re.match(r"POPESTIMATE(\d{4})$", c)] if m}
    )
    out: list[pl.DataFrame] = []
    for year in years:

        def col(prefix: str, year: int = year) -> pl.Expr:
            name = f"{prefix}{year}"
            alt = f"{prefix}_{year}"
            if name in frame.columns:
                return pl.col(name).cast(pl.Float64)
            if alt in frame.columns:
                return pl.col(alt).cast(pl.Float64)
            return pl.lit(None, dtype=pl.Float64)

        out.append(
            frame.select(
                fips_expr.alias("county_fips"),
                pl.lit(year).alias("year"),
                pl.lit(vintage).alias("vintage"),
                col("POPESTIMATE").alias("population"),
                col("BIRTHS").alias("births"),
                col("DEATHS").alias("deaths"),
                col("INTERNATIONALMIG").alias("international_migration"),
                col("DOMESTICMIG").alias("domestic_migration"),
            )
        )
    return pl.concat(out)


def parse_counties(external: Path) -> pl.DataFrame:
    folder = external / "popest"
    frames: list[pl.DataFrame] = []
    for path in sorted(folder.glob("co-est*-alldata.csv")):
        m = re.search(r"co-est(\d{4})-alldata", path.name)
        if not m:
            continue
        vintage = int(m.group(1))
        raw = pl.read_csv(path, encoding="latin-1", infer_schema_length=0)
        raw = raw.filter(pl.col("SUMLEV").cast(pl.Int64) == 50)
        fips = pl.col("STATE").cast(pl.Utf8).str.zfill(2) + pl.col("COUNTY").cast(pl.Utf8).str.zfill(3)
        frames.append(_melt(raw, vintage, fips))
    if not frames:
        raise ContractError(f"no county population files under {folder}")
    frame = pl.concat(frames).sort(["county_fips", "year", "vintage"])
    frame = frame.with_columns(pl.len().over(["county_fips", "year"]).alias("vintages_for_year"))
    return frame


def parse_intercensal_totals(external: Path) -> pl.DataFrame | None:
    """The 2000 to 2010 intercensal county totals: the Census Bureau's own reconciliation of the decade,
    kept as the check on the vintage 2009 estimates the components come from."""
    path = external / "popest" / "co-est00int-tot.csv"
    if not path.exists():
        return None
    raw = pl.read_csv(path, encoding="latin-1", infer_schema_length=0)
    raw = raw.filter(pl.col("SUMLEV").cast(pl.Int64) == 50)
    fips = pl.col("STATE").cast(pl.Utf8).str.zfill(2) + pl.col("COUNTY").cast(pl.Utf8).str.zfill(3)
    return (
        _melt(raw, 2010, fips)
        .select(["county_fips", "year", "population"])
        .rename({"population": "intercensal_population"})
    )


def latest_per_year(frame: pl.DataFrame) -> pl.DataFrame:
    """One row per county and year: the latest vintage that estimated it."""
    return (
        frame.sort(["county_fips", "year", "vintage"])
        .group_by(["county_fips", "year"], maintain_order=True)
        .agg(pl.all().last())
    )


def parse_metros(external: Path) -> pl.DataFrame:
    """The published metro totals, for the roll up check."""
    folder = external / "popest"
    frames: list[pl.DataFrame] = []
    for path in sorted(folder.glob("cbsa-est*-alldata.csv")):
        m = re.search(r"cbsa-est(\d{4})-alldata", path.name)
        if not m:
            continue
        raw = pl.read_csv(path, encoding="latin-1", infer_schema_length=0)
        raw = raw.filter(
            pl.col("LSAD").str.contains("Statistical Area")
            & (pl.col("MDIV").is_null() | (pl.col("MDIV") == ""))
            & (pl.col("STCOU").is_null() | (pl.col("STCOU") == ""))
        )
        frames.append(
            _melt(raw, int(m.group(1)), pl.col("CBSA").cast(pl.Utf8)).rename({"county_fips": "cbsa_code"})
        )
    if not frames:
        raise ContractError(f"no metro population files under {folder}")
    return pl.concat(frames).sort(["cbsa_code", "year", "vintage"])


def quarantine(frame: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    flagged, report = apply_rules(frame, RULES, "popest", "year")
    return flagged.select(
        [*FIELDS, *[c for c in flagged.columns if c.startswith("q_")], "quarantined"]
    ), report.frame()
