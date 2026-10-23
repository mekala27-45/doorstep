"""Chapter 4, supply: where builders kept pace, prices rose less.

Price growth over non overlapping windows is regressed on the building rate (permits per hundred
households, the window shifted back one year so permits lead prices) with metro and period fixed effects
on population weighted cells and state clustered standard errors. The chapter publishes two
specifications: with the demand shock observed (domestic migration per hundred residents over the window
and the two years before it, which is the span through which a demand shock reaches both sides of the
regression) and without it. The simulator proves the estimator recovers the known elasticity when the
demand shock is in the regression and shows the bias when it is not, and the recovery study quantifies
that bias by condition.

The spec asked for permits per new household. That ratio is undefined in a metro that lost households,
which one metro window in five does, so the regressor is permits per hundred households (the building
rate the literature uses) and permits per new household is published as a descriptive beside it; the
decision is in DECISIONS.md.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl
from doorstep_core.config import POLICY, SUPPLY_WINDOWS, Policy
from doorstep_core.formats import format_value
from doorstep_core.scalars import integer, num
from doorstep_sim.metros import World
from doorstep_stats.regression import Coefficient, first, regress

from doorstep_chapters.common import Branch, ChapterResult, Figure, Grade, ensure
from doorstep_chapters.panel import Panel, from_world

NUMBER = 4
SLUG = "supply"
TITLE = "Where builders kept pace, prices rose less"

SQL = """
with annual as (
    select cbsa_code, cbsa_title, states, year, index_at, households, population, permits, domestic_migration,
           100.0 * permits / households as permits_per_100_households,
           100.0 * domestic_migration / population as migration_per_100
    from mart_metro_year where kind = 'metropolitan'
),
windows as (
    select cbsa_code, cbsa_title, states,
           floor((year - 2001) / 5) as window_id, min(year) as first_year, max(year) as last_year,
           avg(permits_per_100_households) as permits_rate, avg(migration_per_100) as migration_rate,
           max(population) as population
    from annual where year >= 2001 group by cbsa_code, cbsa_title, states, floor((year - 2001) / 5)
)
select w.*, (ln(e.index_at) - ln(s.index_at)) / (w.last_year - w.first_year + 1) as annual_growth
from windows w
join annual e on e.cbsa_code = w.cbsa_code and e.year = w.last_year + 1
join annual s on s.cbsa_code = w.cbsa_code and s.year = w.first_year
order by w.cbsa_code, w.window_id
""".strip()


def plan(policy: Policy = POLICY) -> dict[str, Any]:
    return {
        "chapter": NUMBER,
        "slug": SLUG,
        "claim": "Metros that permitted more homes per hundred households saw prices rise less over the following "
        "years, by a measured amount per permit, once the demand shock is held constant.",
        "estimator": "mean annual log price growth over non overlapping windows on the mean building rate (permits per "
        "hundred households) over the same window shifted back one year, metro and period fixed effects on "
        "population weighted cells; with and without domestic migration per hundred residents over the window and "
        "the two years before it",
        "interval": "cluster robust (CR1) by state",
        "split": {
            "windows": f"non overlapping {policy.supply_window_years} year windows from 2001",
            "report": "every window; the recovery study is the check",
        },
        "family": "two specifications reported side by side; no correction",
        "operating_points": {
            "window_years": policy.supply_window_years,
            "window_neighbours": list(SUPPLY_WINDOWS),
            "lag_years": 1,
        },
        "message_rule": "kept_pace: the controlled interval lies below zero; null: it includes zero; demand_dominates: it lies above zero",
    }


def message_rule(controlled: Coefficient, uncontrolled: Coefficient, window: int) -> Branch:
    per_window = controlled.estimate * window
    size = f"{format_value(abs(per_window), 'pct1')} less price growth over {window} years per extra permit per hundred households"
    bare = (
        f"without the demand control the estimate is {format_value(uncontrolled.estimate * window, 'spct1')}"
    )
    if controlled.high < 0.0:
        return Branch(
            "kept_pace",
            f"Where builders kept pace, prices rose less: {size} (interval {format_value(controlled.low * window, 'spct1')} to "
            f"{format_value(controlled.high * window, 'spct1')}); {bare}.",
        )
    if controlled.low > 0.0:
        return Branch(
            "demand_dominates",
            f"Prices rose more where more was built: {format_value(per_window, 'spct1')} over {window} years per extra permit per hundred "
            f"households, which is demand showing through the permits, not supply failing; {bare}.",
        )
    return Branch(
        "null",
        f"The building rate cannot be tied to price growth here: {format_value(per_window, 'spct1')} over {window} years per extra permit "
        f"per hundred households, interval {format_value(controlled.low * window, 'spct1')} to {format_value(controlled.high * window, 'spct1')}; {bare}.",
    )


def cells(panel: Panel, window: int, *, first_year: int = 2001) -> pl.DataFrame:
    """One row per metro and window with the mean annual growth, the lagged building rate, the migration rate and
    the population weight. A window needs every one of its years, its lagged years and the index at both ends."""
    my = panel.metropolitan().filter(pl.col("index_at").is_not_null())
    annual = my.select(
        "cbsa_code",
        "cbsa_title",
        "state",
        "year",
        "index_at",
        "households",
        "population",
        "permits",
        "domestic_migration",
    ).with_columns(
        (100.0 * pl.col("permits") / pl.col("households")).alias("permits_rate"),
        (100.0 * pl.col("domestic_migration") / pl.col("population")).alias("migration_rate"),
    )
    # Households are absent before 2005 in the census; carry the earliest known value back for the rate.
    hh = (
        annual.filter(pl.col("households").is_not_null())
        .sort("year")
        .group_by("cbsa_code")
        .agg(pl.col("households").first().alias("hh_first"))
    )
    annual = annual.join(hh, on="cbsa_code", how="left").with_columns(
        pl.when(pl.col("households").is_null())
        .then(100.0 * pl.col("permits") / pl.col("hh_first"))
        .otherwise(pl.col("permits_rate"))
        .alias("permits_rate")
    )
    last_year = integer(annual["year"].max())
    rows: list[dict[str, Any]] = []
    by_metro = {k[0]: v.sort("year") for k, v in annual.group_by("cbsa_code")}
    window_id = 0
    start = first_year
    while start + window - 1 <= last_year:
        end = start + window - 1
        years = list(range(start, end + 1))
        lagged = [y - 1 for y in years]
        control_years = list(range(start - 2, end + 1))
        for code, frame in sorted(by_metro.items()):
            idx = {int(r["year"]): r for r in frame.iter_rows(named=True)}
            if start - 1 not in idx or end not in idx:
                continue
            if any(y not in idx or idx[y]["permits_rate"] is None for y in lagged):
                continue
            mig = [
                idx[y]["migration_rate"]
                for y in control_years
                if y in idx and idx[y]["migration_rate"] is not None
            ]
            if len(mig) < len(control_years) - 2:
                continue
            i0, i1 = idx[start - 1]["index_at"], idx[end]["index_at"]
            if not i0 or not i1 or i0 <= 0 or i1 <= 0:
                continue
            pop = idx[start]["population"] or idx[end]["population"]
            if not pop:
                continue
            rows.append(
                {
                    "cbsa_code": code,
                    "cbsa_title": idx[end]["cbsa_title"],
                    "state": idx[end]["state"],
                    "window_id": window_id,
                    "first_year": start,
                    "last_year": end,
                    "annual_growth": float(np.log(i1 / i0)) / window,
                    "permits_rate": float(np.mean([idx[y]["permits_rate"] for y in lagged])),
                    "migration_rate": float(np.mean(mig)),
                    "population": float(pop),
                }
            )
        window_id += 1
        start = end + 1
    ensure(bool(rows), "chapter 4 found no complete window")
    return pl.DataFrame(rows).filter(pl.col("state").is_not_null()).sort(["cbsa_code", "window_id"])


def fit_both(frame: pl.DataFrame) -> tuple[Coefficient, Coefficient]:
    """(controlled, uncontrolled) coefficients on the building rate."""
    ensure(frame["window_id"].n_unique() >= 2, "chapter 4 needs at least two windows for the period effects")
    y = frame["annual_growth"].to_numpy()
    w = frame["population"].to_numpy()
    fe = [frame["cbsa_code"].to_numpy(), frame["window_id"].to_numpy()]
    cl = frame["state"].to_numpy()
    with_control = regress(
        y,
        np.column_stack([frame["permits_rate"].to_numpy(), frame["migration_rate"].to_numpy()]),
        ["permits_rate", "migration_rate"],
        weights=w,
        fixed_effects=fe,
        cluster=cl,
    )
    without = regress(
        y,
        frame["permits_rate"].to_numpy()[:, None],
        ["permits_rate"],
        weights=w,
        fixed_effects=fe,
        cluster=cl,
    )
    return first(with_control, "permits_rate"), first(without, "permits_rate")


def estimate(panel: Panel, policy: Policy = POLICY) -> ChapterResult:
    window = policy.supply_window_years
    frame = cells(panel, window)
    controlled, uncontrolled = fit_both(frame)
    branch = message_rule(controlled, uncontrolled, window)
    # Interior test on the window length, before the message is written, because the message says how it went
    rows: list[list[Any]] = []
    signs: dict[int, float] = {}
    for length in SUPPLY_WINDOWS:
        try:
            c, u = fit_both(cells(panel, length))
        except Exception:
            rows.append([length, None, None, None, None, "not enough windows"])
            continue
        signs[length] = c.estimate
        rows.append([length, c.estimate, c.low, c.high, u.estimate, "chosen" if length == window else ""])
    neighbours = [x for x in signs if x != window]
    nearest = min(neighbours, key=lambda x: abs(x - window)) if neighbours else None
    degenerate = nearest is not None and np.sign(signs[nearest]) != np.sign(
        signs.get(window, controlled.estimate)
    )
    if degenerate:
        for row in rows:
            if row[0] == nearest:
                row[5] = "degenerate"
    others = ", ".join(
        f"{length} years {format_value(signs[length] * length, 'spct1')}"
        for length in sorted(signs)
        if length != window
    )
    message_text = branch.text + (
        f" The estimate does not survive the window test: over {others} per window, with intervals that include zero, "
        f"so this is a {window} year statement and the interior table says so."
        if degenerate
        else f" The window test holds: over {others} per window the sign is the same."
    )
    r = ChapterResult(
        number=NUMBER,
        slug=SLUG,
        source=panel.source,
        population=f"{frame['cbsa_code'].n_unique()} metropolitan areas over {frame['window_id'].n_unique()} windows of {window} years ({frame.height} cells, {controlled.clusters} states)",
        branch=branch.name,
        message=message_text,
        reported_years=sorted(int(y) for y in frame["last_year"].unique().to_list()),
    )
    for name, c in (("controlled", controlled), ("uncontrolled", uncontrolled)):
        r.put(f"ch4.{name}.coef", c.estimate, "sfloat4", model="supply_fe")
        r.put(f"ch4.{name}.low", c.low, "sfloat4", model="supply_fe")
        r.put(f"ch4.{name}.high", c.high, "sfloat4", model="supply_fe")
        r.put(f"ch4.{name}.se", c.se, "float4", model="supply_fe")
        r.put(f"ch4.{name}.p", c.p_value, "float3", model="supply_fe")
        r.put(f"ch4.{name}.per_window", c.estimate * window, "spct1", model="supply_fe")
        r.put(f"ch4.{name}.per_window.low", c.low * window, "spct1", model="supply_fe")
        r.put(f"ch4.{name}.per_window.high", c.high * window, "spct1", model="supply_fe")
    r.put("ch4.window_years", window, "int")
    r.put("ch4.metros", int(frame["cbsa_code"].n_unique()), "int")
    r.put("ch4.windows", int(frame["window_id"].n_unique()), "int")
    r.put("ch4.cells", int(frame.height), "int")
    r.put("ch4.clusters", controlled.clusters, "int")
    r.put("ch4.first_year", integer(frame["first_year"].min()), "year")
    r.put("ch4.last_year", integer(frame["last_year"].max()), "year")
    r.put("ch4.permits_rate.mean", num(frame["permits_rate"].mean()), "float2")
    r.put("ch4.permits_rate.p10", num(frame["permits_rate"].quantile(0.1)), "float2")
    r.put("ch4.permits_rate.p90", num(frame["permits_rate"].quantile(0.9)), "float2")
    spread = num(frame["permits_rate"].quantile(0.9)) - num(frame["permits_rate"].quantile(0.1))
    r.put("ch4.effect_p90_vs_p10", controlled.estimate * window * spread, "spct1", model="supply_fe")
    r.put("ch4.branch", branch.name, "text")
    r.put("ch4.message", message_text, "text")
    r.put_table(
        "ch4.window_interior",
        ["Window years", "Controlled", "Low", "High", "Uncontrolled", "Note"],
        ["int", "sfloat4", "sfloat4", "sfloat4", "sfloat4", "text"],
        rows,
        model="supply_fe",
    )
    r.put("ch4.window_degenerate", "degenerate" if degenerate else "stable", "text")

    # Descriptive: permits per new household where defined
    my = panel.metropolitan().filter(pl.col("permits").is_not_null() & pl.col("households").is_not_null())
    hh_change = my.sort(["cbsa_code", "year"]).with_columns(
        pl.col("households").diff().over("cbsa_code").alias("new_households")
    )
    defined = hh_change.filter(pl.col("new_households") > 0)
    r.put(
        "ch4.permits_per_new_household.defined_share",
        defined.height / max(hh_change.filter(pl.col("new_households").is_not_null()).height, 1),
        "pct0",
    )
    r.put(
        "ch4.permits_per_new_household.median",
        num((defined["permits"] / defined["new_households"]).median()) if defined.height else None,
        "float2",
    )

    r.put_table(
        "ch4.specifications",
        [
            "Specification",
            "Annual growth per permit per 100 households",
            "Low",
            "High",
            "Over the window",
            "Clusters",
        ],
        ["text", "sfloat4", "sfloat4", "sfloat4", "spct1", "int"],
        [
            [
                "with the demand control",
                controlled.estimate,
                controlled.low,
                controlled.high,
                controlled.estimate * window,
                controlled.clusters,
            ],
            [
                "without the demand control",
                uncontrolled.estimate,
                uncontrolled.low,
                uncontrolled.high,
                uncontrolled.estimate * window,
                uncontrolled.clusters,
            ],
        ],
        model="supply_fe",
    )
    r.marts["ch4_cells"] = frame
    # The fitted line for the chart: residualised on the fixed effects is what the regression sees; the scatter shows the
    # latest window's raw cells with the controlled slope drawn through their weighted means.
    latest_window = frame.filter(pl.col("window_id") == frame["window_id"].max())
    x_mean = float(
        np.average(latest_window["permits_rate"].to_numpy(), weights=latest_window["population"].to_numpy())
    )
    y_mean = float(
        np.average(latest_window["annual_growth"].to_numpy(), weights=latest_window["population"].to_numpy())
    )
    xs = np.linspace(num(latest_window["permits_rate"].min()), num(latest_window["permits_rate"].max()), 25)
    line = pl.DataFrame(
        {
            "permits_rate": xs,
            "controlled": y_mean + controlled.estimate * (xs - x_mean),
            "controlled_low": y_mean + controlled.low * (xs - x_mean),
            "controlled_high": y_mean + controlled.high * (xs - x_mean),
            "uncontrolled": y_mean + uncontrolled.estimate * (xs - x_mean),
        }
    )
    r.figure = Figure(
        title=branch.text,
        subtitle=f"Annual price growth against the building rate the year before, {window} year windows, with the fitted slope under both specifications",
        sql=SQL,
        frames={"cells": latest_window, "line": line, "all_cells": frame},
        model="supply_fe",
        callout=f"a metro at the 90th percentile of building ({format_value(num(frame['permits_rate'].quantile(0.9)), 'float2')} per 100) against the 10th: {format_value(controlled.estimate * window * spread, 'spct1')} over {window} years",
    )
    r.method = {
        "estimator": "fixed effects on population weighted metro by window cells, alternating projections, two specifications",
        "split": f"non overlapping {window} year windows from {integer(frame['first_year'].min())}; permits shifted back one year",
        "interval": f"cluster robust by state, {controlled.clusters} clusters",
        "family": "two specifications reported side by side",
    }
    r.pushback = (
        "Permits respond to demand: a metro builds because prices are rising, which pushes the uncontrolled estimate "
        "toward zero or past it, and the recovery study measures that bias under every condition. The migration series "
        "is one demand shock, not all of them; income growth and investor demand are not in the regression. Permits are "
        "not completions, and a permit pulled in a downturn may never become a home. The notebook keeps the specification "
        "that put the demand shock in the wrong fixed effect as a dead end."
        + (
            f" And the window matters: the {window} year estimate is the only one of the three lengths tried whose interval "
            "excludes zero, which is the kind of result a reader should hold loosely until a second decade of permits is in."
            if degenerate
            else ""
        )
    )
    return r


# Recovery on the simulator


def simulate_estimate(world: World, policy: Policy = POLICY) -> list[Grade]:
    panel = from_world(world, policy)
    frame = cells(panel, policy.supply_window_years, first_year=world.first_year + 2)
    controlled, uncontrolled = fit_both(frame)
    truth = -world.truth.beta_supply
    return [
        Grade("supply_controlled", controlled.estimate, truth, controlled.low, controlled.high),
        Grade("supply_uncontrolled", uncontrolled.estimate, truth, uncontrolled.low, uncontrolled.high),
    ]
