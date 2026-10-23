"""Synthetic metros with known truth.

Sixty metros over twenty years, quarterly prices and annual everything else, generated from a stated
structural model so that every estimator in the story can be graded on what it was built to recover:

- incomes: a known median per metro with a known growth path, and a known log normal distribution
  around it, so the exact share of households that can afford a stated price is known;
- the census view of those incomes: medians with a margin of error, bracket counts with small cells
  suppressed, and self reported home values biased by a known factor per metro;
- demand: a migration series per metro with a known price response, and a reverse causality knob
  under which migration itself responds to lagged affordability (cheap metros attract people), which
  is the condition the migration chapter's pre trend placebo exists to catch;
- supply: a known elasticity per metro of permits to lagged price growth, and a known effect of
  permits on price growth, so the supply chapter can be graded with and without the demand control;
- rates and loans: a known rate path, purchase and refinance originations whose held rates follow
  it, and a known lock in response of turnover to the share of owners holding cheap mortgages;
- rents: a known rent to price link, so burden shares follow from the income distribution;
- a planted step in the severely burdened series at a known year for the changepoint search;
- the true affordability ranking, confounded by design: the expensive metros are given the high
  incomes, so the raw price ranking and the true payment share ranking disagree.

Everything is seeded through named streams and sorted before any draw, so a seed reproduces a world
whatever order a frame arrived in.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl
from doorstep_core.config import INCOME_BRACKETS
from doorstep_core.model import StrictModel
from doorstep_core.seeds import rng
from doorstep_finance.brackets import exact_share_above_lognormal, lognormal_bracket_counts
from doorstep_finance.mortgage import payment_share


class Condition(StrictModel):
    """One cell of the recovery study."""

    name: str
    demand_strength: str  # "weak" or "strong": the price response to a migration shock
    supply_dispersion: str  # "narrow" or "wide": how much elasticity varies across metros
    reverse_causality: str  # "none", "mild" or "strong": migration's response to lagged affordability
    noise: str  # "low" or "high"

    def knobs(self) -> dict[str, float]:
        return {
            "beta_demand": {"weak": 0.004, "strong": 0.012}[self.demand_strength],
            "elasticity_sd": {"narrow": 0.10, "wide": 0.40}[self.supply_dispersion],
            "reverse": {"none": 0.0, "mild": 0.6, "strong": 1.8}[self.reverse_causality],
            "noise_sd": {"low": 0.010, "high": 0.030}[self.noise],
        }


def conditions() -> list[Condition]:
    out: list[Condition] = []
    for demand in ("weak", "strong"):
        for supply in ("narrow", "wide"):
            for reverse in ("none", "mild", "strong"):
                for noise in ("low", "high"):
                    out.append(
                        Condition(
                            name=f"{demand}_demand/{supply}_supply/{reverse}_reverse/{noise}_noise",
                            demand_strength=demand,
                            supply_dispersion=supply,
                            reverse_causality=reverse,
                            noise=noise,
                        )
                    )
    return out


DEMONSTRATION = Condition(
    name="demonstration",
    demand_strength="strong",
    supply_dispersion="wide",
    reverse_causality="mild",
    noise="low",
)


@dataclass(frozen=True)
class Truth:
    """What the generator knows and the estimators are graded against."""

    beta_supply: float
    beta_demand: float
    reverse: float
    lock_in_response: float
    burden_step_year: int
    burden_step_size: float
    rate_shock_year: int
    metros: pl.DataFrame  # per metro: elasticity, income_bias, value_bias, true ranking inputs


@dataclass(frozen=True)
class World:
    condition: Condition
    seed: int
    first_year: int
    last_year: int
    metro_year: pl.DataFrame
    metro_quarter: pl.DataFrame
    brackets: pl.DataFrame
    loans_year: pl.DataFrame
    rates: pl.DataFrame
    truth: Truth


N_METROS = 60
FIRST_YEAR = 2005
LAST_YEAR = 2024
RATE_SHOCK_YEAR = 2022
LOCK_IN_RESPONSE = 0.04  # purchases per 100 owner households lost per point of lock in share after the shock
BETA_SUPPLY = 0.025  # log price growth per permit per hundred new households, one window lagged
BURDEN_STEP_YEAR = 2013
BURDEN_STEP_SIZE = 0.03
BASE_RENT_TO_PRICE = 0.058
SUPPRESSION_THRESHOLD = 50


def rate_path(first_year: int, last_year: int) -> pl.DataFrame:
    """A stylised thirty year rate: around six percent, falling to three in 2020 and 2021, seven from 2023."""
    rows = []
    for year in range(first_year, last_year + 1):
        for q in range(1, 5):
            if year <= 2008:
                rate = 6.2 - 0.05 * (year - first_year)
            elif year <= 2012:
                rate = 5.0 - 0.3 * (year - 2008)
            elif year <= 2019:
                rate = 3.9 + 0.12 * ((year - 2013) % 4)
            elif year == 2020:
                rate = 3.3 - 0.15 * q
            elif year == 2021:
                rate = 2.9 + 0.05 * q
            elif year == 2022:
                rate = 3.5 + 0.8 * q
            else:
                rate = 6.8 + 0.1 * ((year + q) % 3)
            rows.append({"year": year, "quarter": q, "period": f"{year}Q{q}", "rate": round(rate, 2)})
    return pl.DataFrame(rows)


def generate(condition: Condition, seed: int, *, n_metros: int = N_METROS) -> World:
    k = condition.knobs()
    g_metro = rng(seed, "metros", condition.name)
    g_year = rng(seed, "years", condition.name)
    years = list(range(FIRST_YEAR, LAST_YEAR + 1))
    n_years = len(years)

    # Metro characteristics. Price level and income are given a positive correlation on purpose: the
    # expensive metros are the rich ones, so a price ranking is not an affordability ranking.
    size = np.exp(g_metro.normal(12.3, 0.9, n_metros))  # households
    latent = g_metro.normal(0.0, 1.0, n_metros)
    income0 = 55_000.0 * np.exp(0.22 * latent + g_metro.normal(0.0, 0.08, n_metros))
    price0 = 3.6 * income0 * np.exp(0.35 * latent + g_metro.normal(0.0, 0.12, n_metros))
    sigma = np.clip(g_metro.normal(0.72, 0.05, n_metros), 0.55, 0.9)
    elasticity = np.clip(g_metro.normal(1.0, k["elasticity_sd"], n_metros), 0.05, 3.0)
    value_bias = np.exp(g_metro.normal(0.0, 0.06, n_metros))  # self reported value over the true one
    income_growth = g_metro.normal(0.028, 0.006, n_metros)
    base_migration = g_metro.normal(0.0, 0.6, n_metros)  # per 100 residents per year
    base_permits = np.clip(g_metro.normal(1.0, 0.25, n_metros), 0.3, 2.0)  # per hundred new households
    rent_to_price = BASE_RENT_TO_PRICE * np.exp(g_metro.normal(0.0, 0.08, n_metros))
    renter_share = np.clip(g_metro.normal(0.36, 0.06, n_metros), 0.2, 0.6)
    base_turnover = np.clip(g_metro.normal(5.5, 0.8, n_metros), 3.0, 9.0)  # purchases per 100 owner households
    low_rate_buying = np.clip(g_metro.normal(1.0, 0.25, n_metros), 0.4, 1.8)  # how much a metro bought in 2019 to 2021

    rates = rate_path(FIRST_YEAR, LAST_YEAR)
    annual_rate = rates.group_by("year").agg(pl.col("rate").mean()).sort("year")["rate"].to_numpy()

    log_price = np.log(price0)
    income = income0.copy()
    households = size.copy()
    population = households * 2.5
    migration = np.zeros(n_metros)
    permits = base_permits.copy()
    permits_prev = base_permits.copy()
    last_growth = np.zeros(n_metros)
    metro_rows: list[dict[str, object]] = []
    quarter_rows: list[dict[str, object]] = []
    bracket_rows: list[dict[str, object]] = []
    loans_rows: list[dict[str, object]] = []
    held_low_share = np.zeros(n_metros)
    affordability_gap = np.zeros(n_metros)

    for t, year in enumerate(years):
        shock_t = 1.0 if year >= 2020 and year <= 2021 else 0.0
        national_pull = g_year.normal(0.0, 0.5)
        # Migration: an exogenous draw, a national pull in the pandemic years, and under reverse causality a
        # response to last year's affordability gap (cheaper metros gain people).
        migration = (
            base_migration
            + 1.2 * shock_t * g_metro.normal(0.0, 1.0, n_metros)
            + national_pull
            - k["reverse"] * affordability_gap
            + g_metro.normal(0.0, 0.3, n_metros)
        )
        # Permits respond to last year's price growth with the metro's elasticity.
        permits = np.clip(base_permits * (1.0 + elasticity * last_growth / 0.04), 0.05, None)
        # Price growth: income growth passes through, demand pushes, lagged permits pull down.
        permits_lag = permits_prev
        growth = (
            1.0 * income_growth
            + 0.012
            + k["beta_demand"] * migration
            - BETA_SUPPLY * (permits_lag - base_permits.mean())
            + g_metro.normal(0.0, k["noise_sd"], n_metros)
        )
        if year in (2008, 2009, 2010):
            growth -= 0.06
        if year in (2021, 2022):
            growth += 0.05
        log_price = log_price + growth
        last_growth = growth
        permits_prev = permits
        income = income * (1.0 + income_growth + g_metro.normal(0.0, 0.004, n_metros))
        households = households * (1.0 + 0.006 + migration / 100.0)
        population = households * 2.5
        price = np.exp(log_price)
        rate = float(annual_rate[t])
        share = np.array([payment_share(p, i, rate, 0.10, 30) for p, i in zip(price, income, strict=True)])
        affordability_gap = (share - share.mean()) / share.std() if share.std() > 0 else np.zeros(n_metros)
        rent = rent_to_price * price / 12.0 * np.exp(g_metro.normal(0.0, 0.02, n_metros))
        mu = np.log(income)
        renter_mu = mu - 0.45
        step = BURDEN_STEP_SIZE if year >= BURDEN_STEP_YEAR else 0.0
        for i in range(n_metros):
            metro_id = f"S{i + 1:03d}"
            hh = float(households[i])
            renters = hh * renter_share[i]
            owners = hh - renters
            # Burden shares from the renter income distribution: rent at or above 30 and 50 percent of income.
            annual_rent = float(rent[i]) * 12.0
            burdened = 1.0 - exact_share_above_lognormal(annual_rent / 0.30, renter_mu[i], sigma[i]) + step
            severe = 1.0 - exact_share_above_lognormal(annual_rent / 0.50, renter_mu[i], sigma[i]) + step
            burdened = float(np.clip(burdened, 0.0, 1.0))
            severe = float(np.clip(min(severe, burdened), 0.0, 1.0))
            moe_income = float(income[i]) * (0.02 + 0.04 * (20_000 / max(hh, 20_000)) ** 0.5)
            moe_value = float(price[i]) * 0.025
            metro_rows.append(
                {
                    "metro_id": metro_id,
                    "metro_name": f"Simulated metro {i + 1}",
                    "year": year,
                    "households": hh,
                    "owner_households": owners,
                    "renter_households": renters,
                    "population": float(population[i]),
                    "median_income_true": float(income[i]),
                    "median_income": float(income[i] + g_metro.normal(0.0, moe_income / 1.645)),
                    "median_income_moe": moe_income,
                    "renter_median_income": float(np.exp(renter_mu[i])),
                    "median_value_true": float(price[i]),
                    "median_value_reported": float(price[i] * value_bias[i] + g_metro.normal(0.0, moe_value / 1.645)),
                    "median_value_moe": moe_value,
                    "median_rent": float(rent[i]),
                    "rent_burdened_share": burdened,
                    "rent_severe_share": severe,
                    "permits_per_100_new_households": float(permits[i]),
                    "permits": float(permits[i] * hh * 0.006),
                    "domestic_migration_per_100": float(migration[i]),
                    "rate": rate,
                    "payment_share_true": float(share[i]),
                    "income_sigma": float(sigma[i]),
                }
            )
            counts = lognormal_bracket_counts(float(mu[i]), float(sigma[i]), hh)
            for b, count in enumerate(counts):
                reported = count if count >= SUPPRESSION_THRESHOLD else None
                bracket_rows.append(
                    {"metro_id": metro_id, "year": year, "bracket": b, "households": reported, "households_true": count}
                )
            # Loans: purchases per 100 owner households fall with the lock in share after the shock.
            lock_in = held_low_share[i]
            after = 1.0 if year >= 2023 else 0.0
            turnover = base_turnover[i] - LOCK_IN_RESPONSE * (lock_in * 100.0) * after
            turnover += g_metro.normal(0.0, 0.25)
            turnover = float(max(turnover, 0.3))
            purchases = turnover / 100.0 * owners
            refis = owners * (0.14 if year in (2020, 2021) else 0.04 if year in (2012, 2019) else 0.02)
            loans_rows.append(
                {
                    "metro_id": metro_id,
                    "year": year,
                    "purchase_loans": float(purchases),
                    "refinance_loans": float(refis),
                    "rate_at_origination": rate,
                    "owner_households": owners,
                    "turnover_per_100": turnover,
                    "lock_in_share_true": float(lock_in),
                    "borrower_income_ratio": float(1.35 + 0.08 * after + g_metro.normal(0.0, 0.03)),
                }
            )
            # Owners who bought at a low rate: originations of 2019 to 2021 under four percent per 100 owners.
            if year in (2019, 2020, 2021) and rate < 4.0:
                held_low_share[i] += (purchases + refis) * low_rate_buying[i] / owners
        for q in range(1, 5):
            qrate = float(rates.filter((pl.col("year") == year) & (pl.col("quarter") == q))["rate"][0])
            frac = (q - 2.5) / 4.0
            for i in range(n_metros):
                p_q = float(np.exp(log_price[i] + frac * last_growth[i]))
                quarter_rows.append(
                    {
                        "metro_id": f"S{i + 1:03d}",
                        "year": year,
                        "quarter": q,
                        "period": f"{year}Q{q}",
                        "value_true": p_q,
                        "index": p_q / float(price0[i]) * 100.0,
                        "rate": qrate,
                    }
                )

    metros = pl.DataFrame(
        {
            "metro_id": [f"S{i + 1:03d}" for i in range(n_metros)],
            "elasticity": elasticity,
            "value_bias": value_bias,
            "income_sigma": sigma,
            "base_turnover": base_turnover,
            "rent_to_price": rent_to_price,
        }
    )
    truth = Truth(
        beta_supply=BETA_SUPPLY,
        beta_demand=k["beta_demand"],
        reverse=k["reverse"],
        lock_in_response=LOCK_IN_RESPONSE,
        burden_step_year=BURDEN_STEP_YEAR,
        burden_step_size=BURDEN_STEP_SIZE,
        rate_shock_year=RATE_SHOCK_YEAR,
        metros=metros,
    )
    return World(
        condition=condition,
        seed=seed,
        first_year=FIRST_YEAR,
        last_year=LAST_YEAR,
        metro_year=pl.DataFrame(metro_rows).sort(["metro_id", "year"]),
        metro_quarter=pl.DataFrame(quarter_rows).sort(["metro_id", "year", "quarter"]),
        brackets=pl.DataFrame(bracket_rows, schema_overrides={"households": pl.Float64}).sort(["metro_id", "year", "bracket"]),
        loans_year=pl.DataFrame(loans_rows).sort(["metro_id", "year"]),
        rates=rates,
        truth=truth,
    )


def bracket_bounds() -> list[int]:
    return list(INCOME_BRACKETS)
