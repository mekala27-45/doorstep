"""Chapter 8, the reader decision: what a household can afford, how long the down payment takes, and
when buying beats renting.

For the household: the affordable price at the thirty percent line for the median household and for each
income decile by metro; the share of households that can afford the median home; the down payment years
at the renter median income; the rent or buy breakeven horizon at the latest rate under the stated cost
model, with the appreciation and rent growth paths drawn by block bootstrap from the metro's own history
and the interval the bootstrap gives. For the policy reader: the metros where the affordable price sits
below the median home for the median household, and where it does not. The thirty percent line, the ten
percent down payment and the saving rate get the interior test. On the simulator the breakeven is graded
as late arriving truth: the estimate made with history to a stated year against the breakeven the realised
path produced afterwards.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl
from doorstep_core.config import AFFORDABLE_LINES, DOWN_PAYMENT_SHARES, POLICY, SAVING_RATES, Policy
from doorstep_core.formats import format_value
from doorstep_core.scalars import num
from doorstep_core.seeds import rng
from doorstep_finance.brackets import decile_incomes, share_above
from doorstep_finance.breakeven import CostModel, breakeven, breakeven_year, breakeven_years_vectorised
from doorstep_finance.mortgage import affordable_price, down_payment_years, income_needed
from doorstep_sim.metros import World

from doorstep_chapters.common import Branch, ChapterResult, Figure, Grade, ensure
from doorstep_chapters.panel import Panel, from_world

NUMBER = 8
SLUG = "decision"
TITLE = "The reader decision"
BLOCK_YEARS = 3
MIN_HISTORY_YEARS = 6

SQL = """
select cbsa_code, cbsa_title, year, rate, value_anchored, median_income, renter_median_income, median_rent, payment_share
from mart_metro_year
where kind = 'metropolitan' and year = (select max(year) from mart_metro_year where median_income is not null)
  and value_anchored is not null and median_income is not null and median_rent is not null
