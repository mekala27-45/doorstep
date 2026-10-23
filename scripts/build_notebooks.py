"""Write the three notebooks from source cells, so they are reviewable as code, and execute them
against the committed results. Each keeps a dead end: the alternative that was tried, run again
here, and the reason it was not used. nbmake runs them again in CI.

    uv run python scripts/build_notebooks.py            # write and execute
    uv run python scripts/build_notebooks.py --no-execute
    uv run pytest --nbmake notebooks
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks"

PRELUDE = """import json
import os
from pathlib import Path

import duckdb
import numpy as np
import polars as pl

pl.Config.set_tbl_rows(30)
pl.Config.set_tbl_hide_dataframe_shape(True)
pl.Config.set_fmt_str_lengths(90)
pl.Config.set_tbl_width_chars(160)
pl.Config.set_float_precision(3)
ROOT = Path(os.environ.get("DOORSTEP_NOTEBOOK_ROOT") or (Path.cwd() if (Path.cwd() / "results").exists() else Path.cwd().parent))
manifest = json.loads((ROOT / "results" / "manifest.json").read_text(encoding="utf-8"))
values, tables = manifest["values"], manifest["tables"]


def v(key):
    return values[key]["value"]


def t(key):
    # A manifest value formatted the way the documents print it.
    from doorstep_core.formats import format_value

    return format_value(values[key]["value"], values[key]["fmt"])


def table(key):
    entry = tables[key]
    return pl.DataFrame(entry["rows"], schema=entry["columns"], orient="row")


MARTS = ROOT / "results" / "marts"
print("manifest as of", manifest["as_of"], "with", len(values), "values; prices to", v("data.fhfa.latest_period"), "and the census to", v("data.acs.last_year"))"""


def nb1() -> list[tuple[str, str]]:
    return [
        (
            "markdown",
            """# 01. The anchor

The regulator publishes how prices moved; the census publishes what owners say their homes are worth.
Every dollar in the story is the census median value in one anchor year moved by the index. This
notebook shows why the anchor year is a decision and keeps the dead end: the first version anchored
every metro in the latest release, which made the self report bias of one survey year the level of
every year before it, and moved every headline when the anchor was moved.

First on the simulator, where the true value and the planted self report bias are known; then the real
metros from the committed marts and the manifest.""",
        ),
        ("code", PRELUDE),
        (
            "markdown",
            """## On the simulator

Each simulated metro reports its value with a known factor over the true one. Anchoring in any one
year carries that factor into every year, so the anchored series is the true series times the metro's
bias; the census value over the transaction values in the loan extract bounds the factor without
removing it.""",
        ),
        (
            "code",
            """from doorstep_sim.metros import DEMONSTRATION, generate

world = generate(DEMONSTRATION, 7)
my = world.metro_year
truth = world.truth.metros.select("metro_id", "value_bias")
reported = (
    my.filter(pl.col("year").is_in([2015, 2019, 2023]))
    .select("metro_id", "year", "median_value_reported", "median_value_true")
    .with_columns((pl.col("median_value_reported") / pl.col("median_value_true")).alias("reported_over_true"))
    .join(truth, on="metro_id")
)
reported.group_by("year").agg(
    pl.col("reported_over_true").mean().alias("mean reported over true"),
    (pl.col("reported_over_true") - pl.col("value_bias")).abs().mean().alias("mean gap to the planted factor"),
).sort("year")""",
        ),
        (
            "markdown",
            """The gap to the planted factor is the survey's own sampling noise; the factor itself is what the
anchor inherits. The chapter's self report correction estimates it from the loan extract and the
recovery study grades it.""",
        ),
        (
            "markdown",
            """## The dead end: anchoring in the latest year

The first version anchored in the latest release. Every headline then rested on one survey year that
had not finished revising, and when the anchor was moved to 2019 the national payment share moved
with it. The sensitivity table in the manifest prints the headline under every anchor; the policy
anchor is 2019, the last full response year before the pandemic.""",
        ),
        ("code", """table("ch1.anchor_sensitivity")"""),
        (
            "markdown",
            """## The real metros

