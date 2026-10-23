"""Chapter 2, the rate shock and the lock in.

The event study takes the payment on the same home, quarter by quarter from 2019, and splits its change
from the base quarter into the part the price moved and the part the rate moved, exactly: the price part
is the payment at the current price and the base rate less the base payment, the rate part is the rest.
The quarter in which the rate part overtook the price part is named.

The lock in is measured from the loans themselves: originations of 2019 to 2021 written under four
percent, per hundred owner households, by metro. Turnover (purchase originations per hundred owner
households) in 2023 onward against 2018 and 2019 is regressed on that intensity with metro and year fixed
effects on owner weighted cells and state clustered standard errors; the pre period placebo regresses the
2018 to 2019 change on the same intensity, where nothing should move. The simulator plants a known lock
in response and the recovery study grades the estimator against it.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl
from doorstep_core.config import LOCK_IN_THRESHOLDS, POLICY, Policy
from doorstep_core.formats import format_value
from doorstep_finance.mortgage import payment_on_price
from doorstep_sim.metros import World
from doorstep_stats.regression import Coefficient, first, regress

from doorstep_chapters.common import Branch, ChapterResult, Figure, Grade, ensure
from doorstep_chapters.panel import Panel, from_world

NUMBER = 2
SLUG = "rate_shock"
TITLE = "The rate shock and the lock in"
EVENT_FIRST_YEAR = 2019

SQL_DECOMPOSITION = """
with base as (
    select cbsa_code, payment as base_payment, value_anchored as base_value, rate as base_rate
    from mart_metro_quarter where period = '2019Q1'
)
select q.period,
       sum(q.payment * w.owner_households) / sum(w.owner_households) as payment,
       sum(b.base_payment * w.owner_households) / sum(w.owner_households) as base_payment
