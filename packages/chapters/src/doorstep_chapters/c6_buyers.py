"""Chapter 6, who still buys: the buyer pool from the purchase subset of the HMDA extract.

The median purchase borrower income as a ratio of the metro median household income by year; the share
of purchase loans to borrowers under 35; the share with income above twice the metro median; the median
property value to borrower income; the rate spread distribution. The denial question is not asked: fair
lending is the Day 9 build. Intervals are by bootstrap over lenders, because a lender's book is one
underwriting policy, not thousands of independent draws. The extract reports income in thousands and
the chapter reads histograms per lender in five thousand dollar bins, so no loan is ever held in memory
here and the median is exact to the bin. The simulator plants a known shift in the borrower income ratio
and in the under 35 share after the shock, and the recovery study grades the bootstrap's coverage.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl
from doorstep_core.config import POLICY, Policy
from doorstep_core.formats import format_value
from doorstep_sim.lenders import UNDER_35_SHIFT
from doorstep_sim.metros import World
from doorstep_stats.bootstrap import Interval, percentile_interval, resample_blocks

from doorstep_chapters.common import Branch, ChapterResult, Figure, Grade, ensure
from doorstep_chapters.panel import INCOME_BIN_K, Borrowers, Panel, from_world

NUMBER = 6
SLUG = "buyers"
TITLE = "Who still buys"
BASE_YEAR = 2019

SQL = """
select year,
       sum(loans) as purchase_loans,
       sum(under_35) * 1.0 / sum(loans) as under_35_share,
       sum(over_2x) * 1.0 / sum(loans) as over_2x_share
