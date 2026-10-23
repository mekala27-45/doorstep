"""The eight chapters on the real metros: plans registered first, then every estimate, its numbers, its chart.

Every plan is registered (hashed and written to results/chapters/plans.json) before any estimate runs; a
plan that changed since it was registered stops the stage. Each chapter writes its values, tables and chart
message into the partial manifest, its chart specification into results/charts, and the frames the site
reads into results/marts. The method note fields and the pushback paragraph are manifest values too, so the
story, the memo and the pages all quote the same words.
"""

from __future__ import annotations

import json
import time
from typing import Any

import polars as pl
from doorstep_chapters import (
    c1_definition,
    c2_rate_shock,
    c3_burden,
    c4_supply,
    c5_ranking,
    c6_buyers,
    c7_migration,
    c8_decision,
    calculator,
)
from doorstep_chapters.common import ChapterResult, check_reporting_years
from doorstep_chapters.panel import Panel, from_marts
from doorstep_chapters.plans import MODULES, register
from doorstep_core.config import POLICY, Policy
from doorstep_core.log import get_logger
from doorstep_core.manifest import Manifest, Scribe
from doorstep_core.paths import Paths
from doorstep_core.scalars import integer, num

from doorstep_pipeline.charts import Annotation, Chart, Series, State
from doorstep_pipeline.charts import Panel as ChartPanel
from doorstep_pipeline.common import new_partial, save_partial

log = get_logger(__name__)

CHAPTER_SOURCES = {
    1: "real:fhfa+acs+pmms",
    2: "real:hmda",
    3: "real:acs",
    4: "real:bps+fhfa",
    5: "real:fhfa+acs+pmms",
    6: "real:hmda+acs",
    7: "real:popest+fhfa",
    8: "real:fhfa+acs+pmms",
}


def _points(frame: pl.DataFrame, x: str, y: str) -> list[tuple[Any, float | None]]:
    return [(r[x], None if r[y] is None else float(r[y])) for r in frame.select([x, y]).iter_rows(named=True)]


def _col(frame: pl.DataFrame, name: str) -> list[float | None]:
    return [None if v is None else float(v) for v in frame[name].to_list()]


def _write_result(
    manifest: Manifest,
    r: ChapterResult,
    hashes: dict[str, str],
    p: Paths,
    chart: Chart | None,
    extra: dict[str, Chart],
) -> None:
    source = CHAPTER_SOURCES[r.number] if r.source == "real" else "simulated"
    origin = f"doorstep_chapters.c{r.number}_{r.slug}"
    for key, v in r.values.items():
        Scribe(manifest, source=source, population=r.population, origin=origin, model=v.model).put(
            key, v.value, v.fmt
        )
    for key, t in r.tables.items():
        Scribe(manifest, source=source, population=r.population, origin=origin, model=t.model).table(
            key, t.columns, t.formats, t.rows
        )
    s = Scribe(manifest, source=source, population=r.population, origin=origin)
    s.put(f"ch{r.number}.plan_hash", hashes[r.slug], "text")
    s.put(f"ch{r.number}.title", MODULES[r.number - 1].TITLE, "text")
    s.put(f"ch{r.number}.slug", r.slug, "text")
    s.put(f"ch{r.number}.population", r.population, "text")
    s.put(f"ch{r.number}.pushback", r.pushback, "text")
    for name, text in r.method.items():
        s.put(f"ch{r.number}.method.{name}", text, "text")
    s.put(f"ch{r.number}.reported_years", ", ".join(str(y) for y in r.reported_years), "text")
    if r.figure is not None and chart is not None:
        Scribe(manifest, source=source, population=r.population, origin=origin, model=r.figure.model).figure(
            f"chart.{r.slug}",
            r.figure.title,
            r.figure.callout or r.figure.subtitle,
            data=f"charts/{chart.id}.json",
            subtitle=r.figure.subtitle,
            sql=r.figure.sql,
        )
        chart.write(p.results / "charts")
    for name, fig in r.extra_figures.items():
        c = extra.get(name)
        if c is None:
            continue
        Scribe(manifest, source=source, population=r.population, origin=origin, model=fig.model).figure(
            f"chart.{r.slug}.{name}",
            fig.title,
            fig.callout or fig.subtitle,
            data=f"charts/{c.id}.json",
            subtitle=fig.subtitle,
            sql=fig.sql,
        )
        c.write(p.results / "charts")
    p.marts.mkdir(parents=True, exist_ok=True)
    for name, frame in r.marts.items():
        frame.write_parquet(p.marts / f"{name}.parquet", compression="zstd")


