"""Chapter 1, the definition: affordable is a decision.

Two lines per metro and for the owner weighted national aggregate: the price of the median home as a
multiple of the median household income (the price story), and the share of that income the payment on
the median home takes at each year's rate (the payment story). The level comes from the regulator's
index anchored to the census median value in the anchor year; the interval comes from ten thousand
Monte Carlo draws over the census margins of error with the index held fixed. The message rule compares
the latest year's payment share with every earlier year, 2006 included, on the interval of the
difference. The anchor sensitivity table re-anchors every headline in 2015, 2017 and 2023, and the self
report check compares the census value with the transaction values in the HMDA extract, which is the
correction the simulator plants a known bias for.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl
from doorstep_core.config import AFFORDABLE_LINES, ANCHOR_YEARS, POLICY, Policy
from doorstep_core.formats import format_value
from doorstep_finance.mortgage import payment_on_price
from doorstep_sim.metros import World
from doorstep_stats.monte_carlo import draw_inputs

from doorstep_chapters.common import Branch, ChapterResult, Figure, Grade, ensure, split_for, weighted_mean
from doorstep_chapters.panel import Panel, from_world

NUMBER = 1
SLUG = "definition"
TITLE = "Affordable is a decision"
PEAK_YEAR = 2006

SQL = """
select year,
       sum(value_anchored * owner_households) / sum(owner_households) as median_home,
       sum(price_to_income * owner_households) / sum(owner_households) as price_to_income,
       sum(payment_share * owner_households) / sum(owner_households) as payment_share
