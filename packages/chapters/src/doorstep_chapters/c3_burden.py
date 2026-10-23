"""Chapter 3, the rent burden: a distribution problem that the median hides.

The share of renter households whose rent takes thirty percent or more of income (cost burdened) and
fifty percent or more (severely burdened), by metro and year, the same shares by household income group,
and the owner cost burden for owners with a mortgage beside them. The national severely burdened series
is searched for changepoints with PELT under a BIC penalty. The message rule asks two things of the
latest year: whether the median renter is below the thirty percent line in most metros, and whether the
severely burdened share holds above the stated line with an interval that clears it; when both hold, the
median hides the problem, and every other outcome gets its own sentence.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl
from doorstep_core.config import POLICY, SEVERE_LINES, Policy
from doorstep_core.formats import format_value
from doorstep_core.scalars import integer, num
from doorstep_sim.metros import World
from doorstep_stats.bootstrap import Interval, block_bootstrap, ratio
from doorstep_stats.pelt import bic_penalty, estimate_sigma, pelt

from doorstep_chapters.common import Branch, ChapterResult, Figure, Grade, ensure, split_for
from doorstep_chapters.panel import Panel, from_world

NUMBER = 3
SLUG = "burden"
TITLE = "The rent burden is a distribution problem"

SQL = """
select year,
       sum(renters_burdened) / sum(renters_with_share) as burdened_share,
       sum(renters_severe) / sum(renters_with_share) as severe_share,
       sum(owners_mortgage_burdened) / sum(owners_mortgage_with_share) as owner_mortgage_burdened_share,
       sum(case when median_rent_share < 0.30 then 1 else 0 end) as metros_median_under_30,
       count(*) as metros
from mart_metro_year
where kind = 'metropolitan' and renters_with_share > 0
group by year
order by year
""".strip()

SQL_INCOME = """
select year, income_group, group_order,
       sum(renters_burdened) / sum(renters_with_share) as burdened_share,
       sum(renters_severe) / sum(renters_with_share) as severe_share