# Chart specifications per chapter


def _chart1(r: ChapterResult, source: str) -> Chart:
    assert r.figure is not None
    nat = r.figure.frames["national"]
    peak = int(r.values["ch1.peak_year"].value or 0)
    latest = int(r.values["ch1.latest_year"].value or 0)
    share = Series(
        "Payment share of income",
        "owning",
        _points(nat, "year", "payment_share"),
        low=_col(nat, "payment_share_low"),
        high=_col(nat, "payment_share_high"),
        label="payment share",
    )
    pti = Series(
        "Price to income", "adjusted", _points(nat, "year", "price_to_income"), label="price to income"
    )
    panel_share = ChartPanel(
        "The payment story",
        [share],
        annotations=[
            Annotation(
                peak,
                float(nat.filter(pl.col("year") == peak)["payment_share"][0])
                if peak in nat["year"].to_list()
                else None,
                f"{peak}",
                state="peak",
            ),
            Annotation(
                latest,
                float(nat.filter(pl.col("year") == latest)["payment_share"][0]),
                f"{latest}",
                state="peak",
            ),
        ],
        rules=[{"y": POLICY.affordable_line, "label": "30 percent line", "role": "renting"}],
        y_label="share of median income",
        y_format="pct0",
    )
    panel_pti = ChartPanel(
        "The price story", [pti], y_label="median home over median income", y_format="ratio1"
    )
    states = [
        State(
            "price",
            "Price to income: the median home as a multiple of the median income, every year the census reports one.",
            show=["Price to income"],
        ),
        State(
            "payment",
            "The payment share: twelve payments on the median home over the median income, at each year's rate.",
            show=["Payment share of income"],
            highlight=["Payment share of income"],
        ),
        State(
            "peak",
            "The latest year against 2006, the peak of the last cycle, with the Monte Carlo interval.",
            show=["Payment share of income"],
            highlight=["Payment share of income"],
        ),
    ]
    rows = [
        [
            int(x["year"]),
            float(x["price_to_income"]),
            float(x["payment_share"]),
            float(x["payment_share_low"]),
            float(x["payment_share_high"]),
        ]
        for x in nat.iter_rows(named=True)
    ]
    return Chart(
        "definition",
        "multiples",
        r.figure.title,
        r.figure.subtitle,
        source,
        r.figure.sql,
        "year",
        "int",
        "",
        "",
        [panel_pti, panel_share],
        states,
        ["Year", "Price to income", "Payment share", "Low", "High"],
        rows,
        notes=["The 2020 census release does not exist; the line breaks there."],
    )