The national series from the chapter, and the same series re-anchored in each year of the table above,
computed here from the marts so the arithmetic is visible: value in the anchor year times the index
ratio, the payment at the quarterly rate on ninety percent of it, twelve payments over the median
income, weighted by owner households.""",
        ),
        (
            "code",
            """from doorstep_finance.mortgage import payment_share

metro_year = pl.read_parquet(MARTS / "mart_metro_year.parquet").filter(pl.col("kind") == "metropolitan")


def national_payment_share(frame, anchor_year):
    # the mart carries the policy anchor as anchor_value already, so this notebook's anchor gets its own names
    base = frame.filter((pl.col("year") == anchor_year) & pl.col("median_value_reported").is_not_null() & pl.col("index_at").is_not_null()).select(
        "cbsa_code", pl.col("median_value_reported").alias("nb_anchor_value"), pl.col("index_at").alias("nb_anchor_index")
    )
    rows = (
        frame.join(base, on="cbsa_code")
        .filter(pl.col("index_at").is_not_null() & (pl.col("median_income") > 0) & pl.col("rate").is_not_null() & pl.col("owner_households").is_not_null())
        .with_columns((pl.col("nb_anchor_value") * pl.col("index_at") / pl.col("nb_anchor_index")).alias("value"))
    )
    out = []
    for year, group in sorted(rows.group_by("year"), key=lambda kv: kv[0][0]):
        w = group["owner_households"].to_numpy()
        shares = np.array([payment_share(v, i, r, 0.10, 30) for v, i, r in zip(group["value"], group["median_income"], group["rate"])])
        out.append({"year": year[0], "anchor": anchor_year, "payment_share": float(np.average(shares, weights=w)), "metros": group.height})
    return pl.DataFrame(out)


series = pl.concat([national_payment_share(metro_year, a) for a in (2015, 2017, 2019, 2023)])
series.pivot(on="anchor", index="year", values="payment_share").sort("year")""",
        ),
        (
            "code",
            """latest = series.filter(pl.col("year") == series["year"].max())
peak = series.filter(pl.col("year") == 2006)
latest.join(peak, on="anchor", suffix="_2006").select(
    "anchor", pl.col("payment_share").alias("latest"), pl.col("payment_share_2006").alias("in 2006"), (pl.col("payment_share") - pl.col("payment_share_2006")).alias("difference")
)""",
        ),
        (
            "markdown",
            """The difference against 2006 is the headline of chapter 1. It is read on the anchor the policy fixed
before the data; the table shows what each other anchor would have said, and the chapter prints the
word stable or degenerate depending on whether the sign survives the first neighbour.""",
        ),
    ]


def nb2() -> list[tuple[str, str]]:
    return [
        (
            "markdown",
            """# 02. The lock in

Owners who hold a mortgage far below the market rate do not sell. The chapter measures that from the
loans themselves: originations in 2019 to 2021 under four percent, per hundred owner households, metro
by metro, and then asks what happened to turnover after the rate shock. This notebook keeps the dead
end: the first version of the measure counted every origination, so a metro whose owners refinanced
twice at the bottom counted each refinance, and the intensity measured how often a metro refinanced
rather than how much of it held a low rate.

First on the simulator, where the lock in response is planted; then the real metros.""",
        ),
        ("code", PRELUDE),
        (
            "markdown",
            """## On the simulator