order by payment_share desc
""".strip()


def plan(policy: Policy = POLICY) -> dict[str, Any]:
    return {
        "chapter": NUMBER,
        "slug": SLUG,
        "claim": "In most metros buying beats renting only after a stated number of years at the latest rate, and one "
        "point of rate moves that horizon by a stated amount.",
        "estimator": "affordable price as the inverse of the payment share at the line; decile incomes from the brackets with a "
        "Pareto top bracket; down payment years at the renter median income and the saving rate; breakeven under the cost "
        "model with appreciation and rent growth paths drawn by block bootstrap from the metro's own annual history",
        "interval": f"percentile interval of the breakeven year over {policy.bootstrap_replicates} bootstrap paths with blocks of {BLOCK_YEARS} years",
        "split": {
            "history": f"{policy.fit_first_year} to the latest year for the paths",
            "report_on": "the latest census year at the latest quarterly rate",
        },
        "family": "one headline (the owner weighted median breakeven); the rate sensitivity is a recomputation; no correction",
        "operating_points": {
            "affordable_line": policy.affordable_line,
            "line_neighbours": list(AFFORDABLE_LINES),
            "down_payment_share": policy.down_payment_share,
            "down_neighbours": list(DOWN_PAYMENT_SHARES),
            "saving_rate": policy.saving_rate,
            "saving_neighbours": list(SAVING_RATES),
            "horizon_years": policy.breakeven_horizon_years,
            "cost_model": policy.breakeven_cost_model,
            "block_years": BLOCK_YEARS,
        },
        "message_rule": "years: the national median breakeven lies inside the horizon; never: owning does not catch up inside the "
        "horizon in most metros; immediate: the median breakeven is two years or under",
    }


def message_rule(
    median_years: float,
    low: float,
    high: float,
    never_share: float,
    horizon: int,
    rate_move: float,
    biggest: list[tuple[str, float]],
) -> Branch:
    named = "; ".join(f"{name} {format_value(y, 'beyond0')}" for name, y in biggest[:3])
    tail = f" Longest to break even among the largest metros: {named}." if named else ""
    if never_share > 0.5:
        return Branch(
            "never",
            f"In most metros ({format_value(never_share, 'pct0')}) owning does not catch up with renting inside {horizon} years at the latest rate; "
            f"one point of rate moves the breakeven by {format_value(rate_move, 'sfloat1')} years where it exists."
            + tail,
        )
    if median_years <= 2.0:
        return Branch(
            "immediate",
            f"Buying beats renting almost at once: the median breakeven is {format_value(median_years, 'beyond1')} (interval {format_value(low, 'beyond1')} to "
            f"{format_value(high, 'beyond1')}), and one point of rate moves it by {format_value(rate_move, 'sfloat1')} years."
            + tail,
        )
    return Branch(
        "years",
        f"Buying beats renting only after {format_value(median_years, 'beyond1')} in the typical metro (interval {format_value(low, 'beyond1')} to "
        f"{format_value(high, 'beyond1')}), and one point of rate moves the breakeven by {format_value(rate_move, 'sfloat1')} years."
        + tail,
    )


def _latest_rows(panel: Panel) -> pl.DataFrame:
    year = panel.latest_acs_year
    rows = panel.metropolitan().filter(
        (pl.col("year") == year)
        & pl.col("value_anchored").is_not_null()
        & pl.col("median_income").is_not_null()
        & pl.col("median_rent").is_not_null()
        & (pl.col("median_income") > 0)
        & (pl.col("median_rent") > 0)
    )
    ensure(rows.height >= 3, "chapter 8 needs at least three metros in the latest census year")
    return rows.sort("cbsa_code")


def histories(panel: Panel, *, last_year: int | None = None) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Per metro: the annual appreciation series from the index and the annual rent growth series, over the years
    both exist, to ``last_year`` when given (the late arriving truth test uses this)."""
    my = panel.metropolitan().filter(pl.col("index_at").is_not_null())
    if last_year is not None:
        my = my.filter(pl.col("year") <= last_year)
    out: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for code, sub in my.sort("year").group_by("cbsa_code", maintain_order=True):
        idx = sub["index_at"].to_numpy().astype(np.float64)
        years = sub["year"].to_numpy()
        app = idx[1:] / idx[:-1] - 1.0
        app = app[np.diff(years) == 1]
        rent = sub.filter(pl.col("median_rent").is_not_null())
        rv = rent["median_rent"].to_numpy().astype(np.float64)
        ry = rent["year"].to_numpy()
        rg = (rv[1:] / rv[:-1] - 1.0) / np.diff(ry) if rv.size > 1 else np.array([])
        if app.size >= MIN_HISTORY_YEARS and rg.size >= 3:
            out[str(code[0])] = (app, rg)
    return out


def bootstrap_paths(
    history: np.ndarray, *, horizon: int, draws: int, seed: int, label: str, block: int = BLOCK_YEARS
) -> np.ndarray:
    """Block bootstrap paths of annual rates: blocks of consecutive years drawn with replacement from the history."""
    g = rng(seed, "breakeven", label)
    n = history.shape[0]
    blocks_needed = int(np.ceil(horizon / block))
    starts = g.integers(0, max(n - block + 1, 1), size=(draws, blocks_needed))
    offsets = np.arange(block)
    idx = (starts[:, :, None] + offsets[None, None, :]).reshape(draws, -1)[:, :horizon]
    idx = np.minimum(idx, n - 1)
    return np.asarray(history[idx], dtype=np.float64)