def _chart2(r: ChapterResult, source: str) -> tuple[Chart, Chart]:
    assert r.figure is not None
    d = r.figure.frames["decomposition"]
    over = str(r.values["ch2.overtaking_quarter"].value)
    price = Series("Price part", "owning", _points(d, "period", "price_part"), label="price")
    rate = Series("Rate part", "rate", _points(d, "period", "rate_part"), label="rate")
    ann = []
    if over and over != "never":
        y = float(d.filter(pl.col("period") == over)["rate_part"][0])
        ann.append(Annotation(over, y, f"rate part overtakes in {over}", state="overtaking"))
    panel = ChartPanel(
        "Change in the monthly payment on the median home since 2019Q1",
        [price, rate],
        annotations=ann,
        rules=[{"y": 0.0, "faint": True}],
        y_label="dollars per month",
        y_format="susd0",
    )
    states = [
        State(
            "price",
            "The price part: what the payment would have done had the rate stayed where it was in 2019.",
            show=["Price part"],
            highlight=["Price part"],
        ),
        State(
            "rate",
            "The rate part: the rest of the change, from the rate alone.",
            show=["Price part", "Rate part"],
            highlight=["Rate part"],
        ),
        State(
            "overtaking",
            "The quarter the rate part overtook the price part.",
            show=["Price part", "Rate part"],
            highlight=["Rate part"],
        ),
    ]
    rows = [
        [x["period"], float(x["rate"]), float(x["payment"]), float(x["price_part"]), float(x["rate_part"])]
        for x in d.iter_rows(named=True)
    ]
    main = Chart(
        "rate_shock",
        "area",
        r.figure.title,
        r.figure.subtitle,
        source,
        r.figure.sql,
        "quarter",
        "quarter",
        "dollars per month",
        "susd0",
        [panel],
        states,
        ["Quarter", "Rate", "Payment", "Price part", "Rate part"],
        rows,
    )
    li = r.figure.frames["lock_in"]
    fig = r.extra_figures["lock_in"]
    pts = Series("Metros", "borrowers", _points(li, "lock_in_per_100", "change"), label="metro")
    coef = float(r.values["ch2.lock_in.coef"].value or 0.0)
    xs = [num(li["lock_in_per_100"].min()), num(li["lock_in_per_100"].max())]
    mean_x = num(li["lock_in_per_100"].mean())
    mean_y = num(li["change"].mean())
    line = Series("Fitted slope", "adjusted", [(x, mean_y + coef * (x - mean_x)) for x in xs], label="slope")
    panel2 = ChartPanel(
        "Change in turnover against lock in intensity",
        [pts, line],
        rules=[{"y": 0.0, "faint": True}],
        y_label="purchases per 100 owners, change",
        y_format="sfloat2",
    )
    rows2 = [
        [
            x["cbsa_title"],
            float(x["lock_in_per_100"]),
            float(x["before"]),
            float(x["after"]),
            float(x["change"]),
        ]
        for x in li.iter_rows(named=True)
    ]
    lock = Chart(
        "lock_in",
        "scatter",
        fig.title,
        fig.subtitle,
        source,
        fig.sql,
        "originations under four percent per 100 owner households",
        "float1",
        "change in purchases per 100 owners",
        "sfloat2",
        [panel2],
        [
            State(
                "all",
                "Every metro, with the fitted slope of the fixed effects regression.",
                show=["Metros", "Fitted slope"],
            )
        ],
        ["Metro", "Lock in per 100", "Turnover before", "Turnover after", "Change"],
        rows2,
    )
    return main, lock


def _chart3(r: ChapterResult, source: str) -> Chart:
    assert r.figure is not None
    b = r.figure.frames["bands"]
    under = Series("Under 30 percent", "control", _points(b, "year", "under_30"), label="under 30")
    mid = Series("30 to 50 percent", "renting", _points(b, "year", "from_30_to_50"), label="30 to 50")
    over = Series("50 percent and over", "burden", _points(b, "year", "over_50"), label="50 and over")
    cps = str(r.values["ch3.changepoints"].value or "none")
    ann = [
        Annotation(int(c.strip()), None, f"changepoint {c.strip()}", state="changepoints")
        for c in cps.split(",")
        if c.strip().isdigit()
    ]
    panel = ChartPanel(
        "Renter households by the share of income the rent takes",
        [under, mid, over],
        annotations=ann,
        y_label="share of renters",
        y_format="pct0",
    )
    states = [
        State(
            "bands",
            "Every renter household in one of three bands: under thirty percent of income, thirty to fifty, fifty and over.",
            show=["Under 30 percent", "30 to 50 percent", "50 percent and over"],
        ),
        State(
            "severe",
            "The severely burdened share, fifty percent and over, with its interval in the latest year.",
            show=["Under 30 percent", "30 to 50 percent", "50 percent and over"],
            highlight=["50 percent and over"],
        ),
        State(
            "changepoints",
            "Where the national series moved and stayed moved, by PELT.",
            show=["Under 30 percent", "30 to 50 percent", "50 percent and over"],
            highlight=["50 percent and over"],
        ),
    ]
    rows = [
        [int(x["year"]), float(x["under_30"]), float(x["from_30_to_50"]), float(x["over_50"])]
        for x in b.iter_rows(named=True)
    ]
    return Chart(
        "burden",
        "bars",
        r.figure.title,
        r.figure.subtitle,
        source,
        r.figure.sql,
        "year",
        "int",
        "share of renters",
        "pct0",
        [panel],
        states,
        ["Year", "Under 30 percent", "30 to 50 percent", "50 percent and over"],
        rows,
        notes=["Shares are of renters with a computed rent share; the 2020 release does not exist."],
    )


