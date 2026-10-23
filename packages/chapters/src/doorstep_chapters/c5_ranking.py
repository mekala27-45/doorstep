"""Chapter 5, the fair ranking: the least affordable metros are not the most expensive ones.

Raw: the anchored median value. Adjusted: the payment on the median home as a share of the local median
household income, and the share of local households whose income clears the payment at the thirty
percent line (interpolated inside the census income brackets with a Pareto top bracket). Every rank
carries an interval from Monte Carlo draws over the census margins of error with the index held fixed.
The simulator confounds the raw ranking by design (the expensive metros are given the high incomes) and
knows the true payment share ranking, so the recovery study reports the rank correlation of the adjusted
ranking with the truth beside the raw ranking's. Micropolitan areas are carried in the warehouse and
excluded here: the census one year release covers only the largest of them, so a micropolitan ranking
would rank the ones the survey happens to reach.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl
from doorstep_core.config import INCOME_BRACKETS, POLICY, Policy
from doorstep_core.formats import format_value
from doorstep_finance.brackets import exact_share_above_lognormal, share_above
from doorstep_finance.mortgage import income_needed, payment_on_price
from doorstep_sim.metros import World
from doorstep_stats.monte_carlo import draw_inputs, rank_rows

from doorstep_chapters.common import Branch, ChapterResult, Figure, Grade, ensure
from doorstep_chapters.panel import Panel, from_world

NUMBER = 5
SLUG = "ranking"
TITLE = "The fair ranking"

SQL = """
select cbsa_code, cbsa_title, households, value_anchored, median_income, payment_share,
       rank() over (order by value_anchored desc) as raw_rank,
       rank() over (order by payment_share desc) as adjusted_rank
from mart_metro_year
where kind = 'metropolitan' and year = (select max(year) from mart_metro_year where median_income is not null)
  and value_anchored is not null and median_income is not null
