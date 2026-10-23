"""Chapter 7, the migration shock: the metros that gained the most people saw prices rise the most, and
the pre trend test says whether that is cause.

Price growth from the end of 2019 to the end of 2021 is regressed across metros on the pandemic migration
shock, domestic migration per hundred residents over 2020 and 2021 less the same measure over 2017 and
2018, with the pre pandemic migration as a control, population weighted, state clustered. Migration is
persistent, so the level alone would credit the pandemic with what a metro had been gaining every year;
the shock is the part the pandemic added. The placebo regresses growth from the end of 2016 to the end of
2018 on the same shock: if the metros that gained people in the pandemic were already rising before it,
the placebo moves and the headline is an upper bound.
Synthetic control for the three metros with the largest migration gains per capita, with every other
metro searched as a donor and treated in turn as a placebo, shows the gap and its post 2022 reversal.

The simulator plants a known price response to migration and a reverse causality knob under which
migration itself responds to lagged affordability; the recovery study reports the bias and coverage by
condition and the power of the placebo to flag the biased condition, which is where this chapter has to
admit its limit in print.

The population estimates count a year from July to June, so the migration years and the price window are
offset by two quarters; the decision is in DECISIONS.md.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl
from doorstep_core.config import POLICY, Policy
from doorstep_core.formats import format_value
from doorstep_sim.metros import World
from doorstep_stats.regression import Coefficient, first, regress
from doorstep_stats.synthetic import SyntheticControl, placebo_band, synthetic_control

from doorstep_chapters.common import Branch, ChapterResult, Figure, Grade, ensure
from doorstep_chapters.panel import Panel, from_world

NUMBER = 7
SLUG = "migration"
TITLE = "The migration shock"

SQL = """
with migration as (
    select cbsa_code,
           100.0 * sum(case when year in (2020, 2021) then domestic_migration end) / avg(case when year in (2020, 2021) then population end)
           - 100.0 * sum(case when year in (2017, 2018) then domestic_migration end) / avg(case when year in (2017, 2018) then population end) as migration_shock,
           100.0 * sum(case when year in (2017, 2018) then domestic_migration end) / avg(case when year in (2017, 2018) then population end) as migration_pre
    from mart_metro_year where year in (2017, 2018, 2020, 2021) group by cbsa_code
),
growth as (
    select a.cbsa_code,
           ln(b.index_nsa) - ln(a.index_nsa) as growth,
           ln(d.index_nsa) - ln(c.index_nsa) as placebo_growth
    from mart_metro_quarter a
    join mart_metro_quarter b on b.cbsa_code = a.cbsa_code and b.period = '2021Q4'
    join mart_metro_quarter c on c.cbsa_code = a.cbsa_code and c.period = '2016Q4'
    join mart_metro_quarter d on d.cbsa_code = a.cbsa_code and d.period = '2018Q4'
    where a.period = '2019Q4'
)
select m.cbsa_code, d.cbsa_title, d.states, m.migration_shock, m.migration_pre, g.growth, g.placebo_growth, p.population
from migration m
join growth g using (cbsa_code)
join (select cbsa_code, cbsa_title, states, population from mart_metro_year where year = 2021 and kind = 'metropolitan') d using (cbsa_code)
join (select cbsa_code, population from mart_metro_year where year = 2021) p using (cbsa_code)
order by m.migration_shock desc
""".strip()


def plan(policy: Policy = POLICY) -> dict[str, Any]:
    return {
        "chapter": NUMBER,
        "slug": SLUG,
        "claim": "Metros that gained more people per hundred residents in the pandemic, beyond what they had been gaining, "
        "saw prices rise more, and the pre trend placebo decides whether the gain caused the rise.",
        "estimator": "log price growth over the window regressed across metros on the migration shock (domestic migration per "
        "hundred residents over the migration years less the pre pandemic years) with the pre pandemic migration as a "
        "control, population weighted, state clustered; the same regression on the placebo window; synthetic control on the "
        "quarterly log index for the largest gainers against donors with small shocks, every donor treated in turn as a placebo",
        "interval": "cluster robust (CR1) by state; permutation p value over donors for the synthetic controls",
        "split": {
            "window": list(policy.migration_window),
            "placebo_window": list(policy.migration_placebo_window),
            "migration_years": list(policy.migration_years),
            "pre_years": list(policy.migration_pre_years),
        },
        "family": "headline and placebo reported separately; three synthetic controls each with its own permutation p value; no correction",
        "operating_points": {
            "synthetic_control_metros": policy.synthetic_control_metros,
            "synthetic_control_first_period": policy.synthetic_control_first_period,
        },
        "message_rule": "prices_followed: placebo interval includes zero and the headline excludes it; already_rising: the placebo "
        "excludes zero; null: the headline includes zero",
    }


def message_rule(main: Coefficient, placebo: Coefficient) -> Branch:
    size = f"{format_value(main.estimate, 'spct1')} price growth over the window per person gained per hundred residents beyond the pre pandemic pace"
    if not placebo.covers(0.0):
        return Branch(
            "already_rising",
            f"The metros that gained people were already rising: the placebo on the years before the pandemic is "
            f"{format_value(placebo.estimate, 'spct1')} (interval {format_value(placebo.low, 'spct1')} to {format_value(placebo.high, 'spct1')}), so the "
            f"headline of {size} is an upper bound on what the migration itself did.",
        )
    if main.excludes_zero:
        return Branch(
            "prices_followed",
            f"Demand moved and prices followed: {size} (interval {format_value(main.low, 'spct1')} to {format_value(main.high, 'spct1')}), "
            f"with a placebo of {format_value(placebo.estimate, 'spct1')} on the years before the pandemic whose interval includes zero.",
        )
    return Branch(
        "null",
        f"Migration and price growth cannot be tied across metros here: {size}, interval {format_value(main.low, 'spct1')} to "
        f"{format_value(main.high, 'spct1')}; the placebo is {format_value(placebo.estimate, 'spct1')}.",
    )


def _index_at(panel: Panel, period: str) -> pl.DataFrame:
    return panel.metro_quarter.filter((pl.col("period") == period) & pl.col("index_at").is_not_null()).select(
        "cbsa_code", pl.col("index_at").alias(f"index_{period}")
    )


def _migration_per_100(my: pl.DataFrame, years: tuple[int, int], name: str) -> pl.DataFrame:
    y0, y1 = years
    return (
        my.filter(
            (pl.col("year") >= y0)
            & (pl.col("year") <= y1)
            & pl.col("domestic_migration").is_not_null()
            & pl.col("population").is_not_null()
        )
        .group_by("cbsa_code")
        .agg(
            pl.col("domestic_migration").sum().alias("migration"),
            pl.col("population").mean().alias("population"),
            pl.len().alias("years"),
        )
        .filter(pl.col("years") == (y1 - y0 + 1))
        .with_columns((100.0 * pl.col("migration") / pl.col("population")).alias(name))
        .select("cbsa_code", name, "population")
    )


def cross_section(panel: Panel, policy: Policy = POLICY) -> pl.DataFrame:
    my = panel.metropolitan()
    pandemic = _migration_per_100(my, policy.migration_years, "migration_pandemic")
    pre = _migration_per_100(my, policy.migration_pre_years, "migration_pre").drop("population")
    a, b = policy.migration_window
    c, d = policy.migration_placebo_window
    frame = (
        pandemic.join(pre, on="cbsa_code", how="inner")
        .with_columns((pl.col("migration_pandemic") - pl.col("migration_pre")).alias("migration_shock"))
        .join(_index_at(panel, a), on="cbsa_code", how="inner")
        .join(_index_at(panel, b), on="cbsa_code", how="inner")
        .join(_index_at(panel, c), on="cbsa_code", how="inner")
        .join(_index_at(panel, d), on="cbsa_code", how="inner")
        .join(
            my.filter(pl.col("year") == policy.migration_years[1]).select("cbsa_code", "cbsa_title", "state"),
            on="cbsa_code",
            how="inner",
        )
        .with_columns(
            (pl.col(f"index_{b}").log() - pl.col(f"index_{a}").log()).alias("growth"),
            (pl.col(f"index_{d}").log() - pl.col(f"index_{c}").log()).alias("placebo_growth"),
        )
        .filter(pl.col("state").is_not_null())
        .select(
            "cbsa_code",
            "cbsa_title",
            "state",
            "population",
            "migration_pandemic",
            "migration_pre",
            "migration_shock",
            "growth",
            "placebo_growth",
        )
        .sort("cbsa_code")
    )
    ensure(frame.height >= 10, "chapter 7 needs at least ten metros with migration and both index windows")
    return frame


def fit(frame: pl.DataFrame) -> tuple[Coefficient, Coefficient]:
    x = np.column_stack([frame["migration_shock"].to_numpy(), frame["migration_pre"].to_numpy()])
    names = ["migration_shock", "migration_pre"]
    w = frame["population"].to_numpy()
    cl = frame["state"].to_numpy()
    main = first(regress(frame["growth"].to_numpy(), x, names, weights=w, cluster=cl), "migration_shock")
    placebo = first(
        regress(frame["placebo_growth"].to_numpy(), x, names, weights=w, cluster=cl), "migration_shock"
    )
    return main, placebo


def synthetic_controls(panel: Panel, frame: pl.DataFrame, policy: Policy = POLICY) -> list[SyntheticControl]:
    """The largest shocks per capita against a donor pool of the metros whose shock is small (absolute shock at
    or below the median), on the quarterly log index from the first period, normalised to the last pre period.
    Every donor is treated in turn as a placebo."""
    a, _ = policy.migration_window
    q = panel.metro_quarter.filter(
        pl.col("index_at").is_not_null() & pl.col("cbsa_code").is_in(frame["cbsa_code"].to_list())
    )
    periods = sorted(p for p in q["period"].unique().to_list() if p >= policy.synthetic_control_first_period)
    pre_periods = sum(1 for p in periods if p <= a)
    ensure(pre_periods >= 8, "the synthetic control needs at least eight pre periods")
    wide = (
        q.filter(pl.col("period").is_in(periods))
        .pivot(on="period", index="cbsa_code", values="index_at")
        .sort("cbsa_code")
    )
    complete = wide.filter(pl.all_horizontal([pl.col(p).is_not_null() for p in periods]))
    series: dict[str, np.ndarray] = {}
    for row in complete.iter_rows(named=True):
        path = np.log(np.array([row[p] for p in periods], dtype=np.float64))
        series[str(row["cbsa_code"])] = path - path[pre_periods - 1]
    present = frame.filter(pl.col("cbsa_code").is_in(list(series)))
    treated = (
        present.sort("migration_shock", descending=True)
        .head(policy.synthetic_control_metros)["cbsa_code"]
        .to_list()
    )
    cutoff = float(present["migration_shock"].abs().median())
    donors = present.filter(pl.col("migration_shock").abs() <= cutoff)["cbsa_code"].to_list()
    out: list[SyntheticControl] = []
    for code in treated:
        pool = {str(k): series[str(k)] for k in donors if k != code}
        pool[str(code)] = series[str(code)]
        out.append(synthetic_control(str(code), pool, pre_periods=pre_periods))
    return out


def estimate(panel: Panel, policy: Policy = POLICY) -> ChapterResult:
    frame = cross_section(panel, policy)
    main, placebo = fit(frame)
    branch = message_rule(main, placebo)
    controls = synthetic_controls(panel, frame, policy)
    a, b = policy.migration_window
    titles = {
        r["cbsa_code"]: r["cbsa_title"] for r in frame.select("cbsa_code", "cbsa_title").iter_rows(named=True)
    }
    r = ChapterResult(
        number=NUMBER,
        slug=SLUG,
        source=panel.source,
        population=f"{frame.height} metropolitan areas with migration over {policy.migration_years[0]} and {policy.migration_years[1]} and the index in both windows ({main.clusters} states)",
        branch=branch.name,
        message=branch.text,
        reported_years=[int(b[:4])],
    )
    r.put("ch7.window", f"{a} to {b}", "text")
    r.put(
        "ch7.placebo_window",
        f"{policy.migration_placebo_window[0]} to {policy.migration_placebo_window[1]}",
        "text",
    )
    r.put("ch7.metros", int(frame.height), "int")
    r.put("ch7.clusters", main.clusters, "int")
    r.put("ch7.coef", main.estimate, "spct2", model="migration")
    r.put("ch7.low", main.low, "spct2", model="migration")
    r.put("ch7.high", main.high, "spct2", model="migration")
    r.put("ch7.p", main.p_value, "float3", model="migration")
    r.put("ch7.placebo.coef", placebo.estimate, "spct2", model="migration")
    r.put("ch7.placebo.low", placebo.low, "spct2", model="migration")
    r.put("ch7.placebo.high", placebo.high, "spct2", model="migration")
    r.put("ch7.placebo.p", placebo.p_value, "float3", model="migration")
    r.put("ch7.shock.p10", float(frame["migration_shock"].quantile(0.1)), "sfloat2")
    r.put("ch7.shock.p90", float(frame["migration_shock"].quantile(0.9)), "sfloat2")
    r.put(
        "ch7.pre.mean",
        float(np.average(frame["migration_pre"].to_numpy(), weights=frame["population"].to_numpy())),
        "sfloat2",
    )
    r.put(
        "ch7.pandemic.mean",
        float(np.average(frame["migration_pandemic"].to_numpy(), weights=frame["population"].to_numpy())),
        "sfloat2",
    )
    spread = float(frame["migration_shock"].quantile(0.9) - frame["migration_shock"].quantile(0.1))
    r.put("ch7.effect_p90_vs_p10", main.estimate * spread, "spct1", model="migration")
    r.put(
        "ch7.growth.mean",
        float(np.average(frame["growth"].to_numpy(), weights=frame["population"].to_numpy())),
        "pct1",
    )
    top = frame.sort("migration_shock", descending=True).head(3)
    r.put("ch7.top_gainers", "; ".join(str(x).split(",")[0] for x in top["cbsa_title"].to_list()), "text")
    r.put("ch7.branch", branch.name, "text")
    r.put("ch7.message", branch.text, "text")
    r.put_table(
        "ch7.regression",
        ["Window", "Growth per person per 100 residents of shock", "Low", "High", "p", "Clusters"],
        ["text", "spct2", "spct2", "spct2", "float3", "int"],
        [
            [f"{a} to {b}", main.estimate, main.low, main.high, main.p_value, main.clusters],
            [
                f"{policy.migration_placebo_window[0]} to {policy.migration_placebo_window[1]} (placebo)",
                placebo.estimate,
                placebo.low,
                placebo.high,
                placebo.p_value,
                placebo.clusters,
            ],
        ],
        model="migration",
    )
    sc_rows: list[list[Any]] = []
    sc_frames: list[pl.DataFrame] = []
    q_periods = sorted(
        p
        for p in panel.metro_quarter["period"].unique().to_list()
        if p >= policy.synthetic_control_first_period
    )
    for i, sc in enumerate(controls, start=1):
        band_low, band_high = placebo_band(sc)
        post_gap = sc.post_gap_mean
        peak_idx = int(np.argmax(sc.gap[sc.pre_periods :])) + sc.pre_periods
        last_gap = float(sc.gap[-1])
        reversal = float(sc.gap[peak_idx] - last_gap)
        name = str(titles.get(sc.treated, sc.treated))
        sc_rows.append(
            [
                name,
                post_gap,
                float(sc.gap[peak_idx]),
                q_periods[peak_idx] if peak_idx < len(q_periods) else "",
                last_gap,
                reversal,
                sc.p_value,
                sc.donors_searched,
                "; ".join(f"{titles.get(d, d).split(',')[0]} {w:.2f}" for d, w in sc.top_weights(3)),
            ]
        )
        r.put(f"ch7.sc.{i}.metro", name, "text")
        r.put(f"ch7.sc.{i}.post_gap", post_gap, "spct1", model="synthetic_control")
        r.put(f"ch7.sc.{i}.peak_gap", float(sc.gap[peak_idx]), "spct1", model="synthetic_control")
        r.put(f"ch7.sc.{i}.last_gap", last_gap, "spct1", model="synthetic_control")
        r.put(f"ch7.sc.{i}.p", sc.p_value, "float3", model="synthetic_control")
        r.put(f"ch7.sc.{i}.donors", sc.donors_searched, "int", model="synthetic_control")
        r.put(f"ch7.sc.{i}.pre_rmspe", sc.pre_rmspe, "float4", model="synthetic_control")
        periods_used = q_periods[: len(sc.actual)]
        sc_frames.append(
            pl.DataFrame(
                {
                    "metro": [name] * len(sc.actual),
                    "cbsa_code": [sc.treated] * len(sc.actual),
                    "period": periods_used,
                    "actual": sc.actual,
                    "synthetic": sc.synthetic,
                    "gap": sc.gap,
                    "band_low": band_low,
                    "band_high": band_high,
                    "post": [p > a for p in periods_used],
                }
            )
        )
    r.put("ch7.sc.count", len(controls), "int")
    if sc_rows:
        r.put_table(
            "ch7.synthetic_controls",
            [
                "Metro",
                "Mean post gap",
                "Peak gap",
                "Peak quarter",
                "Latest gap",
                "Reversal since peak",
                "Permutation p",
                "Donors searched",
                "Top weights",
            ],
            ["text", "spct1", "spct1", "quarter", "spct1", "pts1", "float3", "int", "text"],
            sc_rows,
            model="synthetic_control",
        )
    sc_frame = (
        pl.concat(sc_frames)
        if sc_frames
        else pl.DataFrame({"metro": [], "period": [], "actual": [], "synthetic": [], "gap": []})
    )
    r.marts["ch7_cross_section"] = frame
    r.marts["ch7_synthetic_controls"] = sc_frame
    r.figure = Figure(
        title=branch.text,
        subtitle=f"Price growth {a} to {b} against the migration shock per hundred residents (over {policy.migration_years[0]} and {policy.migration_years[1]} less {policy.migration_pre_years[0]} and {policy.migration_pre_years[1]}), with the placebo window beside it",
        sql=SQL,
        frames={"scatter": frame, "synthetic": sc_frame},
        model="migration",
        callout=f"placebo {format_value(placebo.estimate, 'spct2')} against headline {format_value(main.estimate, 'spct2')} per person per hundred",
    )
    r.method = {
        "estimator": "population weighted cross section on the migration shock with the pre pandemic migration as a control, state clusters; synthetic control on the simplex with every donor searched",
        "split": f"window {a} to {b}; placebo {policy.migration_placebo_window[0]} to {policy.migration_placebo_window[1]}",
        "interval": f"cluster robust by state, {main.clusters} clusters; permutation p values over {controls[0].donors_searched if controls else 0} donors",
        "family": "headline and placebo reported separately",
    }
    r.pushback = (
        "Migration follows affordability: people move to the metros they can afford, which pulls the coefficient toward "
        "zero or past it, and the recovery study shows the estimator failing under strong reverse causality while the "
        "placebo flags it only part of the time; that is the limit this chapter admits in print. The population estimates "
        "count domestic migration from July to June, so the migration years and the price window overlap by two quarters "
        "and not four. Remote work moved demand without moving many people, and that part is not in the migration series."
    )
    return r


# Recovery on the simulator


def simulate_estimate(world: World, policy: Policy = POLICY) -> list[Grade]:
    panel = from_world(world, policy)
    frame = cross_section(panel, policy)
    main, placebo = fit(frame)
    truth = world.truth.beta_demand
    flagged = float(not placebo.covers(0.0))
    return [
        Grade(
            "migration_effect",
            main.estimate,
            truth,
            main.low,
            main.high,
            flag=flagged,
            detail="flag: the placebo excluded zero",
        ),
        Grade("migration_placebo", placebo.estimate, 0.0, placebo.low, placebo.high),
    ]