def _chart4(r: ChapterResult, source: str) -> Chart:
    assert r.figure is not None
    cells = r.figure.frames["cells"]
    line = r.figure.frames["line"]
    pts = Series("Metro windows", "supply", _points(cells, "permits_rate", "annual_growth"), label="metro")
    controlled = Series(
        "With the demand control",
        "adjusted",
        _points(line, "permits_rate", "controlled"),
        low=_col(line, "controlled_low"),
        high=_col(line, "controlled_high"),
        label="controlled",
    )
    uncontrolled = Series(
        "Without the demand control",
        "control",
        _points(line, "permits_rate", "uncontrolled"),
        dashed=True,
        label="uncontrolled",
    )
    panel = ChartPanel(
        "Annual price growth against the building rate, latest window",
        [pts, controlled, uncontrolled],
        rules=[{"y": 0.0, "faint": True}],
        y_label="annual log price growth",
        y_format="spct1",
    )
    states = [
        State(
            "cells",
            "Every metro in the latest window: the building rate the year before against the price growth that followed.",
            show=["Metro windows"],
        ),
        State(
            "controlled",
            "The slope with the demand shock in the regression, and its interval.",
            show=["Metro windows", "With the demand control"],
            highlight=["With the demand control"],
        ),
        State(
            "both",
            "The slope without the demand control beside it: the bias the recovery study measures.",
            show=["Metro windows", "With the demand control", "Without the demand control"],
            highlight=["Without the demand control"],
        ),
    ]
    rows = [
        [
            x["cbsa_title"],
            int(x["first_year"]),
            int(x["last_year"]),
            float(x["permits_rate"]),
            float(x["annual_growth"]),
            float(x["migration_rate"]),
        ]
        for x in cells.iter_rows(named=True)
    ]
    return Chart(
        "supply",
        "scatter",
        r.figure.title,
        r.figure.subtitle,
        source,
        r.figure.sql,
        "permits per 100 households, lagged one year",
        "float2",
        "annual log price growth",
        "spct1",
        [panel],
        states,
        ["Metro", "First year", "Last year", "Building rate", "Annual growth", "Migration per 100"],
        rows,
    )


def _chart5(r: ChapterResult, source: str) -> Chart:
    assert r.figure is not None
    slope = r.figure.frames["slope"]
    series = [
        Series(
            str(x["cbsa_title"]).split(",")[0],
            "adjusted" if x["moves"] else "control",
            [("raw", float(x["raw_rank"])), ("adjusted", float(x["adjusted_rank"]))],
            low=[None, float(x["adjusted_rank_low"])],
            high=[None, float(x["adjusted_rank_high"])],
            label=str(x["cbsa_title"]).split(",")[0],
        )
        for x in slope.iter_rows(named=True)
    ]
    panel = ChartPanel(
        "Rank by price and rank by payment share of local income",
        series,
        y_label="rank, 1 is least affordable",
        y_format="int",
    )
    states = [
        State(
            "raw",
            "The twenty largest metros ranked by the price of the median home.",
            show=[s.name for s in series],
        ),
        State(
            "adjusted",
            "The same metros ranked by the payment on that home as a share of what people there earn, with rank intervals.",
            show=[s.name for s in series],
            highlight=[
                s.name for s, x in zip(series, slope.iter_rows(named=True), strict=True) if x["moves"]
            ],
        ),
    ]
    rows = [
        [
            x["cbsa_title"],
            int(x["raw_rank"]),
            int(x["adjusted_rank"]),
            int(x["adjusted_rank_low"]),
            int(x["adjusted_rank_high"]),
            float(x["payment_share"]),
        ]
        for x in slope.iter_rows(named=True)
    ]
    return Chart(
        "ranking",
        "slope",
        r.figure.title,
        r.figure.subtitle,
        source,
        r.figure.sql,
        "",
        "text",
        "rank",
        "int",
        [panel],
        states,
        ["Metro", "Raw rank", "Adjusted rank", "Low", "High", "Payment share"],
        rows,
        notes=["Rank 1 is the most expensive on the left and the least affordable on the right."],
    )