from mart_metro_year
where kind = 'metropolitan' and payment_share is not null and owner_households > 0
group by year
order by year
""".strip()


def plan(policy: Policy = POLICY) -> dict[str, Any]:
    return {
        "chapter": NUMBER,
        "slug": SLUG,
        "claim": "The payment share of income in the latest year exceeds every earlier year including 2006, "
        "while the price to income ratio took the whole window to move as far.",
        "estimator": "FHFA all transactions index anchored to the ACS median value in the anchor year; payment at "
        "the quarterly PMMS rate on ninety percent of the value over thirty years; twelve payments over the "
        "median household income; owner household weighted national aggregate",
        "interval": f"percentile interval of {policy.monte_carlo_draws} Monte Carlo draws over the ACS margins of error "
        "(income and anchor value), index held fixed",
        "split": split_for(policy)
        | {"note": "the baseline years are the fitting years; the headline is the latest year"},
        "family": "one comparison, the latest year against 2006; no correction",
        "operating_points": {
            "anchor_year": policy.anchor_year,
            "anchor_neighbours": list(ANCHOR_YEARS),
            "affordable_line": policy.affordable_line,
            "line_neighbours": list(AFFORDABLE_LINES),
            "down_payment_share": policy.down_payment_share,
            "loan_term_years": policy.loan_term_years,
        },
        "message_rule": "exceeds: the interval of (latest minus 2006) lies above zero and the latest point estimate exceeds "
        "every earlier year; fails_year: a named earlier year is not exceeded; null: the interval includes zero",
    }


def message_rule(
    diff_low: float, diff_high: float, failing_year: int | None, latest_year: int, diff: float
) -> Branch:
    if failing_year is not None and failing_year != PEAK_YEAR:
        return Branch(
            "fails_year",
            f"The payment share of {latest_year} does not exceed {failing_year}; the payment story is not yet the "
            f"largest the window has seen.",
        )
    if diff_low > 0.0:
        return Branch(
            "exceeds",
            f"The payment story happened in eighteen months while the price story took twenty years: the share of "
            f"income the median home takes in {latest_year} sits {format_value(diff, 'pts1')} above 2006 "
            f"(interval {format_value(diff_low, 'pts1')} to {format_value(diff_high, 'pts1')}).",
        )
    if diff_high < 0.0:
        return Branch(
            "below_2006",
            f"The payment share of {latest_year} sits below 2006 by {format_value(-diff, 'apts1')}; the 2006 peak "
            f"still stands.",
        )
    return Branch(
        "null",
        f"The payment share of {latest_year} and that of 2006 cannot be told apart: the interval of the difference "
        f"({format_value(diff_low, 'pts1')} to {format_value(diff_high, 'pts1')}) includes zero.",
    )


def _rate_factor(rate: float, policy: Policy) -> float:
    """Twelve payments on ninety percent of one dollar at this rate: payment share = value * factor / income."""
    return 12.0 * payment_on_price(1.0, rate, policy.down_payment_share, policy.loan_term_years)


def national_series(
    panel: Panel, policy: Policy = POLICY, *, draws: int | None = None, seed: int | None = None
) -> pl.DataFrame:
    """The owner weighted national aggregate by year with its Monte Carlo interval."""
    my = panel.metropolitan().filter(
        pl.col("payment_share").is_not_null()
        & pl.col("owner_households").is_not_null()
        & (pl.col("owner_households") > 0)
        & pl.col("median_income_moe").is_not_null()
        & pl.col("value_anchored_moe").is_not_null()
    )
    ensure(my.height > 0, "chapter 1 has no metro year with a payment share")
    n_draws = draws or policy.monte_carlo_draws
    rows: list[dict[str, float | int | None]] = []
    for year in sorted(my["year"].unique().to_list()):
        sub = my.filter(pl.col("year") == year).sort("cbsa_code")
        w = sub["owner_households"].to_numpy().astype(np.float64)
        w = w / w.sum()
        rate = float(sub["rate"][0])
        factor = _rate_factor(rate, policy)
        d = draw_inputs(
            {"value": sub["value_anchored"].to_numpy(), "income": sub["median_income"].to_numpy()},
            {"value": sub["value_anchored_moe"].to_numpy(), "income": sub["median_income_moe"].to_numpy()},
            draws=n_draws,
            seed=seed or policy.seed,
            label=f"ch1-{year}",
            floor=1000.0,
        )
        share = (d.values["value"] * factor / d.values["income"]) @ w
        pti = (d.values["value"] / d.values["income"]) @ w
        rows.append(
            {
                "year": int(year),
                "metros": int(sub.height),
                "rate": rate,
                "median_home": float(sub["value_anchored"].to_numpy() @ w),
                "price_to_income": float(
                    sub["value_anchored"].to_numpy() / sub["median_income"].to_numpy() @ w
                ),
                "price_to_income_low": float(np.quantile(pti, 0.025)),
                "price_to_income_high": float(np.quantile(pti, 0.975)),
                "payment_share": float(sub["payment_share"].to_numpy() @ w),
                "payment_share_low": float(np.quantile(share, 0.025)),
                "payment_share_high": float(np.quantile(share, 0.975)),
                "draws": int(n_draws),
            }
        )
    return pl.DataFrame(rows)


def _difference_interval(
    panel: Panel, year_a: int, year_b: int, policy: Policy, draws: int, seed: int
) -> tuple[float, float, float]:
    """(latest minus earlier) national payment share with its Monte Carlo interval, drawn jointly so the
    anchor draw is shared between the two years as it is in the series."""
    my = panel.metropolitan().filter(pl.col("payment_share").is_not_null() & (pl.col("owner_households") > 0))
    a = my.filter(pl.col("year") == year_a).sort("cbsa_code")
    b = my.filter(pl.col("year") == year_b).sort("cbsa_code")
    common = sorted(set(a["cbsa_code"].to_list()) & set(b["cbsa_code"].to_list()))
    ensure(len(common) >= 2, f"chapter 1 needs metros present in both {year_a} and {year_b}")
    a = a.filter(pl.col("cbsa_code").is_in(common)).sort("cbsa_code")
    b = b.filter(pl.col("cbsa_code").is_in(common)).sort("cbsa_code")
    wa = a["owner_households"].to_numpy().astype(np.float64)
    wb = b["owner_households"].to_numpy().astype(np.float64)
    wa, wb = wa / wa.sum(), wb / wb.sum()
    fa, fb = _rate_factor(float(a["rate"][0]), policy), _rate_factor(float(b["rate"][0]), policy)
    # One anchor draw per metro moves both years through the index ratio; incomes are drawn per year.
    d = draw_inputs(
        {
            "value_a": a["value_anchored"].to_numpy(),
            "income_a": a["median_income"].to_numpy(),
            "income_b": b["median_income"].to_numpy(),
        },
        {
            "value_a": a["value_anchored_moe"].to_numpy(),
            "income_a": a["median_income_moe"].to_numpy(),
            "income_b": b["median_income_moe"].to_numpy(),
        },
        draws=draws,
        seed=seed,
        label=f"ch1-diff-{year_a}-{year_b}",
        floor=1000.0,
    )
    scale = b["value_anchored"].to_numpy() / a["value_anchored"].to_numpy()
    value_b = d.values["value_a"] * scale[None, :]
    share_a = (d.values["value_a"] * fa / d.values["income_a"]) @ wa
    share_b = (value_b * fb / d.values["income_b"]) @ wb
    diff = share_a - share_b
    point = float(a["payment_share"].to_numpy() @ wa - b["payment_share"].to_numpy() @ wb)
    return point, float(np.quantile(diff, 0.025)), float(np.quantile(diff, 0.975))


def headline(panel: Panel, policy: Policy = POLICY, *, draws: int | None = None) -> dict[str, Any]:
    """The numbers the message rule and the sensitivity table need, at one anchor."""
    n_draws = draws or policy.monte_carlo_draws
    series = national_series(panel, policy, draws=min(n_draws, 2000))
    latest = int(series["year"].max())
    first = int(series["year"].min())
    by_year = {int(r["year"]): r for r in series.iter_rows(named=True)}
    latest_share = float(by_year[latest]["payment_share"])
    earlier = [y for y in by_year if y < latest]
    failing = [y for y in sorted(earlier) if float(by_year[y]["payment_share"]) >= latest_share]
    peak_year = PEAK_YEAR if PEAK_YEAR in by_year else min(by_year)
    diff, low, high = _difference_interval(panel, latest, peak_year, policy, n_draws, policy.seed)
    my = panel.metropolitan()
    a = my.filter(pl.col("year") == latest).select("cbsa_code", pl.col("payment_share").alias("latest"))
    b = my.filter(pl.col("year") == peak_year).select("cbsa_code", pl.col("payment_share").alias("peak"))
    both = a.join(b, on="cbsa_code", how="inner").drop_nulls()
    above = int((both["latest"] > both["peak"]).sum())
    return {
        "latest_year": latest,
        "first_year": first,
        "peak_year": peak_year,
        "latest_share": latest_share,
        "peak_share": float(by_year[peak_year]["payment_share"]),
        "first_share": float(by_year[first]["payment_share"]),
        "latest_pti": float(by_year[latest]["price_to_income"]),
        "first_pti": float(by_year[first]["price_to_income"]),
        "peak_pti": float(by_year[peak_year]["price_to_income"]),
        "diff": diff,
        "diff_low": low,
        "diff_high": high,
        "failing_year": failing[0] if failing else None,
        "metros_compared": int(both.height),
        "metros_above_peak": above,
        "series": series,
    }


def self_report_check(panel: Panel) -> pl.DataFrame:
    """The census value over the transaction value in the anchor year, by metro: the planted factor in the
    simulator, the self report check on the real metros."""
    my = panel.metropolitan().filter(
        (pl.col("year") == panel.anchor_year)
        & pl.col("value_reported").is_not_null()
        & pl.col("purchase_median_value").is_not_null()
        & (pl.col("purchase_median_value") > 0)
    )
    return my.select(
        "cbsa_code",
        "cbsa_title",
        "value_reported",
        "purchase_median_value",
        (pl.col("value_reported") / pl.col("purchase_median_value")).alias("reported_over_transaction"),
    ).sort("cbsa_code")


def estimate(panel: Panel, policy: Policy = POLICY, *, draws: int | None = None) -> ChapterResult:
    h = headline(panel, policy, draws=draws)
    branch = message_rule(h["diff_low"], h["diff_high"], h["failing_year"], h["latest_year"], h["diff"])
    r = ChapterResult(
        number=NUMBER,
        slug=SLUG,
        source=panel.source,
        population=f"every metropolitan area with a census income and an anchored value, {h['first_year']} to {h['latest_year']}",
        branch=branch.name,
        message=branch.text,
        reported_years=[h["latest_year"]],
    )
    series: pl.DataFrame = h["series"]
    r.put("ch1.latest_year", h["latest_year"], "int")
    r.put("ch1.first_year", h["first_year"], "int")
    r.put("ch1.peak_year", h["peak_year"], "int")
    r.put("ch1.latest.payment_share", h["latest_share"], "pct1", model="monte_carlo")
    r.put("ch1.peak.payment_share", h["peak_share"], "pct1", model="monte_carlo")
    r.put("ch1.first.payment_share", h["first_share"], "pct1", model="monte_carlo")
    r.put("ch1.latest.price_to_income", h["latest_pti"], "ratio1", model="anchor")
    r.put("ch1.first.price_to_income", h["first_pti"], "ratio1", model="anchor")
    r.put("ch1.peak.price_to_income", h["peak_pti"], "ratio1", model="anchor")
    r.put("ch1.pti_change", h["latest_pti"] / h["first_pti"] - 1.0, "spct1", model="anchor")
    r.put("ch1.diff", h["diff"], "pts1", model="monte_carlo")
    r.put("ch1.diff.low", h["diff_low"], "pts1", model="monte_carlo")
    r.put("ch1.diff.high", h["diff_high"], "pts1", model="monte_carlo")
    r.put("ch1.failing_year", h["failing_year"] if h["failing_year"] is not None else "none", "text")
    r.put("ch1.metros_compared", h["metros_compared"], "int")
    r.put("ch1.metros_above_peak", h["metros_above_peak"], "int")
    r.put("ch1.metros_above_peak_share", h["metros_above_peak"] / max(h["metros_compared"], 1), "pct0")
    r.put("ch1.draws", int(series["draws"][0]), "int")
    latest_row = series.filter(pl.col("year") == h["latest_year"]).row(0, named=True)
    r.put("ch1.latest.payment_share.low", float(latest_row["payment_share_low"]), "pct1", model="monte_carlo")
    r.put(
        "ch1.latest.payment_share.high", float(latest_row["payment_share_high"]), "pct1", model="monte_carlo"
    )
    r.put("ch1.latest.rate", float(latest_row["rate"]), "rate2")
    r.put("ch1.latest.median_home", float(latest_row["median_home"]), "usd0", model="anchor")
    r.put("ch1.branch", branch.name, "text")
    r.put("ch1.message", branch.text, "text")

    # The series table
    r.put_table(
        "ch1.series",
        ["Year", "Metros", "Rate", "Median home", "Price to income", "Payment share", "Low", "High"],
        ["int", "int", "rate2", "usd0", "ratio2", "pct1", "pct1", "pct1"],
        [
            [
                int(x["year"]),
                int(x["metros"]),
                float(x["rate"]),
                float(x["median_home"]),
                float(x["price_to_income"]),
                float(x["payment_share"]),
                float(x["payment_share_low"]),
                float(x["payment_share_high"]),
            ]
            for x in series.iter_rows(named=True)
        ],
        model="monte_carlo",
    )

    # The line interior test: metros above each affordable line in the latest year
    latest_metros = panel.metropolitan().filter(
        (pl.col("year") == h["latest_year"]) & pl.col("payment_share").is_not_null()
    )
    line_rows: list[list[Any]] = []
    for line in AFFORDABLE_LINES:
        count = int((latest_metros["payment_share"] > line).sum())
        line_rows.append([line, count, count / max(latest_metros.height, 1)])
    r.put_table("ch1.line_interior", ["Line", "Metros above", "Share"], ["pct0", "int", "pct0"], line_rows)
    chosen = [row for row in line_rows if row[0] == policy.affordable_line][0]
    r.put("ch1.metros_above_line", int(chosen[1]), "int")
    r.put("ch1.metros_above_line_share", float(chosen[2]), "pct0")

    # The anchor sensitivity table: the headline under every neighbour, degenerate when the sign turns
    anchor_rows: list[list[Any]] = []
    signs: dict[int, float] = {}
    for anchor in ANCHOR_YEARS:
        try:
            other = panel.with_anchor(anchor)
            hh = headline(other, policy, draws=min(draws or policy.monte_carlo_draws, 2000))
        except Exception:
            anchor_rows.append([anchor, None, None, None, None, "no census value in this year"])
            continue
        signs[anchor] = hh["diff"]
        anchor_rows.append(
            [anchor, hh["latest_share"], hh["peak_share"], hh["diff"], hh["metros_above_peak"], ""]
        )
    chosen_sign = np.sign(signs.get(policy.anchor_year, h["diff"]))
    neighbours = [a for a in ANCHOR_YEARS if a != policy.anchor_year and a in signs]
    nearest = min(neighbours, key=lambda a: abs(a - policy.anchor_year)) if neighbours else None
    degenerate = nearest is not None and np.sign(signs[nearest]) != chosen_sign
    for row in anchor_rows:
        if row[0] == policy.anchor_year:
            row[5] = "chosen"
        elif degenerate and row[0] == nearest:
            row[5] = "degenerate"
    r.put_table(
        "ch1.anchor_sensitivity",
        [
            "Anchor year",
            "Latest payment share",
            "2006 payment share",
            "Difference",
            "Metros above 2006",
            "Note",
        ],
        ["int", "pct1", "pct1", "pts1", "int", "text"],
        anchor_rows,
        model="anchor",
    )
    r.put("ch1.anchor_degenerate", "degenerate" if degenerate else "stable", "text")

    # The self report check
    check = self_report_check(panel)
    if check.height:
        ratio = check["reported_over_transaction"].to_numpy()
        r.put("ch1.self_report.metros", int(check.height), "int")
        r.put("ch1.self_report.median_ratio", float(np.median(ratio)), "ratio2")
        r.put("ch1.self_report.p10", float(np.quantile(ratio, 0.10)), "ratio2")
        r.put("ch1.self_report.p90", float(np.quantile(ratio, 0.90)), "ratio2")
        r.marts["ch1_self_report"] = check
    else:
        r.put("ch1.self_report.metros", 0, "int")
        r.put("ch1.self_report.median_ratio", None, "ratio2")
        r.put("ch1.self_report.p10", None, "ratio2")
        r.put("ch1.self_report.p90", None, "ratio2")

    metro_series = (
        panel.metropolitan()
        .filter(pl.col("payment_share").is_not_null())
        .select(
            "cbsa_code",
            "cbsa_title",
            "year",
            "value_anchored",
            "median_income",
            (pl.col("value_anchored") / pl.col("median_income")).alias("price_to_income"),
            "payment_share",
            "rate",
        )
    )
    r.figure = Figure(
        title=branch.text,
        subtitle=f"Price to income and the payment share of income on the median home, owner weighted across metros, {h['first_year']} to {h['latest_year']}",
        sql=SQL,
        frames={"national": series, "metros": metro_series.sort(["cbsa_code", "year"])},
        model="monte_carlo",
        callout=f"{h['metros_above_peak']} of {h['metros_compared']} metros sit above their 2006 payment share in {h['latest_year']}",
    )
    r.method = {
        "estimator": "the anchored index with the payment at the quarterly rate",
        "split": "no fitted parameter; the baseline years are 2005 to 2019 and the headline is the latest release",
        "interval": f"{series['draws'][0]} Monte Carlo draws over the census margins of error, index held fixed",
        "family": "one comparison, no correction",
    }
    r.pushback = (
        "Self reported values run high or low by metro, and the anchor carries that bias into every year. The anchor "
        "sensitivity table shows what moving the anchor year does to the headline, and the self report check prints "
        "the census value over the transaction values in the loan extract for the same year; neither removes the bias, "
        "they bound it. The payment is principal and interest only, so a reader who adds taxes and insurance will find "
        "every share here understated by the same amount in every year."
    )
    r.marts["ch1_national_series"] = series
    return r


# Recovery on the simulator


def simulate_estimate(world: World, policy: Policy = POLICY, *, draws: int = 1000) -> list[Grade]:
    panel = from_world(world, policy)
    series = national_series(panel, policy, draws=draws, seed=world.seed)
    truth_rows = (
        world.metro_year.filter(pl.col("kind") == "metropolitan")
        .group_by("year")
        .agg(
            (
                (pl.col("payment_share_true") * pl.col("owner_households")).sum()
                / pl.col("owner_households").sum()
            ).alias("truth")
        )
        .sort("year")
    )
    truth_by_year = {int(r["year"]): float(r["truth"]) for r in truth_rows.iter_rows(named=True)}
    latest = series.filter(pl.col("year") == int(series["year"].max())).row(0, named=True)
    grades = [
        Grade(
            "anchored_payment_share",
            float(latest["payment_share"]),
            truth_by_year[int(latest["year"])],
            float(latest["payment_share_low"]),
            float(latest["payment_share_high"]),
            detail="national payment share in the latest year, Monte Carlo interval",
        )
    ]
    check = self_report_check(panel)
    bias = world.truth.metros.select("metro_id", "value_bias")
    merged = check.join(bias, left_on="cbsa_code", right_on="metro_id", how="inner")
    if merged.height:
        err = (merged["reported_over_transaction"] - merged["value_bias"]).abs().mean()
        grades.append(
            Grade(
                "self_report_correction",
                float(merged["reported_over_transaction"].mean()),
                float(merged["value_bias"].mean()),
                detail=f"mean absolute error of the planted factor over {merged.height} metros: {float(err):.4f}",
                flag=float(err),
            )
        )
    # The anchored level itself against the true level, as a relative error
    my = panel.metropolitan().filter(pl.col("year") == int(latest["year"]))
    truth_level = world.metro_year.filter(pl.col("year") == int(latest["year"])).select(
        "metro_id", "median_value_true", "owner_households"
    )
    lvl = my.join(truth_level, left_on="cbsa_code", right_on="metro_id", how="inner")
    w = lvl["owner_households"].to_numpy()
    est_level = float(lvl["value_anchored"].to_numpy() @ w / w.sum())
    true_level = float(lvl["median_value_true"].to_numpy() @ w / w.sum())
    grades.append(
        Grade(
            "anchored_level",
            est_level / true_level,
            1.0,
            detail="anchored over true national value, latest year",
        )
    )
    return grades


def weighted(panel: Panel, column: str) -> float | None:
    return weighted_mean(
        panel.metropolitan().filter(pl.col("year") == panel.latest_acs_year), column, "owner_households"
    )