def breakeven_for_metro(
    price: float,
    annual_rent: float,
    rate: float,
    policy: Policy,
    hist: tuple[np.ndarray, np.ndarray],
    *,
    draws: int,
    seed: int,
    label: str,
    down: float | None = None,
) -> tuple[float, float, float, float]:
    """(median breakeven year, low, high, share of paths that never break even)."""
    app = bootstrap_paths(
        hist[0], horizon=policy.breakeven_horizon_years, draws=draws, seed=seed, label=label + "-app"
    )
    rg = bootstrap_paths(
        hist[1], horizon=policy.breakeven_horizon_years, draws=draws, seed=seed, label=label + "-rent"
    )
    years: np.ndarray = np.array(
        breakeven_years_vectorised(
            price,
            annual_rent,
            rate,
            policy.down_payment_share if down is None else down,
            policy.loan_term_years,
            app,
            rg,
            CostModel.from_mapping(policy.breakeven_cost_model),
        )
    )
    alpha = (1.0 - policy.interval_level) / 2.0
    return (
        float(np.median(years)),
        float(np.quantile(years, alpha)),
        float(np.quantile(years, 1.0 - alpha)),
        float(np.mean(years > policy.breakeven_horizon_years)),
    )


def metro_table(
    panel: Panel,
    policy: Policy = POLICY,
    *,
    draws: int | None = None,
    rate_offset: float = 0.0,
    down: float | None = None,
    line: float | None = None,
) -> pl.DataFrame:
    rows = _latest_rows(panel)
    year = int(rows["year"][0])
    rate = float(rows["rate"][0]) + rate_offset
    n_draws = draws or policy.bootstrap_replicates
    hist = histories(panel)
    counts = {
        str(k[0]): [0.0 if h is None else float(h) for h in v.sort("bracket")["households"].to_list()]
        for k, v in panel.brackets.filter(pl.col("year") == year).group_by("cbsa_code")
    }
    out: list[dict[str, Any]] = []
    the_line = line or policy.affordable_line
    the_down = policy.down_payment_share if down is None else down
    for r in rows.iter_rows(named=True):
        code = str(r["cbsa_code"])
        price = float(r["value_anchored"])
        income = float(r["median_income"])
        rent = float(r["median_rent"]) * 12.0
        renter_income = float(r["renter_median_income"]) if r["renter_median_income"] else income * 0.6
        aff_price = affordable_price(income, rate, the_down, policy.loan_term_years, the_line)
        needed = income_needed(price, rate, the_down, policy.loan_term_years, the_line)
        c = counts.get(code)
        aff_share = share_above(needed, c) if c is not None and sum(c) > 0 and len(c) == 16 else None
        deciles = decile_incomes(c) if c is not None and sum(c) > 0 and len(c) == 16 else None
        dp_years = down_payment_years(price, the_down, renter_income, policy.saving_rate)
        h = hist.get(code)
        if h is not None:
            med, low, high, never = breakeven_for_metro(
                price,
                rent,
                rate,
                policy,
                h,
                draws=n_draws,
                seed=policy.seed,
                label=f"{code}-{rate_offset}-{the_down}",
                down=the_down,
            )
        else:
            med, low, high, never = float("nan"), float("nan"), float("nan"), float("nan")
        row: dict[str, Any] = {
            "cbsa_code": code,
            "cbsa_title": r["cbsa_title"],
            "year": year,
            "rate": rate,
            "households": r["households"],
            "owner_households": r["owner_households"],
            "median_home": price,
            "median_income": income,
            "annual_rent": rent,
            "affordable_price": aff_price,
            "affordable_gap": aff_price - price,
            "median_can_afford": aff_price >= price,
            "income_needed": needed,
            "affordable_share": aff_share,
            "down_payment_years": dp_years,
            "breakeven_years": med,
            "breakeven_low": low,
            "breakeven_high": high,
            "never_share": never,
        }
        for d in range(1, 10):
            row[f"decile_{d}_income"] = deciles[d - 1] if deciles else None
            row[f"decile_{d}_price"] = (
                affordable_price(deciles[d - 1], rate, the_down, policy.loan_term_years, the_line)
                if deciles
                else None
            )
        out.append(row)
    return pl.DataFrame(out).sort("cbsa_code")