def _chart6(r: ChapterResult, source: str) -> Chart:
    assert r.figure is not None
    s = r.figure.frames["series"]
    ratio = Series(
        "Borrower income over the local median",
        "borrowers",
        _points(s, "year", "ratio"),
        low=_col(s, "ratio_low"),
        high=_col(s, "ratio_high"),
        label="income ratio",
    )
    under = Series(
        "Share of buyers under 35",
        "adjusted",
        _points(s, "year", "under_35"),
        low=_col(s, "under_35_low"),
        high=_col(s, "under_35_high"),
        label="under 35",
    )
    p1 = ChartPanel("Borrower income over the metro median", [ratio], y_label="ratio", y_format="ratio2")
    p2 = ChartPanel("Buyers under 35", [under], y_label="share of purchase loans", y_format="pct0")
    states = [
        State(
            "ratio",
            "The median purchase borrower earns this multiple of the local median household income.",
            show=["Borrower income over the local median"],
            highlight=["Borrower income over the local median"],
        ),
        State(
            "age",
            "The share of purchase loans to borrowers under 35.",
            show=["Share of buyers under 35"],
            highlight=["Share of buyers under 35"],
        ),
    ]
    rows = [
        [
            int(x["year"]),
            int(x["loans"]),
            float(x["ratio"]),
            float(x["ratio_low"]),
            float(x["ratio_high"]),
            float(x["under_35"]),
            float(x["over_2x"]),
            float(x["vti"]),
        ]
        for x in s.iter_rows(named=True)
    ]
    return Chart(
        "buyers",
        "multiples",
        r.figure.title,
        r.figure.subtitle,
        source,
        r.figure.sql,
        "year",
        "int",
        "",
        "",
        [p1, p2],
        states,
        [
            "Year",
            "Loans",
            "Income ratio",
            "Low",
            "High",
            "Under 35",
            "Above twice the median",
            "Value to income",
        ],
        rows,
    )


def _chart7(r: ChapterResult, source: str, policy: Policy) -> Chart:
    assert r.figure is not None
    sc = r.figure.frames["scatter"]
    syn = r.figure.frames["synthetic"]
    pts = Series("Metros", "people", _points(sc, "migration_shock", "growth"), label="metro")
    coef = float(r.values["ch7.coef"].value or 0.0)
    xs = [num(sc["migration_shock"].min()), num(sc["migration_shock"].max())]
    mx, my = num(sc["migration_shock"].mean()), num(sc["growth"].mean())
    fit = Series("Fitted slope", "adjusted", [(x, my + coef * (x - mx)) for x in xs], label="slope")
    pcoef = float(r.values["ch7.placebo.coef"].value or 0.0)
    pmy = num(sc["placebo_growth"].mean())
    placebo = Series(
        "Placebo slope", "control", [(x, pmy + pcoef * (x - mx)) for x in xs], dashed=True, label="placebo"
    )
    p1 = ChartPanel(
        "Price growth against the migration shock",
        [pts, fit, placebo],
        rules=[{"y": 0.0, "faint": True}],
        y_label="log price growth over the window",
        y_format="spct0",
    )
    panels = [p1]
    if syn.height:
        first = syn.filter(pl.col("metro") == syn["metro"][0])
        actual = Series("Actual", "ink", _points(first, "period", "actual"), label="actual")
        synthetic = Series(
            "Synthetic control",
            "control",
            _points(first, "period", "synthetic"),
            low=[
                float(a) + float(b)
                for a, b in zip(first["synthetic"].to_list(), first["band_low"].to_list(), strict=True)
            ],
            high=[
                float(a) + float(b)
                for a, b in zip(first["synthetic"].to_list(), first["band_high"].to_list(), strict=True)
            ],
            dashed=True,
            label="synthetic",
        )
        a, b = policy.migration_window
        p2 = ChartPanel(
            f"Synthetic control for {first['metro'][0]}",
            [actual, synthetic],
            bands=[{"from": a, "to": b, "label": "shock window"}],
            y_label="log index, last pre quarter = 0",
            y_format="spct0",
        )
        panels.append(p2)
    states = [
        State(
            "scatter",
            "Every metro: the pandemic migration shock per hundred residents against price growth over the window.",
            show=["Metros", "Fitted slope"],
        ),
        State(
            "placebo",
            "The placebo: the same shock against price growth in the years before the pandemic.",
            show=["Metros", "Fitted slope", "Placebo slope"],
            highlight=["Placebo slope"],
        ),
        State(
            "synthetic",
            "The largest gainer against its synthetic control, with the band the placebo donors fill.",
            show=["Actual", "Synthetic control"],
            highlight=["Actual"],
        ),
    ]
    rows = [
        [
            x["cbsa_title"],
            float(x["migration_pre"]),
            float(x["migration_pandemic"]),
            float(x["migration_shock"]),
            float(x["growth"]),
            float(x["placebo_growth"]),
        ]
        for x in sc.iter_rows(named=True)
    ]
    return Chart(
        "migration",
        "scatter",
        r.figure.title,
        r.figure.subtitle,
        source,
        r.figure.sql,
        "migration shock per 100 residents",
        "sfloat1",
        "log price growth",
        "spct0",
        panels,
        states,
        ["Metro", "Migration before", "Migration in the pandemic", "Shock", "Growth", "Placebo growth"],
        rows,
    )


