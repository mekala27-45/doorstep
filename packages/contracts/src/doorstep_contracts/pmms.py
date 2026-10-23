"""The Freddie Mac Primary Mortgage Market Survey weekly history.

One workbook, one sheet, a header block of seven rows and then one row per week since April 1971:
the 30 year fixed rate and its fees and points, the 15 year fixed rate (from 1991), and the 5/1 ARM
(2005 to 2022). The build keeps the 30 year rate, averages it by quarter for the payment series, and
takes the latest week as the calculator's default. Free with attribution to Freddie Mac, which every
page that shows a rate carries.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import polars as pl

from doorstep_contracts.common import ContractError, Rule, apply_rules, contract_digest, require

FIELDS = ("week", "year", "quarter", "period", "rate_30", "points_30", "rate_15")

RULES = (
    Rule("missing_week", "more than ten days between consecutive published weeks", lambda f: pl.col("days_since_prev") > 10),
    Rule("implausible_rate", "a 30 year rate outside 2 to 20 percent", lambda f: (pl.col("rate_30") < 2.0) | (pl.col("rate_30") > 20.0)),
)

DIGEST = contract_digest("pmms", FIELDS, RULES)


def parse(external: Path) -> pl.DataFrame:
    import openpyxl

    path = require(external / "pmms" / "historicalweeklydata.xlsx", "the PMMS weekly history")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = wb.worksheets[0]
    rows: list[dict[str, object]] = []
    for values in sheet.iter_rows(values_only=True):
        week = values[0]
        if not isinstance(week, dt.datetime | dt.date):
            continue
        rate_30 = values[1]
        if rate_30 is None or not isinstance(rate_30, int | float):
            continue
        day = week.date() if isinstance(week, dt.datetime) else week
        rows.append(
            {
                "week": day,
                "rate_30": float(rate_30),
                "points_30": float(values[2]) if isinstance(values[2], int | float) else None,
                "rate_15": float(values[3]) if isinstance(values[3], int | float) else None,
            }
        )
    if not rows:
        raise ContractError("the PMMS workbook held no weekly rows")
    frame = pl.DataFrame(
        rows, schema={"week": pl.Date, "rate_30": pl.Float64, "points_30": pl.Float64, "rate_15": pl.Float64}
    ).sort("week")
    frame = frame.with_columns(
        pl.col("week").dt.year().cast(pl.Int64).alias("year"),
        pl.col("week").dt.quarter().cast(pl.Int64).alias("quarter"),
    ).with_columns(
        (pl.col("year").cast(pl.Utf8) + pl.lit("Q") + pl.col("quarter").cast(pl.Utf8)).alias("period"),
        (pl.col("week") - pl.col("week").shift(1)).dt.total_days().alias("days_since_prev"),
    )
    return frame


def quarantine(frame: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    flagged, report = apply_rules(frame, RULES, "pmms", "year")
    return flagged.select([*FIELDS, *[c for c in flagged.columns if c.startswith("q_")], "quarantined"]), report.frame()


def quarterly(frame: pl.DataFrame) -> pl.DataFrame:
    """The quarterly average of the weekly 30 year rate, and the number of weeks it averages."""
    return (
        frame.group_by(["year", "quarter", "period"])
        .agg(pl.col("rate_30").mean().alias("rate"), pl.len().alias("weeks"))
        .sort(["year", "quarter"])
    )


def latest(frame: pl.DataFrame) -> tuple[dt.date, float]:
    row = frame.sort("week").tail(1)
    return row["week"][0], float(row["rate_30"][0])