from mart_metro_quarter q
join base b using (cbsa_code)
join (select cbsa_code, owner_households from mart_metro_year where year = 2019) w using (cbsa_code)
where q.year >= 2019 and q.kind = 'metropolitan'
group by q.period
order by q.period
""".strip()

SQL_LOCK_IN = """
with intensity as (
    select cbsa_code,
           100.0 * sum(low_rate_originations) / max(case when year = 2021 then owner_households end) as lock_in_per_100
    from mart_metro_year where year between 2019 and 2021 group by cbsa_code
)
select m.cbsa_code, m.cbsa_title, m.year, m.turnover_per_100_owners, i.lock_in_per_100, m.owner_households, m.states
from mart_metro_year m join intensity i using (cbsa_code)
where m.kind = 'metropolitan' and (m.year in (2018, 2019) or m.year >= 2023) and m.purchase_loans is not null
order by m.cbsa_code, m.year
""".strip()


def plan(policy: Policy = POLICY) -> dict[str, Any]:
    return {
        "chapter": NUMBER,
        "slug": SLUG,
        "claim": "The rate shock of 2022 moved the payment more than the price did, and it froze turnover where owners "
        "held the cheapest mortgages.",
        "estimator": {
            "decomposition": "payment at the current price and the base rate (2019Q1) less the base payment is the price part; "
            "the remainder is the rate part; owner weighted across metros",
            "lock_in": "originations of 2019 to 2021 with a rate under the threshold per 100 owner households of 2021; turnover "
            "regressed on lock in times post with metro and year fixed effects on owner weighted cells",
            "placebo": "the same regression on 2018 and 2019 with 2019 as the post year",
        },
        "interval": "cluster robust (CR1) by state, normal critical value",
        "split": {
            "event_window": [EVENT_FIRST_YEAR, "latest"],
            "base_years": list(policy.turnover_base_years),
            "test_from": policy.turnover_test_first_year,
        },
        "family": "two coefficients (headline and placebo), reported separately; no correction",
        "operating_points": {
            "lock_in_threshold": policy.lock_in_threshold,
            "threshold_neighbours": list(LOCK_IN_THRESHOLDS),
            "lock_in_years": list(policy.lock_in_years),
        },
        "message_rule": "froze: headline interval below zero and placebo interval includes zero; pre_trend: both exclude zero; "
        "null: headline interval includes zero",
    }


def message_rule(main: Coefficient, placebo: Coefficient, overtaking: str | None) -> Branch:
    when = (
        f"The rate part of the payment overtook the price part in {overtaking}. "
        if overtaking
        else "The rate part never overtook the price part. "
    )
    size = f"{format_value(abs(main.estimate), 'float2')} purchases per 100 owner households per point of lock in"
    if main.high < 0.0 and placebo.covers(0.0):
        return Branch(
            "froze",
            when + f"The rate shock froze turnover where owners had the most to lose: {size} "
            f"(interval {format_value(main.low, 'sfloat2')} to {format_value(main.high, 'sfloat2')}), and the placebo on the years before the "
            f"shock sits at {format_value(placebo.estimate, 'sfloat2')} with an interval that includes zero.",
        )
    if main.high < 0.0 and not placebo.covers(0.0):
        return Branch(
            "pre_trend",
            when + f"Turnover fell by {size}, but the placebo on 2018 to 2019 also moved "
            f"({format_value(placebo.estimate, 'sfloat2')}, interval excluding zero): the metros with the most lock in were already "
            f"turning over differently, and the headline is an upper bound.",
        )
    if main.low > 0.0:
        return Branch(
            "reverse",
            when
            + f"Turnover rose where lock in was higher, by {size}; the lock in story does not hold in these years.",
        )
    return Branch(
        "null",
        when
        + f"The lock in coefficient ({format_value(main.estimate, 'sfloat2')}, interval {format_value(main.low, 'sfloat2')} to "
        f"{format_value(main.high, 'sfloat2')}) cannot be told from zero.",
    )


def decomposition(panel: Panel, policy: Policy = POLICY) -> pl.DataFrame:
    """The national payment by quarter from 2019Q1 split into its price and rate parts."""
    q = panel.metro_quarter.filter(pl.col("year") >= EVENT_FIRST_YEAR).join(
        panel.metropolitan()
        .filter(pl.col("year") == EVENT_FIRST_YEAR)
        .select("cbsa_code", "owner_households"),
        on="cbsa_code",
        how="inner",
    )
    q = q.filter(
        pl.col("value_anchored").is_not_null()
        & pl.col("rate").is_not_null()
        & (pl.col("owner_households") > 0)
    )
    ensure(q.height > 0, "chapter 2 has no quarterly rows from 2019")
    base = q.filter((pl.col("year") == EVENT_FIRST_YEAR) & (pl.col("quarter") == 1)).select(
        "cbsa_code", pl.col("value_anchored").alias("base_value"), pl.col("rate").alias("base_rate")
    )
    q = q.join(base, on="cbsa_code", how="inner")
    rows: list[dict[str, Any]] = []
    for period, sub in sorted(q.group_by("period"), key=lambda kv: str(kv[0][0])):
        w = sub["owner_households"].to_numpy().astype(np.float64)
        w = w / w.sum()
        pay_now = np.array(
            [
                payment_on_price(v, r, policy.down_payment_share, policy.loan_term_years)
                for v, r in zip(sub["value_anchored"], sub["rate"], strict=True)
            ]
        )
        pay_base = np.array(
            [
                payment_on_price(v, r, policy.down_payment_share, policy.loan_term_years)
                for v, r in zip(sub["base_value"], sub["base_rate"], strict=True)
            ]
        )
        pay_price_only = np.array(
            [
                payment_on_price(v, r, policy.down_payment_share, policy.loan_term_years)
                for v, r in zip(sub["value_anchored"], sub["base_rate"], strict=True)
            ]
        )
        rows.append(
            {
                "period": str(period[0]),
                "year": int(sub["year"][0]),
                "quarter": int(sub["quarter"][0]),
                "rate": float(sub["rate"][0]),
                "metros": int(sub.height),
                "payment": float(pay_now @ w),
                "base_payment": float(pay_base @ w),
                "price_part": float((pay_price_only - pay_base) @ w),
                "rate_part": float((pay_now - pay_price_only) @ w),
            }
        )
    return pl.DataFrame(rows).sort(["year", "quarter"])


def overtaking_quarter(decomp: pl.DataFrame) -> str | None:
    after = decomp.filter(pl.col("rate_part") > pl.col("price_part")).filter(pl.col("rate_part") > 0)
    return str(after["period"][0]) if after.height else None


def lock_in_intensity(
    panel: Panel, policy: Policy = POLICY, *, column: str = "low_rate_originations"
) -> pl.DataFrame:
    """Originations under the threshold in the lock in years per 100 owner households of the last lock in year."""
    lo, hi = policy.lock_in_years
    my = panel.metropolitan()
    sums = (
        my.filter((pl.col("year") >= lo) & (pl.col("year") <= hi) & pl.col(column).is_not_null())
        .group_by("cbsa_code")
        .agg(pl.col(column).sum().alias("low_rate"))
    )
    owners = my.filter(pl.col("year") == hi).select("cbsa_code", "owner_households")
    out = sums.join(owners, on="cbsa_code", how="inner").filter(pl.col("owner_households") > 0)
    return (
        out.with_columns((100.0 * pl.col("low_rate") / pl.col("owner_households")).alias("lock_in_per_100"))
        .select("cbsa_code", "lock_in_per_100", "low_rate")
        .sort("cbsa_code")
    )


def _turnover_frame(panel: Panel, policy: Policy, intensity: pl.DataFrame) -> pl.DataFrame:
    my = panel.metropolitan().filter(
        pl.col("purchase_loans").is_not_null() & (pl.col("owner_households") > 0)
    )
    my = my.with_columns((100.0 * pl.col("purchase_loans") / pl.col("owner_households")).alias("turnover"))
    return my.join(intensity, on="cbsa_code", how="inner").filter(pl.col("state").is_not_null())


def lock_in_regression(
    panel: Panel, policy: Policy = POLICY, *, column: str = "low_rate_originations"
) -> tuple[Coefficient, Coefficient, int, int]:
    """(headline, placebo, metros, state clusters)."""
    intensity = lock_in_intensity(panel, policy, column=column)
    frame = _turnover_frame(panel, policy, intensity)
    base_lo, base_hi = policy.turnover_base_years
    main = frame.filter(
        (pl.col("year").is_between(base_lo, base_hi)) | (pl.col("year") >= policy.turnover_test_first_year)
    )
    ensure(main["year"].n_unique() >= 3, "chapter 2 needs base years and test years with loans")
    post = (main["year"] >= policy.turnover_test_first_year).cast(pl.Float64).to_numpy()
    x = (main["lock_in_per_100"].to_numpy() * post)[:, None]
    coefs = regress(
        main["turnover"].to_numpy(),
        x,
        ["lock_in_x_post"],
        weights=main["owner_households"].to_numpy(),
        fixed_effects=[main["cbsa_code"].to_numpy(), main["year"].to_numpy()],
        cluster=main["state"].to_numpy(),
    )
    headline = first(coefs, "lock_in_x_post")
    placebo_frame = frame.filter(pl.col("year").is_between(base_lo, base_hi))
    ensure(placebo_frame["year"].n_unique() == 2, "the placebo needs the two base years")
    late = (placebo_frame["year"] == base_hi).cast(pl.Float64).to_numpy()
    xp = (placebo_frame["lock_in_per_100"].to_numpy() * late)[:, None]
    pcoefs = regress(
        placebo_frame["turnover"].to_numpy(),
        xp,
        ["lock_in_x_late"],
        weights=placebo_frame["owner_households"].to_numpy(),
        fixed_effects=[placebo_frame["cbsa_code"].to_numpy(), placebo_frame["year"].to_numpy()],
        cluster=placebo_frame["state"].to_numpy(),
    )
    placebo = first(pcoefs, "lock_in_x_late")
    return headline, placebo, int(main["cbsa_code"].n_unique()), headline.clusters


def estimate(panel: Panel, policy: Policy = POLICY) -> ChapterResult:
    decomp = decomposition(panel, policy)
    overtaking = overtaking_quarter(decomp)
    headline, placebo, metros, clusters = lock_in_regression(panel, policy)
    branch = message_rule(headline, placebo, overtaking)
    latest = decomp.row(decomp.height - 1, named=True)
    r = ChapterResult(
        number=NUMBER,
        slug=SLUG,
        source=panel.source,
        population=f"every metropolitan area with quarterly prices from {EVENT_FIRST_YEAR}Q1 and loans in the base and test years ({metros} metros, {clusters} states)",
        branch=branch.name,
        message=branch.text,
        reported_years=sorted(
            int(y)
            for y in panel.metropolitan()["year"].unique().to_list()
            if int(y) >= policy.turnover_test_first_year
        ),
    )
    r.put("ch2.overtaking_quarter", overtaking or "never", "quarter", model="decomposition")
    r.put("ch2.latest_period", str(latest["period"]), "quarter")
    r.put("ch2.base_payment", float(latest["base_payment"]), "usd0", model="decomposition")
    r.put("ch2.latest_payment", float(latest["payment"]), "usd0", model="decomposition")
    r.put("ch2.latest_price_part", float(latest["price_part"]), "susd0", model="decomposition")
    r.put("ch2.latest_rate_part", float(latest["rate_part"]), "susd0", model="decomposition")
    total_change = float(latest["payment"] - latest["base_payment"])
    r.put("ch2.latest_change", total_change, "susd0", model="decomposition")
    r.put(
        "ch2.rate_part_share",
        float(latest["rate_part"]) / total_change if total_change else None,
        "pct0",
        model="decomposition",
    )
    peak = decomp.sort("rate_part", descending=True).row(0, named=True)
    r.put("ch2.peak_rate_part_period", str(peak["period"]), "quarter", model="decomposition")
    r.put("ch2.peak_rate_part", float(peak["rate_part"]), "susd0", model="decomposition")
    r.put("ch2.lock_in.coef", headline.estimate, "sfloat3", model="lock_in")
    r.put("ch2.lock_in.low", headline.low, "sfloat3", model="lock_in")
    r.put("ch2.lock_in.high", headline.high, "sfloat3", model="lock_in")
    r.put("ch2.lock_in.se", headline.se, "float3", model="lock_in")
    r.put("ch2.lock_in.p", headline.p_value, "float3", model="lock_in")
    r.put("ch2.placebo.coef", placebo.estimate, "sfloat3", model="lock_in")
    r.put("ch2.placebo.low", placebo.low, "sfloat3", model="lock_in")
    r.put("ch2.placebo.high", placebo.high, "sfloat3", model="lock_in")
    r.put("ch2.placebo.p", placebo.p_value, "float3", model="lock_in")
    r.put("ch2.metros", metros, "int")
    r.put("ch2.clusters", clusters, "int")
    r.put("ch2.cells", headline.cells, "int")
    r.put("ch2.branch", branch.name, "text")
    r.put("ch2.message", branch.text, "text")

    intensity = lock_in_intensity(panel, policy)
    r.put("ch2.lock_in.mean", float(intensity["lock_in_per_100"].mean()), "float1", model="lock_in")
    r.put("ch2.lock_in.p10", float(intensity["lock_in_per_100"].quantile(0.1)), "float1", model="lock_in")
    r.put("ch2.lock_in.p90", float(intensity["lock_in_per_100"].quantile(0.9)), "float1", model="lock_in")
    r.put("ch2.low_rate_originations", float(intensity["low_rate"].sum()), "millions1", model="lock_in")
    spread = float(intensity["lock_in_per_100"].quantile(0.9) - intensity["lock_in_per_100"].quantile(0.1))
    r.put("ch2.lock_in.effect_p90_vs_p10", headline.estimate * spread, "sfloat2", model="lock_in")

    # Turnover before and after
    base_lo, base_hi = policy.turnover_base_years
    frame = _turnover_frame(panel, policy, intensity)
    before = frame.filter(pl.col("year").is_between(base_lo, base_hi))
    after = frame.filter(pl.col("year") >= policy.turnover_test_first_year)
    wb = before["owner_households"].to_numpy()
    wa = after["owner_households"].to_numpy()
    r.put("ch2.turnover.before", float(before["turnover"].to_numpy() @ wb / wb.sum()), "float2")
    r.put("ch2.turnover.after", float(after["turnover"].to_numpy() @ wa / wa.sum()), "float2")

    # Interior test on the threshold
    rows: list[list[Any]] = []
    signs: dict[float, float] = {}
    for threshold, column in zip(
        LOCK_IN_THRESHOLDS,
        ("under_3_originations", "under_3_5_originations", "low_rate_originations"),
        strict=True,
    ):
        try:
            h, p, _, _ = lock_in_regression(panel, policy, column=column)
        except Exception:
            rows.append([threshold, None, None, None, None, "no originations under this threshold"])
            continue
        signs[threshold] = h.estimate
        rows.append(
            [
                threshold,
                h.estimate,
                h.low,
                h.high,
                p.estimate,
                "chosen" if threshold == policy.lock_in_threshold else "",
            ]
        )
    neighbours = [t for t in signs if t != policy.lock_in_threshold]
    nearest = min(neighbours, key=lambda t: abs(t - policy.lock_in_threshold)) if neighbours else None
    degenerate = nearest is not None and np.sign(signs[nearest]) != np.sign(
        signs.get(policy.lock_in_threshold, headline.estimate)
    )
    if degenerate:
        for row in rows:
            if row[0] == nearest:
                row[5] = "degenerate"
    r.put_table(
        "ch2.threshold_interior",
        ["Threshold", "Coefficient", "Low", "High", "Placebo", "Note"],
        ["rate2", "sfloat3", "sfloat3", "sfloat3", "sfloat3", "text"],
        rows,
        model="lock_in",
    )
    r.put("ch2.threshold_degenerate", "degenerate" if degenerate else "stable", "text")

    r.put_table(
        "ch2.decomposition",
        ["Quarter", "Rate", "Payment", "Price part", "Rate part"],
        ["quarter", "rate2", "usd0", "susd0", "susd0"],
        [
            [x["period"], x["rate"], x["payment"], x["price_part"], x["rate_part"]]
            for x in decomp.iter_rows(named=True)
        ],
        model="decomposition",
    )
    metro_rows = (
        frame.group_by("cbsa_code", "cbsa_title", "lock_in_per_100")
        .agg(
            pl.col("turnover").filter(pl.col("year").is_between(base_lo, base_hi)).mean().alias("before"),
            pl.col("turnover")
            .filter(pl.col("year") >= policy.turnover_test_first_year)
            .mean()
            .alias("after"),
        )
        .drop_nulls()
        .with_columns((pl.col("after") - pl.col("before")).alias("change"))
        .sort("cbsa_code")
    )
    r.marts["ch2_lock_in_metros"] = metro_rows
    r.marts["ch2_decomposition"] = decomp
    r.figure = Figure(
        title=branch.text,
        subtitle=f"The monthly payment on the median home from {EVENT_FIRST_YEAR}Q1: the part from the price and the part from the rate",
        sql=SQL_DECOMPOSITION,
        frames={"decomposition": decomp, "lock_in": metro_rows},
        model="decomposition",
        callout=f"rate part {format_value(float(latest['rate_part']), 'susd0')} against price part {format_value(float(latest['price_part']), 'susd0')} in {latest['period']}",
    )
    r.extra_figures["lock_in"] = Figure(
        title=f"Turnover fell by {format_value(abs(headline.estimate), 'float2')} purchases per 100 owners per point of lock in; placebo {format_value(placebo.estimate, 'sfloat2')}",
        subtitle="Change in purchase originations per 100 owner households, 2023 onward against 2018 and 2019, by originations under four percent per 100 owners",
        sql=SQL_LOCK_IN,
        frames={"lock_in": metro_rows},
        model="lock_in",
    )
    r.method = {
        "estimator": "exact price and rate decomposition of the payment; turnover on lock in intensity with metro and year fixed effects on owner weighted cells",
        "split": f"event window {EVENT_FIRST_YEAR} to the latest quarter; base years {base_lo} and {base_hi}; test years from {policy.turnover_test_first_year}",
        "interval": f"cluster robust by state, {clusters} clusters",
        "family": "headline and placebo reported separately",
    }
    r.pushback = (
        "Lock in is measured from originations, so a metro where owners refinanced twice at the bottom counts each "
        "refinance; the measure is an intensity, not a count of owners, and the notebook keeps the version that counted "
        "refinances twice as a dead end. Turnover also fell because inventory fell, and a metro with little inventory "
        "sees fewer purchases whatever its owners hold; the placebo bounds the trend, it does not remove the mechanism."
    )
    return r


# Recovery on the simulator


def simulate_estimate(world: World, policy: Policy = POLICY) -> list[Grade]:
    panel = from_world(world, policy)
    headline, placebo, _, _ = lock_in_regression(panel, policy)
    truth = -world.truth.lock_in_response
    return [
        Grade(
            "lock_in_did",
            headline.estimate,
            truth,
            headline.low,
            headline.high,
            flag=float(placebo.covers(0.0)),
            detail="placebo covers zero",
        ),
        Grade("lock_in_placebo", placebo.estimate, 0.0, placebo.low, placebo.high),
    ]