def _chart8(r: ChapterResult, source: str) -> Chart:
    assert r.figure is not None
    curve = r.figure.frames["curve"]
    metros = r.figure.frames["metros"]
    diff = Series(
        "Renter wealth less owner equity", "renting", _points(curve, "year", "difference"), label="difference"
    )
    be = float(r.values["ch8.curve.breakeven"].value or 0.0)
    ann = (
        [Annotation(int(be), 0.0, f"breakeven in year {int(be)}", state="breakeven")]
        if be <= curve.height
        else []
    )
    med = float(r.values["ch8.breakeven.median"].value or 0.0)
    low = float(r.values["ch8.breakeven.low"].value or 0.0)
    high = float(r.values["ch8.breakeven.high"].value or 0.0)
    p1 = ChartPanel(
        f"Rent or buy in {curve['metro'][0]}",
        [diff],
        annotations=ann,
        rules=[{"y": 0.0, "label": "owning catches up", "role": "owning"}],
        bands=[
            {
                "from": str(int(low)),
                "to": str(int(min(high, curve.height))),
                "label": "interval across metros",
            }
        ],
        y_label="dollars, positive means renting is ahead",
        y_format="susd0",
    )
    states = [
        State(
            "curve",
            "Each year, what the renter holds less what the owner would net on selling, under the median path for the largest metro.",
            show=["Renter wealth less owner equity"],
        ),
        State(
            "breakeven",
            "The year owning catches up, and the interval of that year across metros.",
            show=["Renter wealth less owner equity"],
            highlight=["Renter wealth less owner equity"],
        ),
    ]
    rows = [
        [
            x["cbsa_title"],
            float(x["median_home"]),
            float(x["affordable_price"]),
            x["affordable_share"],
            float(x["down_payment_years"]),
            float(x["breakeven_years"]),
            float(x["breakeven_low"]),
            float(x["breakeven_high"]),
        ]
        for x in metros.sort("households", descending=True).head(50).iter_rows(named=True)
    ]
    return Chart(
        "decision",
        "curves",
        r.figure.title,
        r.figure.subtitle,
        source,
        r.figure.sql,
        "years of ownership",
        "int",
        "dollars",
        "susd0",
        [p1],
        states,
        [
            "Metro",
            "Median home",
            "Affordable price",
            "Affordable share",
            "Down payment years",
            "Breakeven",
            "Low",
            "High",
        ],
        rows,
        notes=[f"median breakeven {med:.1f} years across metros"],
    )