from mart_rent_burden_by_income
group by year, income_group, group_order
order by year, group_order
""".strip()


def plan(policy: Policy = POLICY) -> dict[str, Any]:
    return {
        "chapter": NUMBER,
        "slug": SLUG,
        "claim": "The median renter is not cost burdened in most metros while a stated share of renters pays half "
        "their income in rent; the median hides a distribution problem.",
        "estimator": "renters paying thirty and fifty percent or more over renters with a computed share, by metro, "
        "year and income group; PELT changepoints under a BIC penalty on the national severely burdened series",
        "interval": f"block bootstrap over metros with {policy.bootstrap_replicates} replicates for the aggregates; the "
        "census ratio margin of error for each metro",
        "split": split_for(policy)
        | {
            "note": "the BIC penalty and the stated line are fixed before the data; the headline is the latest release"
        },
        "family": "one comparison against the stated line; no correction",
        "operating_points": {
            "burden_line": policy.affordable_line,
            "severe_line": policy.severe_line,
            "severe_share_line": policy.severe_share_line,
            "severe_share_neighbours": list(SEVERE_LINES),
            "pelt_min_size": 3,
            "pelt_penalty": "BIC with two parameters per changepoint and the MAD noise scale",
        },
        "message_rule": "median_hides: the median renter is under the line in most metros and the severe interval clears the "
        "stated share; median_burdened: the median renter is burdened in most metros; at_line: the severe interval "
        "includes the stated share; below_line: the severe interval sits below it",
    }


def message_rule(
    median_under_share: float, severe: Interval, line: float, latest_year: int, changepoints: list[int]
) -> Branch:
    moved = (
        f" The national series moved and stayed moved in {', '.join(str(c) for c in changepoints)}."
        if changepoints
        else " The national series shows no changepoint."
    )
    if median_under_share > 0.5 and severe.low > line:
        return Branch(
            "median_hides",
            f"The median hides it: in {format_value(median_under_share, 'pct0')} of metros the median renter pays under thirty "
            f"percent of income, while {format_value(severe.estimate, 'pct1')} of renters pay half or more "
            f"(interval {format_value(severe.low, 'pct1')} to {format_value(severe.high, 'pct1')}, above the {format_value(line, 'pct0')} line) in {latest_year}."
            + moved,
        )
    if median_under_share <= 0.5:
        return Branch(
            "median_burdened",
            f"The median renter is burdened in {format_value(1.0 - median_under_share, 'pct0')} of metros in {latest_year}, so the "
            f"median hides nothing; the problem is the whole distribution, with {format_value(severe.estimate, 'pct1')} of renters "
            f"paying half or more (interval {format_value(severe.low, 'pct1')} to {format_value(severe.high, 'pct1')})." + moved,
        )
    if severe.covers(line):
        return Branch(
            "at_line",
            f"The severely burdened share ({format_value(severe.estimate, 'pct1')}, interval {format_value(severe.low, 'pct1')} to "
            f"{format_value(severe.high, 'pct1')}) cannot be told from the {format_value(line, 'pct0')} line in {latest_year}."
            + moved,
        )
    return Branch(
        "below_line",
        f"The severely burdened share sits below the {format_value(line, 'pct0')} line in {latest_year} "
        f"({format_value(severe.estimate, 'pct1')}, interval {format_value(severe.low, 'pct1')} to {format_value(severe.high, 'pct1')})."
        + moved,
    )


def _metro_rows(panel: Panel) -> pl.DataFrame:
    return panel.metropolitan().filter(
        pl.col("renters_with_share").is_not_null()
        & (pl.col("renters_with_share") > 0)
        & pl.col("renters_burdened").is_not_null()
    )


def aggregate_interval(
    frame: pl.DataFrame, numerator: str, policy: Policy, label: str, replicates: int | None = None
) -> Interval:
    sums = np.column_stack([frame[numerator].to_numpy(), frame["renters_with_share"].to_numpy()]).astype(
        np.float64
    )
    return block_bootstrap(
        frame["cbsa_code"].to_numpy(),
        sums,
        ratio(0, 1),
        replicates=replicates or policy.bootstrap_replicates,
        seed=policy.seed,
        label=label,
        level=policy.interval_level,
    )


def national_series(panel: Panel) -> pl.DataFrame:
    """The national shares by year: the census national row where it exists, the metro aggregate otherwise."""
    nat = panel.national_year
    if (
        "renter_severe_share" in nat.columns
        and nat.filter(pl.col("renter_severe_share").is_not_null()).height > 0
    ):
        out = nat.filter(pl.col("renter_severe_share").is_not_null()).select(
            "year", "renter_burdened_share", "renter_severe_share"
        )
    else:
        out = (
            _metro_rows(panel)
            .group_by("year")
            .agg(
                (pl.col("renters_burdened").sum() / pl.col("renters_with_share").sum()).alias(
                    "renter_burdened_share"
                ),
                (pl.col("renters_severe").sum() / pl.col("renters_with_share").sum()).alias(
                    "renter_severe_share"
                ),
            )
        )
    return out.sort("year")


def changepoints(series: pl.DataFrame, column: str = "renter_severe_share") -> list[int]:
    """Years at which a new segment starts, from PELT with the BIC penalty (two parameters per change)."""
    values = series[column].to_numpy().astype(np.float64)
    years = series["year"].to_list()
    if values.size < 6:
        return []
    sigma = estimate_sigma(values)
    penalty = bic_penalty(values.size, max(sigma, 1e-6), n_params=2)
    cps = pelt(values, penalty, min_size=3)
    return [int(years[c]) for c in cps]


def ratio_moe(num: np.ndarray, num_moe: np.ndarray, den: np.ndarray, den_moe: np.ndarray) -> np.ndarray:
    """The census handbook margin for a proportion: sqrt(moe_num^2 - p^2 moe_den^2) / den, falling back to
    the ratio form when the proportion form goes negative."""
    p = num / den
    inside = num_moe**2 - (p**2) * den_moe**2
    alt = num_moe**2 + (p**2) * den_moe**2
    return np.asarray(
        np.where(inside >= 0, np.sqrt(np.maximum(inside, 0.0)), np.sqrt(alt)) / den, dtype=np.float64
    )


def metro_shares(panel: Panel) -> pl.DataFrame:
    rows = _metro_rows(panel)
    num_b = rows["renters_burdened"].to_numpy().astype(np.float64)
    num_s = rows["renters_severe"].to_numpy().astype(np.float64)
    den = rows["renters_with_share"].to_numpy().astype(np.float64)
    moe_b = rows["renters_burdened_moe"].fill_null(0.0).to_numpy().astype(np.float64)
    moe_s = rows["renters_severe_moe"].fill_null(0.0).to_numpy().astype(np.float64)
    moe_d = rows["renters_with_share_moe"].fill_null(0.0).to_numpy().astype(np.float64)
    return (
        rows.select(
            "cbsa_code",
            "cbsa_title",
            "year",
            "renters_with_share",
            "median_rent_share",
            "owner_mortgage_burdened_share",
        )
        .with_columns(
            pl.Series("burdened_share", num_b / den),
            pl.Series("burdened_moe", ratio_moe(num_b, moe_b, den, moe_d)),
            pl.Series("severe_share", num_s / den),
            pl.Series("severe_moe", ratio_moe(num_s, moe_s, den, moe_d)),
        )
        .sort(["cbsa_code", "year"])
    )


def estimate(panel: Panel, policy: Policy = POLICY, *, replicates: int | None = None) -> ChapterResult:
    rows = _metro_rows(panel)
    ensure(rows.height > 0, "chapter 3 has no renter burden rows")
    latest = integer(rows["year"].max())
    latest_rows = rows.filter(pl.col("year") == latest)
    severe = aggregate_interval(latest_rows, "renters_severe", policy, f"ch3-severe-{latest}", replicates)
    burdened = aggregate_interval(
        latest_rows, "renters_burdened", policy, f"ch3-burdened-{latest}", replicates
    )
    with_median = latest_rows.filter(pl.col("median_rent_share").is_not_null())
    median_under = (
        num((with_median["median_rent_share"] < policy.affordable_line).mean()) if with_median.height else 0.0
    )
    series = national_series(panel)
    cps = changepoints(series)
    branch = message_rule(median_under, severe, policy.severe_share_line, latest, cps)
    r = ChapterResult(
        number=NUMBER,
        slug=SLUG,
        source=panel.source,
        population=f"every metropolitan area with renters in the census tables, 2005 to {latest} ({latest_rows.height} metros in {latest})",
        branch=branch.name,
        message=branch.text,
        reported_years=[latest],
    )
    r.put("ch3.latest_year", latest, "year")
    r.put("ch3.metros", int(latest_rows.height), "int")
    r.put("ch3.severe.share", severe.estimate, "pct1", model="bootstrap")
    r.put("ch3.severe.low", severe.low, "pct1", model="bootstrap")
    r.put("ch3.severe.high", severe.high, "pct1", model="bootstrap")
    r.put("ch3.burdened.share", burdened.estimate, "pct1", model="bootstrap")
    r.put("ch3.burdened.low", burdened.low, "pct1", model="bootstrap")
    r.put("ch3.burdened.high", burdened.high, "pct1", model="bootstrap")
    r.put("ch3.replicates", severe.replicates, "int")
    r.put("ch3.median_under_line_share", median_under, "pct0", model="burden")
    r.put(
        "ch3.median_under_line_metros",
        int((with_median["median_rent_share"] < policy.affordable_line).sum()),
        "int",
        model="burden",
    )
    r.put("ch3.severe_share_line", policy.severe_share_line, "pct0")
    r.put("ch3.changepoints", ", ".join(str(c) for c in cps) if cps else "none", "text", model="pelt")
    r.put("ch3.changepoint_count", len(cps), "int", model="pelt")
    r.put("ch3.branch", branch.name, "text")
    r.put("ch3.message", branch.text, "text")
    owners = latest_rows.filter(pl.col("owner_mortgage_burdened_share").is_not_null())
    r.put(
        "ch3.owner_mortgage_burdened_share",
        num((owners["owner_mortgage_burdened_share"] * owners["renters_with_share"]).sum())
        / num(owners["renters_with_share"].sum())
        if owners.height
        else None,
        "pct1",
        model="burden",
    )
    first = series.row(0, named=True)
    last = series.row(series.height - 1, named=True)
    r.put("ch3.national.first_year", int(first["year"]), "year")
    r.put("ch3.national.severe.first", float(first["renter_severe_share"]), "pct1", model="burden")
    r.put("ch3.national.severe.latest", float(last["renter_severe_share"]), "pct1", model="burden")
    r.put("ch3.national.burdened.latest", float(last["renter_burdened_share"]), "pct1", model="burden")
    r.put(
        "ch3.national.severe.change",
        float(last["renter_severe_share"] - first["renter_severe_share"]),
        "pts1",
        model="burden",
    )

    # Interior test on the stated line
    interior: list[list[Any]] = []
    signs: dict[float, bool] = {}
    for line in SEVERE_LINES:
        clears = severe.low > line
        signs[line] = clears
        interior.append(
            [
                line,
                severe.estimate,
                "clears" if clears else ("includes" if severe.covers(line) else "below"),
                "chosen" if line == policy.severe_share_line else "",
            ]
        )
    neighbours = [x for x in SEVERE_LINES if x != policy.severe_share_line]
    nearest = min(neighbours, key=lambda x: abs(x - policy.severe_share_line))
    degenerate = signs[nearest] != signs[policy.severe_share_line]
    if degenerate:
        for row in interior:
            if row[0] == nearest:
                row[3] = "degenerate"
    r.put_table(
        "ch3.line_interior",
        ["Stated line", "Severe share", "Interval against the line", "Note"],
        ["pct0", "pct1", "text", "text"],
        interior,
    )
    r.put("ch3.line_degenerate", "degenerate" if degenerate else "stable", "text")

    # By income group, latest year
    groups = panel.burden_by_income
    group_rows: list[list[Any]] = []
    if groups is not None and groups.height:
        g_latest = integer(groups["year"].max())
        g = (
            groups.filter(pl.col("year") == g_latest)
            .group_by("income_group", "group_order")
            .agg(
                pl.col("renters_with_share").sum(),
                pl.col("renters_burdened").sum(),
                pl.col("renters_severe").sum(),
            )
            .sort("group_order")
        )
        for x in g.iter_rows(named=True):
            den = float(x["renters_with_share"])
            group_rows.append(
                [
                    x["income_group"].replace("_", " "),
                    den,
                    float(x["renters_burdened"]) / den if den else None,
                    float(x["renters_severe"]) / den if den else None,
                ]
            )
        r.put("ch3.groups.year", g_latest, "year")
        lowest = group_rows[0]
        highest = group_rows[-1]
        r.put("ch3.groups.lowest.severe", lowest[3], "pct0", model="burden")
        r.put("ch3.groups.highest.severe", highest[3], "pct0", model="burden")
        r.marts["ch3_burden_by_income"] = (
            groups.group_by("year", "income_group", "group_order")
            .agg(
                pl.col("renters_with_share").sum(),
                pl.col("renters_burdened").sum(),
                pl.col("renters_severe").sum(),
            )
            .with_columns(
                (pl.col("renters_burdened") / pl.col("renters_with_share")).alias("burdened_share"),
                (pl.col("renters_severe") / pl.col("renters_with_share")).alias("severe_share"),
            )
            .sort(["year", "group_order"])
        )
    else:
        r.put("ch3.groups.year", None, "year")
        r.put("ch3.groups.lowest.severe", None, "pct0")
        r.put("ch3.groups.highest.severe", None, "pct0")
    if group_rows:
        r.put_table(
            "ch3.by_income_group",
            ["Income group", "Renters", "Burdened", "Severely burdened"],
            ["text", "int", "pct1", "pct1"],
            group_rows,
            model="burden",
        )

    # The bands by year (national): under 30, 30 to 50, 50 and over
    bands = series.with_columns(
        (1.0 - pl.col("renter_burdened_share")).alias("under_30"),
        (pl.col("renter_burdened_share") - pl.col("renter_severe_share")).alias("from_30_to_50"),
        pl.col("renter_severe_share").alias("over_50"),
    )
    r.put_table(
        "ch3.bands",
        ["Year", "Under 30 percent", "30 to 50 percent", "50 percent and over"],
        ["year", "pct1", "pct1", "pct1"],
        [
            [int(x["year"]), float(x["under_30"]), float(x["from_30_to_50"]), float(x["over_50"])]
            for x in bands.iter_rows(named=True)
        ],
        model="burden",
    )
    shares = metro_shares(panel)
    r.marts["ch3_metro_shares"] = shares
    r.marts["ch3_national_bands"] = bands
    r.figure = Figure(
        title=branch.text,
        subtitle="Renter households by the share of income their rent takes, nationally by year, with the thirty and fifty percent lines",
        sql=SQL,
        frames={
            "bands": bands,
            "metros": shares.filter(pl.col("year") == latest),
            "groups": r.marts.get("ch3_burden_by_income", bands),
        },
        model="burden",
        callout=f"{format_value(severe.estimate, 'pct1')} of renters pay half or more of income in {latest}",
    )
    r.method = {
        "estimator": "burdened and severely burdened renters over renters with a computed share; PELT with a BIC penalty on the national series",
        "split": "no fitted parameter; the penalty and the stated line are fixed before the data; the headline is the latest release",
        "interval": f"block bootstrap over metros, {severe.replicates} replicates; census ratio margins per metro",
        "family": "one comparison against the stated line",
    }
    r.pushback = (
        "Gross rent as a share of income is computed only for renters who reported both, and the census excludes those "
        "it could not compute; a metro where many students or retirees rent shows a high severe share that is income, "
        "not rent. The bands are left closed at thirty and fifty percent because the census publishes them that way, and "
        "a household at 29.9 percent is counted as unburdened by a line it did not choose."
    )
    return r


# Recovery on the simulator


def simulate_estimate(world: World, policy: Policy = POLICY) -> list[Grade]:
    panel = from_world(world, policy)
    series = national_series(panel)
    cps = changepoints(series)
    nearest = float(min(cps, key=lambda c: abs(c - world.truth.burden_step_year))) if cps else float("nan")
    hit = float(any(abs(c - world.truth.burden_step_year) <= 1 for c in cps))
    rows = _metro_rows(panel)
    latest = integer(rows["year"].max())
    latest_rows = rows.filter(pl.col("year") == latest)
    severe = aggregate_interval(latest_rows, "renters_severe", policy, f"ch3-severe-{latest}", 200)
    truth_rows = world.metro_year.filter((pl.col("year") == latest) & (pl.col("kind") == "metropolitan"))
    truth_severe = num((truth_rows["rent_severe_share"] * truth_rows["renter_households"]).sum()) / num(
        truth_rows["renter_households"].sum()
    )
    return [
        Grade(
            "burden_changepoint",
            nearest,
            float(world.truth.burden_step_year),
            flag=hit,
            detail=f"changepoints {cps}",
        ),
        Grade("severe_share", severe.estimate, truth_severe, severe.low, severe.high),
    ]
