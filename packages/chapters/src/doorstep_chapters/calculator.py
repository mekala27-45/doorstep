"""The marts the affordability calculator reads, written from the panel after the chapters run.

``calc_metros``: one row per metropolitan area with the latest anchored value, the latest census income
and rent, the income brackets, and the metro's own appreciation and rent growth history for the breakeven
paths. ``calc_quarters``: the anchored value and the rate by quarter since 2015, which the scorer reads
when the next quarter publishes. The default rate is the latest weekly PMMS rate when the derived file
is there, else the latest quarterly average. Nothing here is about a person.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
from doorstep_core.config import INCOME_BRACKETS, POLICY, Policy

from doorstep_chapters.c8_decision import histories
from doorstep_chapters.panel import Panel

FIRST_QUARTER_YEAR = 2015


def default_rate(derived: Path, panel: Panel) -> tuple[float, str]:
    weekly = derived / "pmms_weekly.parquet"
    if weekly.exists():
        w = pl.read_parquet(weekly)
        if "rate_30" in w.columns and "week" in w.columns and w.height:
            last = w.filter(pl.col("rate_30").is_not_null()).sort("week").row(-1, named=True)
            return float(last["rate_30"]), f"week of {last['week']}"
    q = panel.metro_quarter.filter(pl.col("rate").is_not_null()).sort(["year", "quarter"])
    return float(q["rate"][-1]), f"quarter {q['period'][-1]}"


def build(
    panel: Panel, derived: Path, policy: Policy = POLICY
) -> tuple[pl.DataFrame, pl.DataFrame, dict[str, object]]:
    year = panel.latest_acs_year
    my = (
        panel.metropolitan()
        .filter(
            (pl.col("year") == year)
            & pl.col("median_income").is_not_null()
            & pl.col("median_rent").is_not_null()
            & pl.col("value_anchored").is_not_null()
        )
        .sort("cbsa_code")
    )
    latest_q = (
        panel.metro_quarter.filter(pl.col("value_anchored").is_not_null() & pl.col("rate").is_not_null())
        .sort(["cbsa_code", "year", "quarter"])
        .group_by("cbsa_code", maintain_order=True)
        .agg(
            pl.col("period").last().alias("latest_period"),
            pl.col("value_anchored").last().alias("value_latest"),
            pl.col("rate").last().alias("rate_latest"),
        )
    )
    rate, rate_source = default_rate(derived, panel)
    hist = histories(panel)
    counts: dict[str, list[float]] = {}
    for code, sub in panel.brackets.filter(pl.col("year") == year).group_by("cbsa_code"):
        c = [0.0] * (len(INCOME_BRACKETS) + 1)
        for k, h in zip(sub["bracket"].to_list(), sub["households"].to_list(), strict=True):
            if 0 <= int(k) < len(c) and h is not None:
                c[int(k)] = float(h)
        if sum(c) > 0:
            counts[str(code[0])] = c
    rows = my.join(latest_q, on="cbsa_code", how="inner")
    metros = rows.select(
        "cbsa_code",
        "cbsa_title",
        "kind",
        "households",
        "owner_households",
        "renter_households",
        pl.lit(year).alias("income_year"),
        "median_income",
        "renter_median_income",
        "median_rent",
        "latest_period",
        "value_latest",
        "rate_latest",
        pl.lit(rate).alias("rate_default"),
        pl.lit(rate_source).alias("rate_default_source"),
    ).with_columns(
        pl.Series(
            "brackets", [counts.get(c) for c in rows["cbsa_code"].to_list()], dtype=pl.List(pl.Float64)
        ),
        pl.Series(
            "appreciation",
            [list(map(float, hist[c][0])) if c in hist else None for c in rows["cbsa_code"].to_list()],
            dtype=pl.List(pl.Float64),
        ),
        pl.Series(
            "rent_growth",
            [list(map(float, hist[c][1])) if c in hist else None for c in rows["cbsa_code"].to_list()],
            dtype=pl.List(pl.Float64),
        ),
    )
    quarters = (
        panel.metro_quarter.filter(
            (pl.col("year") >= FIRST_QUARTER_YEAR)
            & pl.col("value_anchored").is_not_null()
            & pl.col("rate").is_not_null()
            & pl.col("cbsa_code").is_in(metros["cbsa_code"].to_list())
        )
        .select("cbsa_code", "year", "quarter", "period", "value_anchored", "rate")
        .sort(["cbsa_code", "year", "quarter"])
    )
    meta = {
        "income_year": year,
        "latest_period": panel.latest_period,
        "rate_default": rate,
        "rate_default_source": rate_source,
        "metros": metros.height,
        "anchor_year": panel.anchor_year,
        "down_payment_share": policy.down_payment_share,
        "affordable_line": policy.affordable_line,
        "loan_term_years": policy.loan_term_years,
        "cost_model": policy.breakeven_cost_model,
    }
    return metros, quarters, meta


def write(panel: Panel, derived: Path, marts: Path, policy: Policy = POLICY) -> dict[str, object]:
    import json

    metros, quarters, meta = build(panel, derived, policy)
    marts.mkdir(parents=True, exist_ok=True)
    metros.write_parquet(marts / "calc_metros.parquet", compression="zstd")
    quarters.write_parquet(marts / "calc_quarters.parquet", compression="zstd")
    (marts / "calc_meta.json").write_text(json.dumps(meta, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return meta