def run(
    p: Paths, *, replicates: int | None = None, draws: int | None = None, policy: Policy = POLICY
) -> Manifest:
    hashes = register(p.results / "chapters" / "plans.json", policy)
    panel = from_marts(p.marts, policy)
    manifest = new_partial("chapters")
    timings: dict[str, float] = {}
    index: list[dict[str, Any]] = []

    def done(r: ChapterResult, chart: Chart | None, extra: dict[str, Chart] | None = None) -> None:
        check_reporting_years(MODULES[r.number - 1].plan(policy), r.reported_years, policy)
        _write_result(manifest, r, hashes, p, chart, extra or {})
        index.append(
            {
                "number": r.number,
                "slug": r.slug,
                "title": MODULES[r.number - 1].TITLE,
                "branch": r.branch,
                "message": r.message,
                "plan_hash": hashes[r.slug],
                "chart": chart.id if chart else None,
            }
        )
        log.info("chapter done", chapter=r.number, branch=r.branch, seconds=round(timings[r.slug], 1))

    def timed(slug: str, fn: Any) -> Any:
        t = time.time()
        out = fn()
        timings[slug] = time.time() - t
        return out

    src = "real" if panel.source == "real" else "simulated"
    r1 = timed("definition", lambda: c1_definition.estimate(panel, policy, draws=draws))
    done(r1, _chart1(r1, CHAPTER_SOURCES[1] if src == "real" else "simulated"))
    r2 = timed("rate_shock", lambda: c2_rate_shock.estimate(panel, policy))
    main2, lock2 = _chart2(r2, CHAPTER_SOURCES[2] if src == "real" else "simulated")
    done(r2, main2, {"lock_in": lock2})
    r3 = timed("burden", lambda: c3_burden.estimate(panel, policy, replicates=replicates))
    done(r3, _chart3(r3, CHAPTER_SOURCES[3] if src == "real" else "simulated"))
    r4 = timed("supply", lambda: c4_supply.estimate(panel, policy))
    done(r4, _chart4(r4, CHAPTER_SOURCES[4] if src == "real" else "simulated"))
    r5 = timed("ranking", lambda: c5_ranking.estimate(panel, policy, draws=draws))
    done(r5, _chart5(r5, CHAPTER_SOURCES[5] if src == "real" else "simulated"))
    r6 = timed("buyers", lambda: c6_buyers.estimate(panel, policy, replicates=replicates))
    done(r6, _chart6(r6, CHAPTER_SOURCES[6] if src == "real" else "simulated"))
    r7 = timed("migration", lambda: c7_migration.estimate(panel, policy))
    done(r7, _chart7(r7, CHAPTER_SOURCES[7] if src == "real" else "simulated", policy))
    r8 = timed("decision", lambda: c8_decision.estimate(panel, policy, draws=replicates))
    done(r8, _chart8(r8, CHAPTER_SOURCES[8] if src == "real" else "simulated"))

    calc_meta = calculator.write(panel, p.derived, p.marts, policy)
    s = Scribe(manifest, source="mixed", population="the eight chapters", origin="stages/chapters.py")
    s.put("chapters.count", len(index), "int")
    s.put("calculator.metros", integer(calc_meta["metros"]), "int")
    s.put("calculator.rate_default", num(calc_meta["rate_default"]), "rate2")
    s.put("calculator.rate_default_source", str(calc_meta["rate_default_source"]), "text")
    s.put("calculator.latest_period", str(calc_meta["latest_period"]), "quarter")
    s.put("calculator.income_year", integer(calc_meta["income_year"]), "year")
    s.put("chapters.panel_source", panel.source, "text")
    s.put("chapters.metros", int(panel.metro_year["cbsa_code"].n_unique()), "int")
    s.put("chapters.metropolitan", int(panel.metropolitan()["cbsa_code"].n_unique()), "int")
    s.put("chapters.latest_year", panel.latest_year, "year")
    s.put("chapters.latest_acs_year", panel.latest_acs_year, "year")
    s.put("chapters.latest_period", panel.latest_period, "quarter")
    s.put("chapters.anchor_year", panel.anchor_year, "year")
    s.put("chapters.seconds", sum(timings.values()), "float1")
    (p.results / "chapters" / "index.json").write_text(
        json.dumps({"chapters": index, "timings": timings}, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    save_partial(p, "chapters", manifest)
    return manifest


def panel_for(p: Paths, policy: Policy = POLICY) -> Panel:
    return from_marts(p.marts, policy)