order by adjusted_rank
""".strip()


def plan(policy: Policy = POLICY) -> dict[str, Any]:
    return {
        "chapter": NUMBER,
        "slug": SLUG,
        "claim": "Ranking metros by the payment share of local income, not by price, changes the order, and the "
        "largest moves are named.",
        "estimator": "payment share at the local median income and the affordable share from the income brackets with a "
        "Pareto top bracket, in the latest census year; ranks over every metropolitan area present in both the index "
        "and the survey; the twenty largest metros drawn as a slope chart",
        "interval": f"percentile rank interval over {policy.monte_carlo_draws} Monte Carlo draws of income and anchor value, index held fixed",
        "split": {"note": "descriptive ranking in the latest release; no fitted parameter"},
        "family": "one ranking; the movers are those whose adjusted rank interval excludes their raw rank; no correction",
        "operating_points": {
            "affordable_line": policy.affordable_line,
            "largest_metros": policy.largest_metros,
            "pareto_shape": "fitted from the mean where known, else 2.5",
            "micropolitan": "excluded",
        },
        "message_rule": "changes: at least one of the largest metros moves beyond its interval; unchanged: none does",
    }


def message_rule(
    movers: int,
    largest: int,
    up: list[tuple[str, int, int]],
    down: list[tuple[str, int, int]],
    spearman: float,
) -> Branch:
    if movers == 0:
        return Branch(
            "unchanged",
            f"Holding income constant does not change the order of the {largest} largest metros beyond their intervals "
            f"(rank correlation {format_value(spearman, 'float2')} between the raw and adjusted rankings).",
        )
    named_up = "; ".join(f"{name} from {a} to {b}" for name, a, b in up[:3])
    named_down = "; ".join(f"{name} from {a} to {b}" for name, a, b in down[:3])
    return Branch(
        "changes",
        f"The ranking changes when you hold constant what people earn there: {movers} of the {largest} largest metros "
        f"move beyond their intervals. Less affordable than their price says: {named_up}. More affordable: {named_down}.",
    )


def _latest_rows(panel: Panel, policy: Policy) -> pl.DataFrame:
    year = panel.latest_acs_year
    rows = panel.metropolitan().filter(
        (pl.col("year") == year)
        & pl.col("value_anchored").is_not_null()
        & pl.col("median_income").is_not_null()
        & (pl.col("median_income") > 0)
        & pl.col("households").is_not_null()
        & pl.col("value_anchored_moe").is_not_null()
        & pl.col("median_income_moe").is_not_null()
    )
    ensure(rows.height >= 3, "chapter 5 needs at least three metros in the latest census year")
    return rows.sort("cbsa_code")


def bracket_counts(panel: Panel, year: int) -> dict[str, list[float]]:
    """Household counts by bracket per metro, suppressed cells taken as empty (counted by the quarantine)."""
    b = panel.brackets.filter(pl.col("year") == year).sort(["cbsa_code", "bracket"])
    out: dict[str, list[float]] = {}
    for code, sub in b.group_by("cbsa_code", maintain_order=True):
        counts = [0.0] * (len(INCOME_BRACKETS) + 1)
        for k, h in zip(sub["bracket"].to_list(), sub["households"].to_list(), strict=True):
            if 0 <= int(k) < len(counts) and h is not None:
                counts[int(k)] = float(h)
        if sum(counts) > 0:
            out[str(code[0])] = counts
    return out


def affordable_shares(
    rows: pl.DataFrame, counts: dict[str, list[float]], rate: float, policy: Policy, line: float | None = None
) -> list[float | None]:
    out: list[float | None] = []
    for code, value in zip(rows["cbsa_code"].to_list(), rows["value_anchored"].to_list(), strict=True):
        c = counts.get(str(code))
        if c is None or value is None:
            out.append(None)
            continue
        needed = income_needed(
            float(value),
            rate,
            policy.down_payment_share,
            policy.loan_term_years,
            line or policy.affordable_line,
        )
        out.append(share_above(needed, c))
    return out


def rank(values: np.ndarray, *, descending: bool = True) -> np.ndarray:
    order = np.argsort(-values if descending else values, kind="stable")
    ranks = np.empty(values.shape[0])
    ranks[order] = np.arange(1, values.shape[0] + 1)
    return ranks


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra, rb = rank(a), rank(b)
    return float(np.corrcoef(ra, rb)[0, 1])


def rankings(panel: Panel, policy: Policy = POLICY, *, draws: int | None = None) -> tuple[pl.DataFrame, int]:
    """The ranking table with intervals and the number of draws used."""
    rows = _latest_rows(panel, policy)
    year = int(rows["year"][0])
    rate = float(rows["rate"][0])
    n_draws = draws or policy.monte_carlo_draws
    value = rows["value_anchored"].to_numpy().astype(np.float64)
    income = rows["median_income"].to_numpy().astype(np.float64)
    factor = 12.0 * payment_on_price(1.0, rate, policy.down_payment_share, policy.loan_term_years)
    share = value * factor / income
    counts = bracket_counts(panel, year)
    affordable = affordable_shares(rows, counts, rate, policy)
    d = draw_inputs(
        {"value": value, "income": income},
        {"value": rows["value_anchored_moe"].to_numpy(), "income": rows["median_income_moe"].to_numpy()},
        draws=n_draws,
        seed=policy.seed,
        label=f"ch5-{year}",
        floor=1000.0,
    )
    share_draws = d.values["value"] * factor / d.values["income"]
    adjusted_ranks = rank_rows(share_draws)
    raw_ranks = rank_rows(d.values["value"])
    raw_rank = rank(value)
    adjusted_rank = rank(share)
    aff = np.array([np.nan if a is None else a for a in affordable], dtype=np.float64)
    affordable_rank = rank(
        np.where(np.isnan(aff), -np.inf, -aff)
    )  # least affordable first: the lowest share is rank 1
    out = (
        rows.select(
            "cbsa_code", "cbsa_title", "households", "owner_households", "value_anchored", "median_income"
        )
        .with_columns(
            pl.lit(year).alias("year"),
            pl.lit(rate).alias("rate"),
            pl.Series("payment_share", share),
            pl.Series("payment_share_low", np.quantile(share_draws, 0.025, axis=0)),
            pl.Series("payment_share_high", np.quantile(share_draws, 0.975, axis=0)),
            pl.Series("affordable_share", aff),
            pl.Series("raw_rank", raw_rank.astype(np.int64)),
            pl.Series("raw_rank_low", np.quantile(raw_ranks, 0.025, axis=0).astype(np.int64)),
            pl.Series("raw_rank_high", np.quantile(raw_ranks, 0.975, axis=0).astype(np.int64)),
            pl.Series("adjusted_rank", adjusted_rank.astype(np.int64)),
            pl.Series("adjusted_rank_low", np.quantile(adjusted_ranks, 0.025, axis=0).astype(np.int64)),
            pl.Series("adjusted_rank_high", np.quantile(adjusted_ranks, 0.975, axis=0).astype(np.int64)),
            pl.Series("affordable_rank", affordable_rank.astype(np.int64)),
        )
        .with_columns(
            (pl.col("raw_rank") - pl.col("adjusted_rank")).alias("rank_change"),
            (
                (pl.col("raw_rank") < pl.col("adjusted_rank_low"))
                | (pl.col("raw_rank") > pl.col("adjusted_rank_high"))
            ).alias("moves"),
        )
    )
    return out.sort("adjusted_rank"), n_draws


def estimate(panel: Panel, policy: Policy = POLICY, *, draws: int | None = None) -> ChapterResult:
    table, n_draws = rankings(panel, policy, draws=draws)
    year = int(table["year"][0])
    largest = table.sort("households", descending=True).head(policy.largest_metros)
    movers = largest.filter(pl.col("moves"))
    up = [
        (str(r["cbsa_title"]).split(",")[0], int(r["raw_rank"]), int(r["adjusted_rank"]))
        for r in movers.filter(pl.col("rank_change") > 0)
        .sort("rank_change", descending=True)
        .iter_rows(named=True)
    ]
    down = [
        (str(r["cbsa_title"]).split(",")[0], int(r["raw_rank"]), int(r["adjusted_rank"]))
        for r in movers.filter(pl.col("rank_change") < 0).sort("rank_change").iter_rows(named=True)
    ]
    rho = spearman(table["value_anchored"].to_numpy(), table["payment_share"].to_numpy())
    branch = message_rule(int(movers.height), int(largest.height), up, down, rho)
    r = ChapterResult(
        number=NUMBER,
        slug=SLUG,
        source=panel.source,
        population=f"every metropolitan area present in both the index and the census release of {year} ({table.height} metros); micropolitan areas excluded",
        branch=branch.name,
        message=branch.text,
        reported_years=[year],
    )
    r.put("ch5.year", year, "year")
    r.put("ch5.metros_ranked", int(table.height), "int")
    r.put(
        "ch5.micropolitan_excluded",
        int(
            panel.metro_year.filter(
                (pl.col("kind") == "micropolitan")
                & (pl.col("year") == year)
                & pl.col("median_income").is_not_null()
            ).height
        ),
        "int",
    )
    r.put("ch5.draws", n_draws, "int", model="monte_carlo")
    r.put("ch5.largest", int(largest.height), "int")
    r.put("ch5.movers", int(movers.height), "int", model="monte_carlo")
    r.put("ch5.spearman", rho, "float2", model="monte_carlo")
    r.put("ch5.mean_abs_rank_change", float(table["rank_change"].abs().mean()), "float1", model="monte_carlo")
    r.put("ch5.max_rank_change", int(table["rank_change"].abs().max()), "int", model="monte_carlo")
    biggest = table.sort(pl.col("rank_change").abs(), descending=True).row(0, named=True)
    r.put("ch5.biggest_mover", str(biggest["cbsa_title"]), "text")
    r.put("ch5.biggest_mover.raw_rank", int(biggest["raw_rank"]), "int")
    r.put("ch5.biggest_mover.adjusted_rank", int(biggest["adjusted_rank"]), "int")
    r.put("ch5.biggest_mover.payment_share", float(biggest["payment_share"]), "pct1", model="monte_carlo")
    for label, sub in (("raw", table.sort("raw_rank")), ("adjusted", table.sort("adjusted_rank"))):
        top = sub.head(3)
        bottom = sub.tail(3)
        r.put(
            f"ch5.{label}.top3", "; ".join(str(x).split(",")[0] for x in top["cbsa_title"].to_list()), "text"
        )
        r.put(
            f"ch5.{label}.bottom3",
            "; ".join(str(x).split(",")[0] for x in bottom["cbsa_title"].to_list()),
            "text",
        )
    least = table.row(0, named=True)
    most = table.row(table.height - 1, named=True)
    r.put("ch5.least_affordable", str(least["cbsa_title"]), "text")
    r.put("ch5.least_affordable.payment_share", float(least["payment_share"]), "pct1", model="monte_carlo")
    r.put("ch5.least_affordable.low", float(least["payment_share_low"]), "pct1", model="monte_carlo")
    r.put("ch5.least_affordable.high", float(least["payment_share_high"]), "pct1", model="monte_carlo")
    r.put("ch5.most_affordable", str(most["cbsa_title"]), "text")
    r.put("ch5.most_affordable.payment_share", float(most["payment_share"]), "pct1", model="monte_carlo")
    with_aff = table.filter(pl.col("affordable_share").is_not_null())
    r.put("ch5.affordable_share.metros", int(with_aff.height), "int", model="bracket")
    r.put(
        "ch5.affordable_share.median",
        float(with_aff["affordable_share"].median()) if with_aff.height else None,
        "pct0",
        model="bracket",
    )
    r.put(
        "ch5.affordable_share.min",
        float(with_aff["affordable_share"].min()) if with_aff.height else None,
        "pct0",
        model="bracket",
    )
    r.put(
        "ch5.affordable_share.max",
        float(with_aff["affordable_share"].max()) if with_aff.height else None,
        "pct0",
        model="bracket",
    )
    r.put("ch5.branch", branch.name, "text")
    r.put("ch5.message", branch.text, "text")
    r.put_table(
        "ch5.largest",
        [
            "Metro",
            "Households",
            "Median home",
            "Median income",
            "Payment share",
            "Low",
            "High",
            "Raw rank",
            "Adjusted rank",
            "Interval",
            "Moves",
        ],
        ["text", "int", "usd0", "usd0", "pct1", "pct1", "pct1", "int", "int", "text", "text"],
        [
            [
                str(x["cbsa_title"]),
                int(x["households"]),
                float(x["value_anchored"]),
                float(x["median_income"]),
                float(x["payment_share"]),
                float(x["payment_share_low"]),
                float(x["payment_share_high"]),
                int(x["raw_rank"]),
                int(x["adjusted_rank"]),
                f"{int(x['adjusted_rank_low'])} to {int(x['adjusted_rank_high'])}",
                "yes" if x["moves"] else "no",
            ]
            for x in largest.sort("adjusted_rank").iter_rows(named=True)
        ],
        model="monte_carlo",
    )
    r.marts["ch5_ranking"] = table
    r.figure = Figure(
        title=branch.text,
        subtitle=f"The {largest.height} largest metros ranked by the price of the median home and by the payment share of local income, {year}",
        sql=SQL,
        frames={"slope": largest.sort("adjusted_rank"), "all": table},
        model="monte_carlo",
        callout=f"{movers.height} of {largest.height} move beyond their rank interval; rank correlation {format_value(rho, 'float2')}",
    )
    r.method = {
        "estimator": "payment share at the local median income; affordable share by bracket interpolation",
        "split": "descriptive, latest census year",
        "interval": f"{n_draws} Monte Carlo draws over the income and anchor value margins, index held fixed",
        "family": "one ranking; movers judged by their rank interval",
    }
    r.pushback = (
        "The median income is not the buyer income: in a metro where buyers earn twice the median, the payment share of "
        "the median household overstates what the people who actually buy face, and chapter 6 measures that ratio from the "
        "loans. The index has no margin, so the interval understates what a thin market's index carries. Metros that lost "
        "their one year census coverage drop out of the ranking in that year rather than being carried."
    )
    return r


# Recovery on the simulator


def simulate_estimate(world: World, policy: Policy = POLICY, *, draws: int = 500) -> list[Grade]:
    panel = from_world(world, policy)
    table, _ = rankings(panel, policy, draws=draws)
    year = int(table["year"][0])
    truth = world.metro_year.filter((pl.col("year") == year) & (pl.col("kind") == "metropolitan")).select(
        "metro_id",
        "payment_share_true",
        "median_income_true",
        "median_value_true",
        "income_sigma",
        "households",
    )
    merged = table.join(truth, left_on="cbsa_code", right_on="metro_id", how="inner")
    rho_adjusted = spearman(merged["payment_share"].to_numpy(), merged["payment_share_true"].to_numpy())
    rho_raw = spearman(merged["value_anchored"].to_numpy(), merged["payment_share_true"].to_numpy())
    # The bracket interpolation against the exact share on the known log normal distributions
    rate = float(table["rate"][0])
    counts = bracket_counts(panel, year)
    errors: list[float] = []
    for x in merged.iter_rows(named=True):
        c = counts.get(str(x["cbsa_code"]))
        if c is None:
            continue
        needed = income_needed(
            float(x["median_value_true"]),
            rate,
            policy.down_payment_share,
            policy.loan_term_years,
            policy.affordable_line,
        )
        exact = exact_share_above_lognormal(
            needed, float(np.log(x["median_income_true"])), float(x["income_sigma"])
        )
        errors.append(abs(share_above(needed, c) - exact))
    return [
        Grade(
            "ranking_adjusted",
            rho_adjusted,
            1.0,
            flag=rho_raw,
            detail="rank correlation with the true payment share ranking; flag is the raw ranking's",
        ),
        Grade(
            "bracket_interpolation",
            float(np.mean(errors)) if errors else float("nan"),
            0.0,
            detail=f"mean absolute error of the affordable share over {len(errors)} metros",
        ),
    ]
