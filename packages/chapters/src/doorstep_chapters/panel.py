"""The panel every chapter reads: one shape whether the rows came from the simulator or the warehouse.

A chapter's estimator takes a ``Panel`` and never asks where it came from. ``from_world`` builds one from
a simulated world exactly the way the warehouse builds the real one (the index anchored to the reported
census value in the anchor year, the payment at the year's rate on ninety percent of the anchored value),
so an estimator proven here is the estimator that runs on the real metros. ``from_marts`` reads the
shipped marts under results/marts.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import polars as pl
from doorstep_core.config import POLICY, Policy
from doorstep_core.scalars import integer
from doorstep_finance.mortgage import payment_on_price
from doorstep_sim.lenders import lender_loans
from doorstep_sim.metros import World, burden_by_income

METRO_YEAR_COLUMNS = (
    "cbsa_code",
    "cbsa_title",
    "state",
    "kind",
    "year",
    "households",
    "owner_households",
    "renter_households",
    "population",
    "median_income",
    "median_income_moe",
    "renter_median_income",
    "value_reported",
    "value_reported_moe",
    "index_at",
    "value_anchored",
    "value_anchored_moe",
    "median_rent",
    "median_rent_moe",
    "median_rent_share",
    "renters_with_share",
    "renters_burdened",
    "renters_severe",
    "renters_with_share_moe",
    "renters_burdened_moe",
    "renters_severe_moe",
    "renter_burdened_share",
    "renter_severe_share",
    "owner_mortgage_burdened_share",
    "permits",
    "domestic_migration",
    "rate",
    "purchase_loans",
    "refinance_loans",
    "low_rate_originations",
    "under_3_5_originations",
    "under_3_originations",
    "purchase_median_value",
    "purchase_median_income",
    "purchase_under_35",
    "purchase_with_age",
    "purchase_lenders",
)


class PanelError(ValueError):
    pass


@dataclass(frozen=True)
class Panel:
    source: str  # "simulated" or "real"
    anchor_year: int
    metro_year: pl.DataFrame
    metro_quarter: pl.DataFrame  # cbsa_code, year, quarter, period, index_at, rate, value_anchored
    brackets: pl.DataFrame  # year, cbsa_code, bracket, households
    national_year: pl.DataFrame  # year, households, renter_households, median_income, rate, burden shares
    burden_by_income: pl.DataFrame | None = (
        None  # year, cbsa_code, income_group, group_order, renters, burdened, severe
    )
    borrowers: Borrowers | None = None

    def years(self) -> list[int]:
        return sorted(int(y) for y in self.metro_year["year"].unique().to_list())

    @property
    def latest_year(self) -> int:
        return self.years()[-1]

    @property
    def latest_acs_year(self) -> int:
        with_income = self.metro_year.filter(pl.col("median_income").is_not_null())
        return integer(with_income["year"].max()) if with_income.height else self.latest_year

    @property
    def latest_period(self) -> str:
        q = self.metro_quarter.filter(pl.col("index_at").is_not_null()).sort(["year", "quarter"])
        return str(q["period"][-1]) if q.height else f"{self.latest_year}Q4"

    def metropolitan(self) -> pl.DataFrame:
        return self.metro_year.filter(pl.col("kind") == "metropolitan")

    def with_anchor(self, anchor_year: int) -> Panel:
        """The same panel re-anchored: every value moved from the reported census value of another year."""
        return re_anchor(self, anchor_year)


def _payment(frame: pl.DataFrame, policy: Policy) -> pl.DataFrame:
    rows = frame.select(["value_anchored", "rate", "median_income"]).iter_rows()
    pay: list[float | None] = []
    share: list[float | None] = []
    for value, rate, income in rows:
        if value is None or rate is None:
            pay.append(None)
            share.append(None)
            continue
        p = payment_on_price(float(value), float(rate), policy.down_payment_share, policy.loan_term_years)
        pay.append(p)
        share.append(12.0 * p / float(income) if income else None)
    return frame.with_columns(
        pl.Series("payment", pay, dtype=pl.Float64), pl.Series("payment_share", share, dtype=pl.Float64)
    )


def re_anchor(panel: Panel, anchor_year: int, policy: Policy = POLICY) -> Panel:
    my = panel.metro_year
    anchor = my.filter(
        (pl.col("year") == anchor_year)
        & pl.col("value_reported").is_not_null()
        & pl.col("index_at").is_not_null()
    ).select(
        "cbsa_code",
        pl.col("value_reported").alias("_anchor_value"),
        pl.col("value_reported_moe").alias("_anchor_moe"),
        pl.col("index_at").alias("_anchor_index"),
    )
    if anchor.height == 0:
        raise PanelError(f"no metro has a reported value and an index in {anchor_year}")
    my2 = (
        my.drop(
            [
                c
                for c in ("value_anchored", "value_anchored_moe", "payment", "payment_share")
                if c in my.columns
            ]
        )
        .join(anchor, on="cbsa_code", how="left")
        .with_columns(
            (pl.col("_anchor_value") * pl.col("index_at") / pl.col("_anchor_index")).alias("value_anchored"),
            (pl.col("_anchor_moe") * pl.col("index_at") / pl.col("_anchor_index")).alias(
                "value_anchored_moe"
            ),
        )
        .drop(["_anchor_value", "_anchor_moe", "_anchor_index"])
    )
    my2 = _payment(my2, policy)
    q = panel.metro_quarter.drop(
        [c for c in ("value_anchored", "payment") if c in panel.metro_quarter.columns]
    )
    q = (
        q.join(anchor.select("cbsa_code", "_anchor_value", "_anchor_index"), on="cbsa_code", how="left")
        .with_columns(
            (pl.col("_anchor_value") * pl.col("index_at") / pl.col("_anchor_index")).alias("value_anchored")
        )
        .drop(["_anchor_value", "_anchor_index"])
    )
    pay = [
        payment_on_price(float(v), float(r), policy.down_payment_share, policy.loan_term_years)
        if v is not None and r is not None
        else None
        for v, r in q.select(["value_anchored", "rate"]).iter_rows()
    ]
    q = q.with_columns(pl.Series("payment", pay, dtype=pl.Float64))
    return replace(
        panel,
        anchor_year=anchor_year,
        metro_year=my2.sort(["cbsa_code", "year"]),
        metro_quarter=q.sort(["cbsa_code", "year", "quarter"]),
    )


def from_world(world: World, policy: Policy = POLICY, *, with_loans: bool = False) -> Panel:
    """The simulated world in the panel's shape: anchored like the warehouse anchors the real index."""
    my = world.metro_year
    loans = world.loans_year
    annual_index = (
        world.metro_quarter.group_by(["metro_id", "year"])
        .agg(pl.col("index").mean().alias("index_at"))
        .sort(["metro_id", "year"])
    )
    frame = (
        my.join(annual_index, on=["metro_id", "year"], how="left")
        .join(
            loans.select(
                "metro_id",
                "year",
                "purchase_loans",
                "refinance_loans",
                "low_rate_originations",
                "rate_at_origination",
                "purchase_median_value",
                "borrower_income_ratio",
            ),
            on=["metro_id", "year"],
            how="left",
        )
        .with_columns(
            pl.col("metro_id").alias("cbsa_code"),
            pl.col("metro_name").alias("cbsa_title"),
            pl.col("median_value_reported").alias("value_reported"),
            pl.col("median_value_moe").alias("value_reported_moe"),
            (pl.col("domestic_migration_per_100") * pl.col("population") / 100.0).alias("domestic_migration"),
            (pl.col("renter_households") * 0.97).alias("renters_with_share"),
            (pl.col("renter_households") * 0.97 * pl.col("rent_burdened_share")).alias("renters_burdened"),
            (pl.col("renter_households") * 0.97 * pl.col("rent_severe_share")).alias("renters_severe"),
            (1.645 * (pl.col("renter_households") * 0.97 * 12.0).sqrt()).alias("renters_with_share_moe"),
            (
                1.645 * (pl.col("renter_households") * 0.97 * pl.col("rent_burdened_share") * 12.0).sqrt()
            ).alias("renters_burdened_moe"),
            (1.645 * (pl.col("renter_households") * 0.97 * pl.col("rent_severe_share") * 12.0).sqrt()).alias(
                "renters_severe_moe"
            ),
            (12.0 * pl.col("median_rent") / pl.col("renter_median_income")).alias("median_rent_share"),
            pl.col("rent_burdened_share").alias("renter_burdened_share"),
            pl.col("rent_severe_share").alias("renter_severe_share"),
            (pl.col("rent_burdened_share") * 0.65).alias("owner_mortgage_burdened_share"),
            pl.when(pl.col("rate_at_origination") < 3.5)
            .then(pl.col("low_rate_originations"))
            .otherwise(0.0)
            .alias("under_3_5_originations"),
            pl.when(pl.col("rate_at_origination") < 3.0)
            .then(pl.col("low_rate_originations"))
            .otherwise(0.0)
            .alias("under_3_originations"),
            (pl.col("median_income") * pl.col("borrower_income_ratio")).alias("purchase_median_income"),
            (pl.col("purchase_loans") * 0.36).alias("purchase_under_35"),
            pl.col("purchase_loans").alias("purchase_with_age"),
            pl.lit(12).alias("purchase_lenders"),
        )
        .with_columns(
            pl.lit(None, dtype=pl.Float64).alias("value_anchored"),
            pl.lit(None, dtype=pl.Float64).alias("value_anchored_moe"),
        )
    )
    frame = frame.select([c for c in METRO_YEAR_COLUMNS if c in frame.columns])
    quarter = world.metro_quarter.select(
        pl.col("metro_id").alias("cbsa_code"),
        "year",
        "quarter",
        "period",
        pl.col("index").alias("index_at"),
        "rate",
    )
    brackets = world.brackets.select(
        pl.col("year"), pl.col("metro_id").alias("cbsa_code"), "bracket", "households"
    )
    weights = my.select(
        "year",
        "households",
        "renter_households",
        "owner_households",
        "median_income",
        "median_value_true",
        "median_rent",
        "rent_burdened_share",
        "rent_severe_share",
        "rate",
    )
    national = (
        weights.group_by("year")
        .agg(
            pl.col("households").sum(),
            pl.col("owner_households").sum(),
            pl.col("renter_households").sum(),
            ((pl.col("median_income") * pl.col("households")).sum() / pl.col("households").sum()).alias(
                "median_income"
            ),
            (
                (pl.col("median_value_true") * pl.col("owner_households")).sum()
                / pl.col("owner_households").sum()
            ).alias("median_value_reported"),
            (
                (pl.col("median_rent") * pl.col("renter_households")).sum()
                / pl.col("renter_households").sum()
            ).alias("median_rent"),
            (
                (pl.col("rent_burdened_share") * pl.col("renter_households")).sum()
                / pl.col("renter_households").sum()
            ).alias("renter_burdened_share"),
            (
                (pl.col("rent_severe_share") * pl.col("renter_households")).sum()
                / pl.col("renter_households").sum()
            ).alias("renter_severe_share"),
            pl.col("rate").first(),
        )
        .sort("year")
    )
    panel = Panel(
        source="simulated",
        anchor_year=policy.anchor_year,
        metro_year=frame.sort(["cbsa_code", "year"]),
        metro_quarter=quarter.sort(["cbsa_code", "year", "quarter"]),
        brackets=brackets.sort(["year", "cbsa_code", "bracket"]),
        national_year=national,
        burden_by_income=burden_by_income(world).rename({"metro_id": "cbsa_code"}),
        borrowers=borrowers_from_loans(
            lender_loans(world), frame.select("year", "cbsa_code", "median_income")
        )
        if with_loans
        else None,
    )
    return re_anchor(panel, policy.anchor_year, policy)