def _weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    ok = np.isfinite(values) & np.isfinite(weights)
    v, w = values[ok], weights[ok]
    order = np.argsort(v, kind="stable")
    v, w = v[order], w[order]
    cs = np.cumsum(w)
    i = int(np.searchsorted(cs, 0.5 * cs[-1], side="left"))
    return float(v[min(i, v.shape[0] - 1)])


def estimate(panel: Panel, policy: Policy = POLICY, *, draws: int | None = None) -> ChapterResult:
    table = metro_table(panel, policy, draws=draws)
    year = int(table["year"][0])
    rate = float(table["rate"][0])
    with_be = table.filter(pl.col("breakeven_years").is_not_nan())
    ensure(with_be.height > 0, "chapter 8 has no metro with enough history for the breakeven")
    w = with_be["owner_households"].fill_null(1.0).to_numpy().astype(np.float64)
    med = _weighted_median(with_be["breakeven_years"].to_numpy(), w)
    low = _weighted_median(with_be["breakeven_low"].to_numpy(), w)
    high = _weighted_median(with_be["breakeven_high"].to_numpy(), w)
    never_share = float(
        np.average(
            (with_be["breakeven_years"] > policy.breakeven_horizon_years).cast(pl.Float64).to_numpy(),
            weights=w,
        )
    )
    plus_one = metro_table(
        panel, policy, draws=min(draws or policy.bootstrap_replicates, 200), rate_offset=1.0
    ).filter(pl.col("breakeven_years").is_not_nan())
    joined = with_be.select("cbsa_code", "breakeven_years", "owner_households").join(
        plus_one.select("cbsa_code", pl.col("breakeven_years").alias("plus_one")), on="cbsa_code", how="inner"
    )
    both = joined.filter(
        (pl.col("breakeven_years") <= policy.breakeven_horizon_years)
        & (pl.col("plus_one") <= policy.breakeven_horizon_years)
    )
    rate_move = (
        float(
            np.average(
                (both["plus_one"] - both["breakeven_years"]).to_numpy(),
                weights=both["owner_households"].fill_null(1.0).to_numpy(),
            )
        )
        if both.height
        else float("nan")
    )
    largest = with_be.sort("households", descending=True).head(policy.largest_metros)
    biggest = [
        (str(x["cbsa_title"]).split(",")[0], float(x["breakeven_years"]))
        for x in largest.sort("breakeven_years", descending=True).iter_rows(named=True)
    ]
    branch = message_rule(med, low, high, never_share, policy.breakeven_horizon_years, rate_move, biggest)
    r = ChapterResult(
        number=NUMBER,
        slug=SLUG,
        source=panel.source,
        population=f"every metropolitan area with an anchored value, a census income and rent in {year} ({table.height} metros; {with_be.height} with enough history for the breakeven)",
        branch=branch.name,
        message=branch.text,
        reported_years=[year],
    )
    r.put("ch8.year", year, "year")
    r.put("ch8.rate", rate, "rate2")
    r.put("ch8.metros", int(table.height), "int")
    r.put("ch8.metros_with_breakeven", int(with_be.height), "int")
    r.put("ch8.draws", draws or policy.bootstrap_replicates, "int")
    r.put("ch8.breakeven.median", med, "beyond1", model="breakeven")
    r.put("ch8.breakeven.low", low, "beyond1", model="breakeven")
    r.put("ch8.breakeven.high", high, "beyond1", model="breakeven")
    r.put("ch8.breakeven.never_share", never_share, "pct0", model="breakeven")
    r.put("ch8.breakeven.rate_move", rate_move, "sfloat1", model="breakeven")
    r.put("ch8.horizon", policy.breakeven_horizon_years, "int")
    can = table.filter(pl.col("median_can_afford"))
    r.put("ch8.median_can_afford.metros", int(can.height), "int", model="payment")
    r.put("ch8.median_can_afford.share", can.height / table.height, "pct0", model="payment")
    r.put("ch8.affordable_gap.median", num(table["affordable_gap"].median()), "susd0", model="payment")
    with_share = table.filter(pl.col("affordable_share").is_not_null())
    r.put(
        "ch8.affordable_share.median",
        num(with_share["affordable_share"].median()) if with_share.height else None,
        "pct0",
        model="bracket",
    )
    r.put(
        "ch8.down_payment_years.median",
        num(table["down_payment_years"].median()),
        "years1",
        model="payment",
    )
    r.put("ch8.down_payment_years.max", num(table["down_payment_years"].max()), "years1", model="payment")
    worst = table.sort("down_payment_years", descending=True).row(0, named=True)
    r.put("ch8.down_payment_years.max_metro", str(worst["cbsa_title"]), "text")
    for i, (name, years) in enumerate(biggest[:3], start=1):
        r.put(f"ch8.longest.{i}.metro", name, "text")
        r.put(f"ch8.longest.{i}.years", years, "beyond0", model="breakeven")
    quickest = sorted(biggest, key=lambda kv: kv[1])[:3]
    for i, (name, years) in enumerate(quickest, start=1):
        r.put(f"ch8.quickest.{i}.metro", name, "text")
        r.put(f"ch8.quickest.{i}.years", years, "beyond0", model="breakeven")
    r.put("ch8.branch", branch.name, "text")
    r.put("ch8.message", branch.text, "text")

    # Interior tests
    line_rows: list[list[Any]] = []
    line_sign: dict[float, int] = {}
    for line in AFFORDABLE_LINES:
        t = metro_table(panel, policy, draws=10, line=line)
        n = int(t.filter(pl.col("median_can_afford")).height)
        line_sign[line] = n
        line_rows.append([line, n, n / t.height, "chosen" if line == policy.affordable_line else ""])
    down_rows: list[list[Any]] = []
    down_sign: dict[float, float] = {}
    for d in DOWN_PAYMENT_SHARES:
        t = metro_table(panel, policy, draws=min(draws or policy.bootstrap_replicates, 200), down=d).filter(
            pl.col("breakeven_years").is_not_nan()
        )
        m = _weighted_median(
            t["breakeven_years"].to_numpy(),
            t["owner_households"].fill_null(1.0).to_numpy().astype(np.float64),
        )
        down_sign[d] = m
        down_rows.append(
            [
                d,
                m,
                num(t["down_payment_years"].median()),
                "chosen" if d == policy.down_payment_share else "",
            ]
        )
    saving_rows: list[list[Any]] = []
    for s in SAVING_RATES:
        dp = (
            (table["median_home"] * policy.down_payment_share / (table["median_income"] * 0.6 * s)).median()
            if "renter_median_income" not in table.columns
            else None
        )
        renter_income = _latest_rows(panel)["renter_median_income"].fill_null(
            _latest_rows(panel)["median_income"] * 0.6
        )
        years_s = table["median_home"] * policy.down_payment_share / (renter_income * s)
        saving_rows.append([s, num(years_s.median()), "chosen" if s == policy.saving_rate else ""])
        del dp
    chosen = policy.affordable_line
    neighbour = min((x for x in AFFORDABLE_LINES if x != chosen), key=lambda x: abs(x - chosen))
    line_degenerate = (line_sign[neighbour] > len(table) / 2) != (line_sign[chosen] > len(table) / 2)
    if line_degenerate:
        for row in line_rows:
            if row[0] == neighbour:
                row[3] = "degenerate"
    d_neighbour = min(
        (x for x in DOWN_PAYMENT_SHARES if x != policy.down_payment_share),
        key=lambda x: abs(x - policy.down_payment_share),
    )
    down_degenerate = (down_sign[d_neighbour] > policy.breakeven_horizon_years) != (
        down_sign[policy.down_payment_share] > policy.breakeven_horizon_years
    )
    if down_degenerate:
        for row in down_rows:
            if row[0] == d_neighbour:
                row[3] = "degenerate"
    r.put_table(
        "ch8.line_interior",
        ["Line", "Metros where the median household can afford the median home", "Share", "Note"],
        ["pct0", "int", "pct0", "text"],
        line_rows,
        model="payment",
    )
    r.put_table(
        "ch8.down_interior",
        ["Down payment", "Median breakeven", "Median down payment years", "Note"],
        ["pct0", "beyond1", "years1", "text"],
        down_rows,
        model="breakeven",
    )
    r.put_table(
        "ch8.saving_interior",
        ["Saving rate", "Median down payment years", "Note"],
        ["pct0", "years1", "text"],
        saving_rows,
        model="payment",
    )
    r.put("ch8.line_degenerate", "degenerate" if line_degenerate else "stable", "text")
    r.put("ch8.down_degenerate", "degenerate" if down_degenerate else "stable", "text")

    r.put_table(
        "ch8.largest",
        [
            "Metro",
            "Median home",
            "Affordable price",
            "Can afford",
            "Affordable share",
            "Down payment years",
            "Breakeven",
            "Low",
            "High",
        ],
        ["text", "usd0", "usd0", "text", "pct0", "years1", "beyond1", "beyond1", "beyond1"],
        [
            [
                str(x["cbsa_title"]),
                float(x["median_home"]),
                float(x["affordable_price"]),
                "yes" if x["median_can_afford"] else "no",
                x["affordable_share"],
                float(x["down_payment_years"]),
                float(x["breakeven_years"]),
                float(x["breakeven_low"]),
                float(x["breakeven_high"]),
            ]
            for x in largest.sort("breakeven_years", descending=True).iter_rows(named=True)
        ],
        model="breakeven",
    )
    # The breakeven curve for the largest metro: cumulative difference by horizon under the median path
    top = largest.sort("households", descending=True).row(0, named=True)
    hist = histories(panel)[str(top["cbsa_code"])]
    curve = breakeven(
        float(top["median_home"]),
        float(top["annual_rent"]),
        rate,
        policy.down_payment_share,
        policy.loan_term_years,
        policy.breakeven_horizon_years,
        float(np.median(hist[0])),
        float(np.median(hist[1])),
        CostModel.from_mapping(policy.breakeven_cost_model),
    )
    curve_frame = pl.DataFrame(
        {
            "metro": [str(top["cbsa_title"])] * curve.horizon,
            "year": [y.year for y in curve.years],
            "difference": [y.difference for y in curve.years],
            "owner_equity": [y.owner_equity for y in curve.years],
            "renter_wealth": [y.renter_wealth for y in curve.years],
        }
    )
    r.put("ch8.curve.metro", str(top["cbsa_title"]), "text")
    r.put(
        "ch8.curve.breakeven",
        breakeven_year(curve, policy.breakeven_horizon_years),
        "beyond0",
        model="breakeven",
    )
    r.marts["ch8_metros"] = table
    r.marts["ch8_curve"] = curve_frame
    r.figure = Figure(
        title=branch.text,
        subtitle=f"Renter wealth less owner equity by horizon for the largest metro at {format_value(rate, 'rate2')}, with the breakeven marked and its interval across metros",
        sql=SQL,
        frames={
            "curve": curve_frame,
            "metros": table.select(
                "cbsa_code",
                "cbsa_title",
                "households",
                "median_home",
                "affordable_price",
                "affordable_share",
                "down_payment_years",
                "breakeven_years",
                "breakeven_low",
                "breakeven_high",
            ),
        },
        model="breakeven",
        callout=f"median breakeven {format_value(med, 'beyond1')}; the median household can afford the median home in {can.height} of {table.height} metros",
    )
    r.method = {
        "estimator": "closed form payment arithmetic; bracket interpolation; breakeven under the cost model on bootstrap paths",
        "split": f"paths from each metro's own history; reported in {year} at the latest quarterly rate",
        "interval": f"block bootstrap, blocks of {BLOCK_YEARS} years, {draws or policy.bootstrap_replicates} paths per metro",
        "family": "one headline",
    }
    r.pushback = (
        "A payment is not the whole cost of owning: the cost model adds taxes, insurance, maintenance and the costs of "
        "buying and selling, but not the roof that fails in year four, and it credits the renter with a return the renter "
        "has to earn. The paths are drawn from the metro's own past, which includes a decade nobody expects to repeat, and "
        "the interval is the spread of those paths, not a forecast. The down payment years assume a renter who saves a tenth "
        "of income with no help and no return, which is the simplest honest reading of the question."
        + (
            f" The {format_value(chosen, 'pct0')} line is doing work: at {format_value(neighbour, 'pct0')}, the sensitivity line, the "
            f"median household can afford the median home in {line_sign[neighbour]} of the {len(table)} metros rather than "
            f"{line_sign[chosen]}, and the majority reading goes with the line."
            if line_degenerate
            else ""
        )
    )
    return r


