"""Loan level rows for the borrower pool chapter, with a known borrower income ratio and a known share of
buyers under 35, spread over lenders so the lender bootstrap can be graded for coverage.

Chapter 6 reads purchase loans at the grain the HMDA extract gives: a lender, a metro, a year, an income
reported in thousands, an age band and a property value at a bin midpoint. The simulator writes the same
grain at a stated scale, so the estimator that runs on the real extract runs here unchanged and its
interval can be checked against the parameters the generator used.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from doorstep_core.seeds import rng

from doorstep_sim.metros import World

N_LENDERS = 12
INCOME_SIGMA = 0.45
VALUE_TO_INCOME = 3.4
UNDER_35_BASE = 0.38
UNDER_35_SHIFT = -0.05  # the buyer pool gets older after the shock by five points
HMDA_FIRST_YEAR = 2018


def lender_loans(w: World, *, scale: float = 0.25) -> pl.DataFrame:
    """One row per simulated purchase loan from 2018 on: year, metro, lender, income in thousands, whether the
    borrower is under 35, the property value as a ratio of income and the rate spread. ``scale`` thins every
    metro by the same factor so the relative weight of metros is kept."""
    g = rng(w.seed, "lenders", w.condition.name)
    income_by = {
        (r["metro_id"], r["year"]): float(r["median_income"]) for r in w.metro_year.iter_rows(named=True)
    }
    frames: list[pl.DataFrame] = []
    for r in w.loans_year.sort(["metro_id", "year"]).iter_rows(named=True):
        year = int(r["year"])
        if year < HMDA_FIRST_YEAR:
            continue
        n = int(round(float(r["purchase_loans"]) * scale))
        if n == 0:
            continue
        code = str(r["metro_id"])
        ratio = float(r["borrower_income_ratio_true"])
        after = year >= w.truth.rate_shock_year + 1
        median_income = income_by[(code, year)]
        incomes = median_income * ratio * np.exp(g.normal(0.0, INCOME_SIGMA, n))
        under_35 = g.random(n) < (UNDER_35_BASE + (UNDER_35_SHIFT if after else 0.0))
        vti = VALUE_TO_INCOME * np.exp(g.normal(0.0, 0.25, n))
        spread = np.round(g.normal(0.3 + (0.2 if after else 0.0), 0.4, n), 3)
        lenders = g.integers(0, N_LENDERS, n)
        frames.append(
            pl.DataFrame(
                {
                    "year": np.full(n, year, dtype=np.int64),
                    "cbsa_code": [code] * n,
                    "lei": [f"SIMLEI{int(k):03d}" for k in lenders],
                    "income_k": np.maximum(np.round(incomes / 1000.0), 1.0).astype(np.int64),
                    "under_35": under_35.astype(np.int64),
                    "value_to_income": np.round(vti, 3),
                    "rate_spread": spread,
                }
            )
        )
    return pl.concat(frames).sort(["year", "cbsa_code", "lei", "income_k"])


def truth_under_35(year: int, w: World) -> float:
    return UNDER_35_BASE + (UNDER_35_SHIFT if year >= w.truth.rate_shock_year + 1 else 0.0)