def _first_state(states: str | None) -> str | None:
    if not states:
        return None
    return states.split("-")[0].strip()


def from_marts(marts: Path, policy: Policy = POLICY) -> Panel:
    """The real panel from the shipped marts."""
    my_path = marts / "mart_metro_year.parquet"
    if not my_path.exists():
        raise PanelError(f"{my_path} is missing; run the warehouse stage first")
    my = pl.read_parquet(my_path)
    state = pl.Series("state", [_first_state(s) for s in my["states"].to_list()], dtype=pl.String)
    frame = my.with_columns(
        state,
        pl.col("median_value_reported").alias("value_reported"),
        pl.col("median_value_reported_moe").alias("value_reported_moe"),
    )
    frame = frame.with_columns(
        [pl.lit(None, dtype=pl.Float64).alias(c) for c in METRO_YEAR_COLUMNS if c not in frame.columns]
    )
    frame = frame.select(list(METRO_YEAR_COLUMNS))
    quarter = pl.read_parquet(marts / "mart_metro_quarter.parquet").select(
        "cbsa_code", "year", "quarter", "period", pl.col("index_nsa").alias("index_at"), "rate"
    )
    brackets = pl.read_parquet(marts / "mart_income_brackets.parquet").select(
        "year", "cbsa_code", "bracket", "households"
    )
    national = pl.read_parquet(marts / "mart_national_year.parquet")
    burden_path = marts / "mart_rent_burden_by_income.parquet"
    burden = pl.read_parquet(burden_path) if burden_path.exists() else None
    panel = Panel(
        source="real",
        anchor_year=policy.anchor_year,
        metro_year=frame.sort(["cbsa_code", "year"]),
        metro_quarter=quarter.sort(["cbsa_code", "year", "quarter"]),
        brackets=brackets.sort(["year", "cbsa_code", "bracket"]),
        national_year=national.sort("year"),
        burden_by_income=burden,
        borrowers=borrowers_from_marts(marts),
    )
    return re_anchor(panel, policy.anchor_year, policy)