# Recovery on the simulator


def simulate_estimate(
    world: World, policy: Policy = POLICY, *, draws: int = 200, as_of_year: int = 2014
) -> list[Grade]:
    """Late arriving truth: the breakeven estimated with history to ``as_of_year`` against the breakeven the realised
    path after it produced, over the years the world has left."""
    panel = from_world(world, policy)
    hist = histories(panel, last_year=as_of_year)
    my = panel.metropolitan().filter(pl.col("year") == as_of_year)
    horizon = world.last_year - as_of_year
    cost = CostModel.from_mapping(policy.breakeven_cost_model)
    errors: list[float] = []
    covered: list[float] = []
    for r in my.iter_rows(named=True):
        code = str(r["cbsa_code"])
        if code not in hist or r["value_anchored"] is None or r["median_rent"] is None:
            continue
        price, rent, rate = float(r["value_anchored"]), float(r["median_rent"]) * 12.0, float(r["rate"])
        app = bootstrap_paths(
            hist[code][0], horizon=horizon, draws=draws, seed=world.seed, label=f"{code}-app"
        )
        rg = bootstrap_paths(
            hist[code][1], horizon=horizon, draws=draws, seed=world.seed, label=f"{code}-rent"
        )
        years: np.ndarray = np.array(
            breakeven_years_vectorised(
                price, rent, rate, policy.down_payment_share, policy.loan_term_years, app, rg, cost
            )
        )
        est, lo, hi = (
            float(np.median(years)),
            float(np.quantile(years, 0.025)),
            float(np.quantile(years, 0.975)),
        )
        future = (
            panel.metropolitan()
            .filter((pl.col("cbsa_code") == code) & (pl.col("year") > as_of_year))
            .sort("year")
        )
        idx = (
            panel.metropolitan()
            .filter((pl.col("cbsa_code") == code) & (pl.col("year") >= as_of_year))
            .sort("year")["index_at"]
            .to_numpy()
        )
        true_app = list(idx[1:] / idx[:-1] - 1.0)
        rents = (
            panel.metropolitan()
            .filter((pl.col("cbsa_code") == code) & (pl.col("year") >= as_of_year))
            .sort("year")["median_rent"]
            .to_numpy()
        )
        true_rg = list(rents[1:] / rents[:-1] - 1.0)
        if len(true_app) < horizon or len(true_rg) < horizon - 1:
            continue
        truth = breakeven_year(
            breakeven(
                price,
                rent,
                rate,
                policy.down_payment_share,
                policy.loan_term_years,
                horizon,
                true_app,
                [*true_rg, true_rg[-1]],
                cost,
            ),
            horizon,
        )
        errors.append(est - truth)
        covered.append(float(lo <= truth <= hi))
        del future
    return [
        Grade(
            "breakeven_horizon",
            float(np.mean(np.abs(errors))) if errors else float("nan"),
            0.0,
            flag=float(np.mean(covered)) if covered else None,
            detail=f"mean absolute error in years over {len(errors)} metros; flag is the interval coverage",
        ),
    ]