The simulator plants a turnover response of 0.04 purchases per hundred owners lost per point of lock in
after the shock. The regression with metro and year fixed effects recovers it from the all origination
measure; the purchase only measure (the dead end's alternative) carries the same information with less
of it.""",
        ),
        (
            "code",
            """from doorstep_chapters import c2_rate_shock
from doorstep_chapters.panel import from_world
from doorstep_sim.metros import DEMONSTRATION, LOCK_IN_RESPONSE, generate

rows = []
for seed in range(4):
    world = generate(DEMONSTRATION, seed)
    panel = from_world(world, with_loans=True)
    for column, label in (("low_rate_originations", "all originations under 4%"), ("under_3_5_originations", "originations under 3.5%")):
        head, placebo, metros, clusters = c2_rate_shock.lock_in_regression(panel, column=column)
        rows.append({"seed": seed, "measure": label, "estimate": head.estimate, "low": head.low, "high": head.high, "placebo": placebo.estimate})
pl.DataFrame(rows).group_by("measure").agg(
    pl.col("estimate").mean().alias("mean estimate"), pl.col("placebo").mean().alias("mean placebo"), pl.lit(-LOCK_IN_RESPONSE).alias("truth")
)""",
        ),
        (
            "markdown",
            """## The dead end on the real loans

Every origination under four percent, purchase and refinance alike, against purchase originations
alone, per hundred owner households in 2021. The two intensities rank the metros almost the same
way; what the all origination measure adds is the refinancing wave, which is where the lock in lives,
so the chapter keeps it and says in its pushback that it is an intensity rather than a count of
owners.""",
        ),
        (
            "code",
            """metro_year = pl.read_parquet(MARTS / "mart_metro_year.parquet").filter(pl.col("kind") == "metropolitan")
lock = (
    metro_year.filter(pl.col("year").is_between(2019, 2021))
    .group_by("cbsa_code", "cbsa_title")
    .agg(pl.col("low_rate_originations").sum().alias("all_under_4"), pl.col("purchase_loans").sum().alias("purchases"))
    .join(metro_year.filter(pl.col("year") == 2021).select("cbsa_code", "owner_households"), on="cbsa_code")
    .filter(pl.col("owner_households") > 0)
    .with_columns(
        (100.0 * pl.col("all_under_4") / pl.col("owner_households")).alias("lock_in_all"),
        (100.0 * pl.col("purchases") / pl.col("owner_households")).alias("purchases_per_100"),
    )
)
print("metros", lock.height, "rank correlation", round(float(np.corrcoef(lock["lock_in_all"].rank(), lock["purchases_per_100"].rank())[0, 1]), 3))
lock.sort("lock_in_all", descending=True).select("cbsa_title", "lock_in_all", "purchases_per_100").head(10)""",
        ),
        (
            "markdown",
            """## The regression on the real metros

The headline and the placebo from the manifest, with the threshold interior test beside them.""",
        ),
        (
            "code",
            """print("lock in per point:", t("ch2.lock_in.coef"), "interval", t("ch2.lock_in.low"), "to", t("ch2.lock_in.high"), "p", t("ch2.lock_in.p"))
print("placebo on the base years:", t("ch2.placebo.coef"), "interval", t("ch2.placebo.low"), "to", t("ch2.placebo.high"))
print("turnover before", t("ch2.turnover.before"), "after", t("ch2.turnover.after"), "per 100 owner households")
table("ch2.threshold_interior")""",
        ),
    ]


def nb3() -> list[tuple[str, str]]:
    return [
        (
            "markdown",
            """# 03. Supply and demand

Where builders kept pace, prices rose less. The regression that says so has one objection built
into it: builders build where people are arriving, and a regression that cannot see the arrivals
credits the building with what the demand did. This notebook keeps the dead end: the specification
that put the demand shock in the wrong fixed effect. It averaged each metro's migration over the
whole window set and entered that as the control, which the metro fixed effect absorbs entirely, so
the controlled and the uncontrolled estimates came out identical and the control did nothing.

First on the simulator, where the elasticity is planted; then the real cells.""",
        ),
        ("code", PRELUDE),
        (
            "markdown",
            """## On the simulator

Three specifications on the same cells: no demand control, the dead end (a metro level mean of
migration, absorbed by the metro effect), and the kept one (migration over the window and the two
years before it, which varies within the metro).""",
        ),
        (
            "code",
            """from doorstep_chapters import c4_supply
from doorstep_chapters.panel import from_world
from doorstep_sim.metros import BETA_SUPPLY, Condition, generate
from doorstep_stats.regression import first, regress

strong = Condition(name="strong", demand_strength="strong", supply_dispersion="narrow", reverse_causality="none", noise="low")
rows = []
for seed in range(4):
    world = generate(strong, seed)
    cells = c4_supply.cells(from_world(world), 5)
    y = cells["annual_growth"].to_numpy()
    w = cells["population"].to_numpy()
    fe = [cells["cbsa_code"].to_numpy(), cells["window_id"].to_numpy()]
    cl = cells["state"].to_numpy()
    metro_mean = cells.join(cells.group_by("cbsa_code").agg(pl.col("migration_rate").mean().alias("metro_mean")), on="cbsa_code")["metro_mean"].to_numpy()
    none = first(regress(y, cells["permits_rate"].to_numpy()[:, None], ["permits_rate"], weights=w, fixed_effects=fe, cluster=cl), "permits_rate")
    try:
        dead_end = first(regress(y, np.column_stack([cells["permits_rate"].to_numpy(), metro_mean]), ["permits_rate", "metro_mean"], weights=w, fixed_effects=fe, cluster=cl), "permits_rate")
        dead_end_estimate = dead_end.estimate
    except Exception as err:  # the solver refuses a control the fixed effects absorb
        dead_end_estimate = float("nan")
        if seed == 0:
            print("dead end:", err)
    kept, _ = c4_supply.fit_both(cells)
    rows.append({"seed": seed, "no control": none.estimate, "dead end": dead_end_estimate, "kept": kept.estimate})
frame = pl.DataFrame(rows)
print("planted elasticity", -BETA_SUPPLY)
frame.select(pl.all().exclude("seed").mean())""",
        ),
        (
            "markdown",
            """The dead end does not even run: a control that does not vary within the metro is collinear with the
metro effect, and the solver refuses it rather than returning the uncontrolled estimate under a
different name, which is what the first version of this chapter had silently done. The kept
specification moves toward the planted value under strong demand; the recovery study on the data
page reports the remaining attenuation by condition.""",
        ),
        (
            "markdown",
            """## The real cells

Both specifications from the manifest, the window interior test, and the cells themselves.""",
        ),
        ("code", """table("ch4.specifications")"""),
        ("code", """table("ch4.window_interior")"""),
        (
            "code",
            """cells = pl.read_parquet(MARTS / "ch4_cells.parquet")
print(cells.height, "cells over", cells["cbsa_code"].n_unique(), "metros and", cells["window_id"].n_unique(), "windows")
cells.group_by("window_id").agg(
    pl.col("first_year").min(), pl.col("last_year").max(), pl.col("permits_rate").mean().alias("mean building rate"),
    pl.col("annual_growth").mean().alias("mean annual growth"), pl.col("migration_rate").mean().alias("mean migration per 100"),
).sort("window_id")""",
        ),
    ]


NOTEBOOKS = {
    "01_the_anchor.ipynb": nb1,
    "02_the_lock_in.ipynb": nb2,
    "03_supply_and_demand.ipynb": nb3,
}


def build(name: str, cells: list[tuple[str, str]]) -> nbformat.NotebookNode:
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb.metadata["language_info"] = {"name": "python"}
    nb.cells = [
        nbformat.v4.new_markdown_cell(text) if kind == "markdown" else nbformat.v4.new_code_cell(text)
        for kind, text in cells
    ]
    return nb


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-execute", action="store_true")
    parser.add_argument("--only", default=None, help="one notebook file name")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    for name, cells in NOTEBOOKS.items():
        if args.only and name != args.only:
            continue
        nb = build(name, cells())
        if not args.no_execute:
            from nbclient import NotebookClient

            NotebookClient(
                nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(OUT)}}
            ).execute()
        nbformat.write(nb, OUT / name)
        print(f"wrote notebooks/{name}{'' if args.no_execute else ' (executed)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