# The borrower pool, at the grain the chapter reads: histograms per lender, never a loan.

INCOME_BIN_K = 5
VTI_BIN = 0.25
SPREAD_BIN = 0.125


@dataclass(frozen=True)
class Borrowers:
    """``income``: year, cbsa_code, lei, income_bin (lower edge in thousands), loans, under_35, over_2x;
    ``vti``: year, lei, vti_bin, loans; ``spread``: year, spread_bin, loans."""

    income: pl.DataFrame
    vti: pl.DataFrame
    spread: pl.DataFrame


def borrowers_from_loans(loans: pl.DataFrame, median_income: pl.DataFrame) -> Borrowers:
    """Loan level rows (year, cbsa_code, lei, income_k, under_35, value_to_income, rate_spread) into the histograms.
    ``median_income`` has year, cbsa_code, median_income; a loan's year falls back to the nearest census year."""
    med = median_income.filter(pl.col("median_income").is_not_null()).sort(["cbsa_code", "year"])
    years = sorted(int(y) for y in loans["year"].unique().to_list())
    pieces: list[pl.DataFrame] = []
    for year in years:
        candidates = (
            med.filter(pl.col("year") <= year)
            .group_by("cbsa_code")
            .agg(pl.col("median_income").last().alias("metro_median"))
        )
        later = (
            med.filter(pl.col("year") > year)
            .group_by("cbsa_code")
            .agg(pl.col("median_income").first().alias("metro_median_later"))
        )
        sub = (
            loans.filter(pl.col("year") == year)
            .join(candidates, on="cbsa_code", how="left")
            .join(later, on="cbsa_code", how="left")
        )
        sub = sub.with_columns(pl.coalesce(["metro_median", "metro_median_later"]).alias("metro_median"))
        pieces.append(sub)
    joined = pl.concat(pieces).filter(pl.col("metro_median").is_not_null())
    joined = joined.with_columns(
        ((pl.col("income_k") // INCOME_BIN_K) * INCOME_BIN_K).cast(pl.Int64).alias("income_bin"),
        (pl.col("income_k") * 1000.0 >= 2.0 * pl.col("metro_median")).cast(pl.Int64).alias("over_2x"),
        ((pl.col("value_to_income") / VTI_BIN).floor() * VTI_BIN).alias("vti_bin"),
        ((pl.col("rate_spread") / SPREAD_BIN).floor() * SPREAD_BIN).alias("spread_bin"),
    )
    income = (
        joined.group_by(["year", "cbsa_code", "lei", "income_bin"])
        .agg(
            pl.len().alias("loans"),
            pl.col("under_35").sum().alias("under_35"),
            pl.col("over_2x").sum().alias("over_2x"),
        )
        .sort(["year", "cbsa_code", "lei", "income_bin"])
    )
    vti = (
        joined.group_by(["year", "lei", "vti_bin"])
        .agg(pl.len().alias("loans"))
        .sort(["year", "lei", "vti_bin"])
    )
    spread = (
        joined.filter(pl.col("spread_bin").is_not_null())
        .group_by(["year", "spread_bin"])
        .agg(pl.len().alias("loans"))
        .sort(["year", "spread_bin"])
    )
    return Borrowers(income, vti, spread)


def borrowers_from_marts(marts: Path) -> Borrowers | None:
    paths = [
        marts / "mart_borrowers_income.parquet",
        marts / "mart_borrowers_vti.parquet",
        marts / "mart_borrowers_spread.parquet",
    ]
    if not all(p.exists() for p in paths):
        return None
    return Borrowers(pl.read_parquet(paths[0]), pl.read_parquet(paths[1]), pl.read_parquet(paths[2]))