from mart_borrowers_income
group by year
order by year
""".strip()


def plan(policy: Policy = POLICY) -> dict[str, Any]:
    return {
        "chapter": NUMBER,
        "slug": SLUG,
        "claim": "The purchase borrower of the latest year is richer relative to the local median and older than the "
        "borrower of 2019.",
        "estimator": "purchase loans (purpose 1) on principal residences; borrower income over the metro median household "
        "income of the nearest census year, median across loans from five thousand dollar bins; shares under 35 and "
        "above twice the median; median property value to income from quarter point bins; rate spread deciles",
        "interval": f"bootstrap over lenders, {policy.bootstrap_replicates} replicates, within year",
        "split": {"base_year": BASE_YEAR, "report_on": "the latest published HMDA year"},
        "family": "two differences (ratio and under 35 share), each on its own interval; no correction",
        "operating_points": {
            "base_year": BASE_YEAR,
            "largest_metros": policy.largest_metros,
            "income_bin_thousands": INCOME_BIN_K,
        },
        "message_rule": "richer_older: both difference intervals exclude zero in the stated direction; richer: only the ratio does; "
        "older: only the under 35 share does; null: neither",
    }


def message_rule(
    ratio_diff: Interval, under35_diff: Interval, latest_year: int, movers: list[tuple[str, float]]
) -> Branch:
    richer = ratio_diff.low > 0.0
    older = under35_diff.high < 0.0
    named = "; ".join(f"{name} {format_value(d, 'sfloat2')}" for name, d in movers[:3])
    tail = f" The ratio moved most in {named}." if named else ""
    if richer and older:
        return Branch(
            "richer_older",
            f"The buyer is richer and older than in {BASE_YEAR}: the borrower earns {format_value(ratio_diff.estimate, 'sfloat2')} more of the local "
            f"median income (interval {format_value(ratio_diff.low, 'sfloat2')} to {format_value(ratio_diff.high, 'sfloat2')}) and the under 35 share fell "
            f"{format_value(-under35_diff.estimate, 'apts1')} (interval {format_value(under35_diff.low, 'pts1')} to {format_value(under35_diff.high, 'pts1')}) by {latest_year}."
            + tail,
        )
    if richer:
        return Branch(
            "richer",
            f"The buyer is richer than in {BASE_YEAR} by {format_value(ratio_diff.estimate, 'sfloat2')} of the local median income (interval "
            f"{format_value(ratio_diff.low, 'sfloat2')} to {format_value(ratio_diff.high, 'sfloat2')}), but not measurably older: the under 35 share moved "
            f"{format_value(under35_diff.estimate, 'pts1')} with an interval that includes zero." + tail,
        )
    if older:
        return Branch(
            "older",
            f"The buyer is older than in {BASE_YEAR} (under 35 share {format_value(under35_diff.estimate, 'pts1')}, interval "
            f"{format_value(under35_diff.low, 'pts1')} to {format_value(under35_diff.high, 'pts1')}) but not measurably richer relative to the local median."
            + tail,
        )
    return Branch(
        "null",
        f"Relative to {BASE_YEAR} the buyer pool has not measurably moved: the income ratio changed {format_value(ratio_diff.estimate, 'sfloat2')} and the "
        f"under 35 share {format_value(under35_diff.estimate, 'pts1')}, both with intervals that include zero."
        + tail,
    )


def metro_median_for_year(panel: Panel, year: int) -> pl.DataFrame:
    """The metro median household income of the nearest census year at or before ``year``, else after."""
    med = (
        panel.metro_year.filter(pl.col("median_income").is_not_null())
        .select("cbsa_code", "year", "median_income")
        .sort(["cbsa_code", "year"])
    )
    before = (
        med.filter(pl.col("year") <= year)
        .group_by("cbsa_code")
        .agg(pl.col("median_income").last().alias("before"))
    )
    after = (
        med.filter(pl.col("year") > year)
        .group_by("cbsa_code")
        .agg(pl.col("median_income").first().alias("after"))
    )
    out = before.join(after, on="cbsa_code", how="full", coalesce=True)
    return (
        out.with_columns(pl.coalesce(["before", "after"]).alias("metro_median"))
        .select("cbsa_code", "metro_median")
        .filter(pl.col("metro_median").is_not_null())
    )


def _ratio_rows(panel: Panel, year: int, *, cbsa: str | None = None) -> pl.DataFrame:
    ensure(panel.borrowers is not None, "chapter 6 needs the borrower histograms")
    assert panel.borrowers is not None
    inc = panel.borrowers.income.filter(pl.col("year") == year)
    if cbsa is not None:
        inc = inc.filter(pl.col("cbsa_code") == cbsa)
    inc = inc.join(metro_median_for_year(panel, year), on="cbsa_code", how="inner")
    return inc.with_columns(
        ((pl.col("income_bin") + INCOME_BIN_K / 2.0) * 1000.0 / pl.col("metro_median")).alias("ratio")
    ).sort("ratio")


def _weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    """Values must be sorted ascending."""
    total = weights.sum()
    if total <= 0:
        return float("nan")
    cs = np.cumsum(weights)
    i = int(np.searchsorted(cs, 0.5 * total, side="left"))
    return float(values[min(i, values.shape[0] - 1)])


def _median_replicates(
    values: np.ndarray, weights: np.ndarray, lender_idx: np.ndarray, mult: np.ndarray, *, chunk: int = 20
) -> np.ndarray:
    """Weighted medians over bootstrap replicates; ``mult`` is (replicates, lenders)."""
    out = np.empty(mult.shape[0])
    total_rows = values.shape[0]
    for start in range(0, mult.shape[0], chunk):
        m = mult[start : start + chunk]
        w = weights[None, :] * m[:, lender_idx]
        cs = np.cumsum(w, axis=1)
        half = 0.5 * cs[:, -1]
        idx = np.array([int(np.searchsorted(cs[b], half[b], side="left")) for b in range(cs.shape[0])])
        out[start : start + chunk] = values[np.minimum(idx, total_rows - 1)]
    return out


def _lender_index(frame: pl.DataFrame) -> tuple[np.ndarray, int]:
    lenders = sorted(frame["lei"].unique().to_list())
    lookup = {k: i for i, k in enumerate(lenders)}
    return np.array([lookup[k] for k in frame["lei"].to_list()], dtype=np.int64), len(lenders)


def ratio_interval(
    panel: Panel, year: int, policy: Policy, *, cbsa: str | None = None, replicates: int | None = None
) -> tuple[Interval, np.ndarray]:
    rows = _ratio_rows(panel, year, cbsa=cbsa)
    ensure(rows.height > 0, f"chapter 6 has no purchase loans in {year}")
    values = rows["ratio"].to_numpy().astype(np.float64)
    weights = rows["loans"].to_numpy().astype(np.float64)
    idx, n_lenders = _lender_index(rows)
    estimate = _weighted_median(values, weights)
    reps = replicates or policy.bootstrap_replicates
    if n_lenders < 2:
        return Interval(estimate, estimate, estimate, 0, n_lenders), np.full(reps, estimate)
    mult = resample_blocks(
        n_lenders, replicates=reps, seed=policy.seed, label=f"ch6-ratio-{year}-{cbsa or 'all'}"
    ).astype(np.float64)
    draws = _median_replicates(values, weights, idx, mult)
    return percentile_interval(estimate, draws, level=policy.interval_level, blocks=n_lenders), draws


def share_interval(
    panel: Panel,
    year: int,
    column: str,
    policy: Policy,
    *,
    cbsa: str | None = None,
    replicates: int | None = None,
) -> tuple[Interval, np.ndarray]:
    assert panel.borrowers is not None
    inc = panel.borrowers.income.filter(pl.col("year") == year)
    if cbsa is not None:
        inc = inc.filter(pl.col("cbsa_code") == cbsa)
    by_lender = inc.group_by("lei").agg(pl.col("loans").sum(), pl.col(column).sum()).sort("lei")
    ensure(by_lender.height > 0, f"chapter 6 has no loans for {column} in {year}")
    num = by_lender[column].to_numpy().astype(np.float64)
    den = by_lender["loans"].to_numpy().astype(np.float64)
    estimate = float(num.sum() / den.sum())
    reps = replicates or policy.bootstrap_replicates
    if by_lender.height < 2:
        return Interval(estimate, estimate, estimate, 0, by_lender.height), np.full(reps, estimate)
    mult = resample_blocks(
        by_lender.height, replicates=reps, seed=policy.seed, label=f"ch6-{column}-{year}-{cbsa or 'all'}"
    ).astype(np.float64)
    draws = (mult @ num) / (mult @ den)
    return percentile_interval(estimate, draws, level=policy.interval_level, blocks=by_lender.height), draws


def vti_interval(
    borrowers: Borrowers, year: int, policy: Policy, *, replicates: int | None = None
) -> Interval:
    rows = borrowers.vti.filter(pl.col("year") == year).sort("vti_bin")
    ensure(rows.height > 0, f"chapter 6 has no value to income bins in {year}")
    values = (rows["vti_bin"].to_numpy() + 0.125).astype(np.float64)
    weights = rows["loans"].to_numpy().astype(np.float64)
    idx, n_lenders = _lender_index(rows)
    estimate = _weighted_median(values, weights)
    if n_lenders < 2:
        return Interval(estimate, estimate, estimate, 0, n_lenders)
    mult = resample_blocks(
        n_lenders,
        replicates=replicates or policy.bootstrap_replicates,
        seed=policy.seed,
        label=f"ch6-vti-{year}",
    ).astype(np.float64)
    return percentile_interval(
        estimate,
        _median_replicates(values, weights, idx, mult),
        level=policy.interval_level,
        blocks=n_lenders,
    )


def spread_deciles(borrowers: Borrowers, year: int) -> tuple[float, float, float]:
    rows = borrowers.spread.filter(pl.col("year") == year).sort("spread_bin")
    if rows.height == 0:
        return float("nan"), float("nan"), float("nan")
    values = rows["spread_bin"].to_numpy().astype(np.float64) + 0.0625
    weights = rows["loans"].to_numpy().astype(np.float64)
    cs = np.cumsum(weights) / weights.sum()
    out = []
    for q in (0.1, 0.5, 0.9):
        i = int(np.searchsorted(cs, q, side="left"))
        out.append(float(values[min(i, values.shape[0] - 1)]))
    return out[0], out[1], out[2]


def _difference(a: Interval, a_draws: np.ndarray, b: Interval, b_draws: np.ndarray, level: float) -> Interval:
    return percentile_interval(
        a.estimate - b.estimate, a_draws - b_draws, level=level, blocks=a.blocks + b.blocks
    )


def estimate(panel: Panel, policy: Policy = POLICY, *, replicates: int | None = None) -> ChapterResult:
    ensure(panel.borrowers is not None, "chapter 6 needs the borrower histograms")
    assert panel.borrowers is not None
    years = sorted(int(y) for y in panel.borrowers.income["year"].unique().to_list())
    ensure(BASE_YEAR in years, f"chapter 6 needs {BASE_YEAR} in the loans")
    latest = years[-1]
    ensure(latest > BASE_YEAR, "chapter 6 needs a year after the base year")
    by_year: dict[int, dict[str, Any]] = {}
    draws_ratio: dict[int, np.ndarray] = {}
    draws_u35: dict[int, np.ndarray] = {}
    for y in years:
        ratio, dr = ratio_interval(panel, y, policy, replicates=replicates)
        u35, du = share_interval(panel, y, "under_35", policy, replicates=replicates)
        over, _ = share_interval(panel, y, "over_2x", policy, replicates=replicates)
        vti = vti_interval(panel.borrowers, y, policy, replicates=replicates)
        p10, p50, p90 = spread_deciles(panel.borrowers, y)
        loans = int(panel.borrowers.income.filter(pl.col("year") == y)["loans"].sum())
        lenders = int(panel.borrowers.income.filter(pl.col("year") == y)["lei"].n_unique())
        by_year[y] = {
            "ratio": ratio,
            "under_35": u35,
            "over_2x": over,
            "vti": vti,
            "spread": (p10, p50, p90),
            "loans": loans,
            "lenders": lenders,
        }
        draws_ratio[y] = dr
        draws_u35[y] = du
    ratio_diff = _difference(
        by_year[latest]["ratio"],
        draws_ratio[latest],
        by_year[BASE_YEAR]["ratio"],
        draws_ratio[BASE_YEAR],
        policy.interval_level,
    )
    u35_diff = _difference(
        by_year[latest]["under_35"],
        draws_u35[latest],
        by_year[BASE_YEAR]["under_35"],
        draws_u35[BASE_YEAR],
        policy.interval_level,
    )

    # The largest metros: the ratio in the base and latest years with lender intervals, and the movers
    loans_by_metro = (
        panel.borrowers.income.filter(pl.col("year") == latest)
        .group_by("cbsa_code")
        .agg(pl.col("loans").sum())
        .sort("loans", descending=True)
    )
    largest = loans_by_metro.head(policy.largest_metros)["cbsa_code"].to_list()
    titles = {
        r["cbsa_code"]: r["cbsa_title"]
        for r in panel.metro_year.select("cbsa_code", "cbsa_title").unique().iter_rows(named=True)
    }
    metro_rows: list[list[Any]] = []
    movers: list[tuple[str, float]] = []
    metro_frame_rows: list[dict[str, Any]] = []
    for code in largest:
        try:
            base, bd = ratio_interval(panel, BASE_YEAR, policy, cbsa=code, replicates=replicates)
            now, nd = ratio_interval(panel, latest, policy, cbsa=code, replicates=replicates)
        except Exception:
            continue
        diff = _difference(now, nd, base, bd, policy.interval_level)
        u35_now, _ = share_interval(panel, latest, "under_35", policy, cbsa=code, replicates=replicates)
        name = str(titles.get(code, code)).split(",")[0]
        metro_rows.append(
            [
                titles.get(code, code),
                base.estimate,
                now.estimate,
                now.low,
                now.high,
                diff.estimate,
                u35_now.estimate,
            ]
        )
        metro_frame_rows.append(
            {
                "cbsa_code": code,
                "cbsa_title": titles.get(code, code),
                "ratio_base": base.estimate,
                "ratio_latest": now.estimate,
                "ratio_low": now.low,
                "ratio_high": now.high,
                "change": diff.estimate,
                "change_low": diff.low,
                "change_high": diff.high,
                "under_35_latest": u35_now.estimate,
            }
        )
        if diff.low > 0.0 or diff.high < 0.0:
            movers.append((name, diff.estimate))
    movers.sort(key=lambda kv: -abs(kv[1]))
    branch = message_rule(ratio_diff, u35_diff, latest, movers)

    r = ChapterResult(
        number=NUMBER,
        slug=SLUG,
        source=panel.source,
        population=f"every purchase loan on a principal residence in the extract, {years[0]} to {latest} ({by_year[latest]['loans']:,} loans from {by_year[latest]['lenders']:,} lenders in {latest})",
        branch=branch.name,
        message=branch.text,
        reported_years=[latest],
    )
    r.put("ch6.base_year", BASE_YEAR, "year")
    r.put("ch6.latest_year", latest, "year")
    r.put("ch6.replicates", ratio_diff.replicates, "int")
    for y in (BASE_YEAR, latest):
        tag = "base" if y == BASE_YEAR else "latest"
        v = by_year[y]
        r.put(f"ch6.{tag}.loans", v["loans"], "int")
        r.put(f"ch6.{tag}.lenders", v["lenders"], "int")
        r.put(f"ch6.{tag}.ratio", v["ratio"].estimate, "ratio2", model="borrowers")
        r.put(f"ch6.{tag}.ratio.low", v["ratio"].low, "ratio2", model="bootstrap")
        r.put(f"ch6.{tag}.ratio.high", v["ratio"].high, "ratio2", model="bootstrap")
        r.put(f"ch6.{tag}.under_35", v["under_35"].estimate, "pct1", model="borrowers")
        r.put(f"ch6.{tag}.under_35.low", v["under_35"].low, "pct1", model="bootstrap")
        r.put(f"ch6.{tag}.under_35.high", v["under_35"].high, "pct1", model="bootstrap")
        r.put(f"ch6.{tag}.over_2x", v["over_2x"].estimate, "pct1", model="borrowers")
        r.put(f"ch6.{tag}.vti", v["vti"].estimate, "ratio2", model="borrowers")
        r.put(f"ch6.{tag}.spread.p10", v["spread"][0], "rate2", model="borrowers")
        r.put(f"ch6.{tag}.spread.p50", v["spread"][1], "rate2", model="borrowers")
        r.put(f"ch6.{tag}.spread.p90", v["spread"][2], "rate2", model="borrowers")
    r.put("ch6.ratio_diff", ratio_diff.estimate, "sfloat2", model="bootstrap")
    r.put("ch6.ratio_diff.low", ratio_diff.low, "sfloat2", model="bootstrap")
    r.put("ch6.ratio_diff.high", ratio_diff.high, "sfloat2", model="bootstrap")
    r.put("ch6.under_35_diff", u35_diff.estimate, "pts1", model="bootstrap")
    r.put("ch6.under_35_diff.low", u35_diff.low, "pts1", model="bootstrap")
    r.put("ch6.under_35_diff.high", u35_diff.high, "pts1", model="bootstrap")
    r.put(
        "ch6.over_2x_diff",
        by_year[latest]["over_2x"].estimate - by_year[BASE_YEAR]["over_2x"].estimate,
        "pts1",
        model="borrowers",
    )
    r.put("ch6.largest", len(metro_rows), "int")
    r.put("ch6.movers", len(movers), "int", model="bootstrap")
    r.put("ch6.top_mover", movers[0][0] if movers else "none", "text")
    r.put("ch6.top_mover.change", movers[0][1] if movers else None, "sfloat2", model="bootstrap")
    r.put("ch6.branch", branch.name, "text")
    r.put("ch6.message", branch.text, "text")
    r.put_table(
        "ch6.by_year",
        [
            "Year",
            "Loans",
            "Lenders",
            "Income ratio",
            "Low",
            "High",
            "Under 35",
            "Above twice the median",
            "Value to income",
            "Spread p50",
        ],
        ["int", "int", "int", "ratio2", "ratio2", "ratio2", "pct1", "pct1", "ratio2", "rate2"],
        [
            [
                y,
                v["loans"],
                v["lenders"],
                v["ratio"].estimate,
                v["ratio"].low,
                v["ratio"].high,
                v["under_35"].estimate,
                v["over_2x"].estimate,
                v["vti"].estimate,
                v["spread"][1],
            ]
            for y, v in by_year.items()
        ],
        model="bootstrap",
    )
    if metro_rows:
        r.put_table(
            "ch6.largest_metros",
            ["Metro", f"Ratio {BASE_YEAR}", f"Ratio {latest}", "Low", "High", "Change", f"Under 35 {latest}"],
            ["text", "ratio2", "ratio2", "ratio2", "ratio2", "sfloat2", "pct1"],
            metro_rows,
            model="bootstrap",
        )
    series = pl.DataFrame(
        {
            "year": list(by_year),
            "loans": [v["loans"] for v in by_year.values()],
            "ratio": [v["ratio"].estimate for v in by_year.values()],
            "ratio_low": [v["ratio"].low for v in by_year.values()],
            "ratio_high": [v["ratio"].high for v in by_year.values()],
            "under_35": [v["under_35"].estimate for v in by_year.values()],
            "under_35_low": [v["under_35"].low for v in by_year.values()],
            "under_35_high": [v["under_35"].high for v in by_year.values()],
            "over_2x": [v["over_2x"].estimate for v in by_year.values()],
            "vti": [v["vti"].estimate for v in by_year.values()],
            "spread_p10": [v["spread"][0] for v in by_year.values()],
            "spread_p50": [v["spread"][1] for v in by_year.values()],
            "spread_p90": [v["spread"][2] for v in by_year.values()],
        }
    )
    r.marts["ch6_by_year"] = series
    r.marts["ch6_largest_metros"] = pl.DataFrame(metro_frame_rows) if metro_frame_rows else series.head(0)
    r.marts["ch6_spread"] = panel.borrowers.spread
    r.figure = Figure(
        title=branch.text,
        subtitle="Purchase borrower income over the local median, and the share of buyers under 35, by year, with lender bootstrap intervals",
        sql=SQL,
        frames={"series": series, "metros": r.marts["ch6_largest_metros"], "spread": panel.borrowers.spread},
        model="bootstrap",
        callout=f"income ratio {format_value(by_year[BASE_YEAR]['ratio'].estimate, 'ratio2')} in {BASE_YEAR}, {format_value(by_year[latest]['ratio'].estimate, 'ratio2')} in {latest}",
    )
    r.method = {
        "estimator": "weighted medians over five thousand dollar income bins per lender; shares as ratios of sums",
        "split": f"base year {BASE_YEAR}; reported on {latest}",
        "interval": f"bootstrap over lenders within year, {ratio_diff.replicates} replicates",
        "family": "two differences on their own intervals",
    }
    r.pushback = (
        "The HMDA income is the income the lender used, not the household's; a co-borrower or a self employed buyer is "
        "reported differently by different lenders, which is why the interval resamples lenders. The ratio compares buyers "
        "with the metro median household in the nearest census year, and the census has no 2020 release, so 2020 loans are "
        "compared with 2019 incomes. The purchase subset leaves out buyers who paid cash, who are the richest buyers of all."
    )
    return r


# Recovery on the simulator


def simulate_estimate(world: World, policy: Policy = POLICY, *, replicates: int = 100) -> list[Grade]:
    panel = from_world(world, policy, with_loans=True)
    latest = int(panel.metro_year.filter(pl.col("purchase_loans").is_not_null())["year"].max())
    ratio_now, dn = ratio_interval(panel, latest, policy, replicates=replicates)
    ratio_base, db = ratio_interval(panel, BASE_YEAR, policy, replicates=replicates)
    diff = _difference(ratio_now, dn, ratio_base, db, policy.interval_level)
    u_now, un = share_interval(panel, latest, "under_35", policy, replicates=replicates)
    u_base, ub = share_interval(panel, BASE_YEAR, "under_35", policy, replicates=replicates)
    u_diff = _difference(u_now, un, u_base, ub, policy.interval_level)
    return [
        Grade("borrower_ratio_shift", diff.estimate, world.truth.borrower_ratio_shift, diff.low, diff.high),
        Grade("under_35_shift", u_diff.estimate, UNDER_35_SHIFT, u_diff.low, u_diff.high),
    ]
