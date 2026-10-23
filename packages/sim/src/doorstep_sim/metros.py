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
    noise: str  # "low" or "high" in the study; "none" for the known truth tests

    def knobs(self) -> dict[str, float]:
        return {
            "beta_demand": {"weak": 0.004, "strong": 0.012}[self.demand_strength],
            "elasticity_sd": {"narrow": 0.10, "wide": 0.40}[self.supply_dispersion],
            "reverse": {"none": 0.0, "mild": 0.6, "strong": 1.8}[self.reverse_causality],
            "noise_sd": {"none": 0.0, "low": 0.010, "high": 0.030}[self.noise],
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
    borrower_ratio_shift: float
    metros: pl.DataFrame  # per metro: state, kind, elasticity, value_bias, income sigma, base turnover


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
N_STATES = 15
N_MICROPOLITAN = (
    6  # the last metros are micropolitan areas, carried in the warehouse and excluded from the ranking
)
FIRST_YEAR = 2005
LAST_YEAR = 2024
RATE_SHOCK_YEAR = 2022
LOCK_IN_RESPONSE = 0.04  # purchases per 100 owner households lost per point of lock in share after the shock
BETA_SUPPLY = 0.025  # log price growth per permit per hundred households, lagged one year
PERMIT_RESPONSE_MIGRATION = 0.30  # building rate response per person per hundred residents arrived last year, at unit elasticity
PERMIT_RESPONSE_GROWTH = 0.40  # the growth surprise that moves the building rate by its elasticity (ten percent per four points)
BURDEN_STEP_YEAR = 2013
BURDEN_STEP_SIZE = 0.03
BORROWER_RATIO_BASE = 1.35
BORROWER_RATIO_SHIFT = 0.08  # the buyer pool moves up the income ladder by this much after the shock
BASE_RENT_TO_PRICE = 0.058
SUPPRESSION_THRESHOLD = 50
MEAN_REVERSION = 0.006  # log price growth lost per standard deviation of the affordability gap
SUPPLY_SHOCK_SD = 0.30  # log building rate shock a metro's own land, zoning and costs give it each year
SUPPLY_SHOCK_PERSISTENCE = 0.6
MIGRATION_PERSISTENCE = 0.7  # a metro that gained people this year tends to gain them next year
MIGRATION_INNOVATION_SD = 0.3  # per 100 residents per year


def state_of(i: int) -> str:
    """Synthetic metros are spread over fifteen synthetic states, the clusters for the standard errors."""
    return f"Z{(i % N_STATES) + 1:02d}"


def kind_of(i: int, n_metros: int = N_METROS) -> str:
    return "micropolitan" if i >= n_metros - N_MICROPOLITAN else "metropolitan"


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
    base_turnover = np.clip(
        g_metro.normal(5.5, 0.8, n_metros), 3.0, 9.0
    )  # purchases per 100 owner households
    low_rate_buying = np.clip(
        g_metro.normal(1.0, 0.25, n_metros), 0.4, 1.8
    )  # how much a metro bought in 2019 to 2021

    rates = rate_path(FIRST_YEAR, LAST_YEAR)
    annual_rate = rates.group_by("year").agg(pl.col("rate").mean()).sort("year")["rate"].to_numpy()

    log_price = np.log(price0)
    income = income0.copy()
    households = size.copy()
    population = households * 2.5
    migration = np.zeros(n_metros)
    migration_prev = np.zeros(n_metros)
    permits = base_permits.copy()
    permits_prev = base_permits.copy()
    last_growth = np.zeros(n_metros)
    metro_rows: list[dict[str, object]] = []
    quarter_rows: list[dict[str, object]] = []
    bracket_rows: list[dict[str, object]] = []
    loans_rows: list[dict[str, object]] = []
    held_low_share = np.zeros(n_metros)
    affordability_gap = np.zeros(n_metros)
    households_prev = households.copy()
    supply_shock = g_metro.normal(0.0, SUPPLY_SHOCK_SD, n_metros)
    migration_swing = g_metro.normal(0.0, MIGRATION_INNOVATION_SD, n_metros)
    gap_history: list[np.ndarray] = []
    gap_lagged = np.zeros(n_metros)  # the affordability gap two years ago: a move answers the gap with a lag
    gap_lagged_change = np.zeros(n_metros)  # how that gap had moved over the two years before it

    for t, year in enumerate(years):
        shock_t = 1.0 if year >= 2020 and year <= 2021 else 0.0
        national_pull = g_year.normal(0.0, 0.5)
        # Migration: a metro level, a persistent swing (booms last several years, which is what makes the demand
        # shock a confounder for the supply chapter: a metro's building rate and its price growth rise together
        # while people arrive), a national pull, the pandemic draw, and under reverse causality a response to the
        # affordability gap two years back: people leave the metros that are expensive for their incomes and, more
        # so, the metros that had just become expensive. The lag is what a move takes, and it is what gives the
        # pre trend placebo its power: the metros people are leaving were already growing more slowly.
        migration_swing = MIGRATION_PERSISTENCE * migration_swing + g_metro.normal(
            0.0, MIGRATION_INNOVATION_SD, n_metros
        )
        migration = (
            base_migration
            + migration_swing
            + 1.2 * shock_t * g_metro.normal(0.0, 1.0, n_metros)
            + national_pull
            - k["reverse"] * (1.0 * gap_lagged + 0.5 * gap_lagged_change)
        )
        # Permits follow demand: builders build where people arrived last year (the demand shock the supply chapter
        # must control for; a permit follows the inflow it answers by about a year) and, weakly, where prices just
        # rose; both scaled by the metro's elasticity, around a persistent supply shock of their own (land, zoning,
        # costs) that gives the building rate the variation demand did not cause.
        supply_shock = SUPPLY_SHOCK_PERSISTENCE * supply_shock + g_metro.normal(
            0.0, SUPPLY_SHOCK_SD, n_metros
        )
        permits = np.clip(
            base_permits
            * (
                1.0
                + elasticity
                * (PERMIT_RESPONSE_MIGRATION * migration_prev + last_growth / PERMIT_RESPONSE_GROWTH)
            )
            * np.exp(supply_shock),
            0.05,
            None,
        )
        # Price growth: income growth passes through, demand pushes, lagged permits pull down.
        permits_lag = permits_prev
        # Price growth: income growth passes through, demand pushes, lagged permits pull down, and a metro that
        # has run ahead of its incomes (a high affordability gap) grows more slowly, which is the channel through
        # which reverse causality confounds the migration chapter: the same gap sends people away.
        growth = (
            1.0 * income_growth
            + 0.012
            + k["beta_demand"] * migration
            - BETA_SUPPLY * (permits_lag - base_permits.mean())
            - MEAN_REVERSION * affordability_gap
            + g_metro.normal(0.0, k["noise_sd"], n_metros)
        )
        if year in (2008, 2009, 2010):
            growth -= 0.06
        if year in (2021, 2022):
            growth += 0.05
        log_price_prev = log_price.copy()
        log_price = log_price + growth
        last_growth = growth
        permits_prev = permits
        migration_prev = migration.copy()
        income = income * (1.0 + income_growth + g_metro.normal(0.0, 0.004, n_metros))
        households_prev = households.copy()
        households = households * (1.0 + 0.006 + migration / 100.0)
        population = households * 2.5
        new_households = households - households_prev
        # The year's growth arrives in four equal quarterly steps from last year's end, so the fourth quarter is
        # the end of year level and a fourth quarter to fourth quarter difference is exactly the years' growth.
        # The year's price is the mean of its four quarters, as an annual index average is, so the truth the
        # chapters are graded against sits at the grain the census survey year sits at.
        quarter_prices = np.exp(log_price_prev[None, :] + np.arange(1, 5)[:, None] / 4.0 * growth[None, :])
        price = quarter_prices.mean(axis=0)
        rate = float(annual_rate[t])
        share = np.array([payment_share(p, i, rate, 0.10, 30) for p, i in zip(price, income, strict=True)])
        affordability_gap = (share - share.mean()) / share.std() if share.std() > 0 else np.zeros(n_metros)
        gap_history.append(affordability_gap)
        gap_lagged = gap_history[-2] if len(gap_history) >= 2 else gap_history[0]
        gap_lagged_change = gap_lagged - (gap_history[-4] if len(gap_history) >= 4 else gap_history[0])
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
                    "state": state_of(i),
                    "kind": kind_of(i, n_metros),
                    "year": year,
                    "households": hh,
                    "new_households": float(new_households[i]),
                    "owner_households": owners,
                    "renter_households": renters,
                    "population": float(population[i]),
                    "median_income_true": float(income[i]),
                    "median_income": float(income[i] + g_metro.normal(0.0, moe_income / 1.645)),
                    "median_income_moe": moe_income,
                    "renter_median_income": float(np.exp(renter_mu[i])),
                    "median_value_true": float(price[i]),
                    "median_value_reported": float(
                        price[i] * value_bias[i] + g_metro.normal(0.0, moe_value / 1.645)
                    ),
                    "median_value_moe": moe_value,
                    "median_rent": float(rent[i]),
                    "rent_burdened_share": burdened,
                    "rent_severe_share": severe,
                    "permits_per_100_households": float(permits[i]),
                    "permits": float(permits[i] / 100.0 * hh),
                    "permits_per_100_new_households": (
                        float(permits[i] / 100.0 * hh / new_households[i] * 100.0)
                        if new_households[i] > 0
                        else None
                    ),
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
                    {
                        "metro_id": metro_id,
                        "year": year,
                        "bracket": b,
                        "households": reported,
                        "households_true": count,
                    }
                )
            # Loans: purchases per 100 owner households fall with the lock in share after the shock.
            lock_in = held_low_share[i]
            after = 1.0 if year >= 2023 else 0.0
            turnover = base_turnover[i] - LOCK_IN_RESPONSE * (lock_in * 100.0) * after
            turnover += g_metro.normal(0.0, 0.25)
            turnover = float(max(turnover, 0.3))
            purchases = turnover / 100.0 * owners
            refis = owners * (0.14 if year in (2020, 2021) else 0.04 if year in (2012, 2019) else 0.02)
            # Originations written at a rate under four percent: the whole year's book when the year's rate is
            # under four, scaled by how much the metro borrowed at the bottom, else none.
            low_rate = (
                (purchases + refis) * low_rate_buying[i]
                if (year in (2019, 2020, 2021) and rate < 4.0)
                else 0.0
            )
            ratio_true = BORROWER_RATIO_BASE + BORROWER_RATIO_SHIFT * after
            loans_rows.append(
                {
                    "metro_id": metro_id,
                    "state": state_of(i),
                    "year": year,
                    "purchase_loans": float(purchases),
                    "refinance_loans": float(refis),
                    "low_rate_originations": float(low_rate),
                    "rate_at_origination": rate,
                    "owner_households": owners,
                    "turnover_per_100": turnover,
                    "lock_in_share_true": float(lock_in),
                    "borrower_income_ratio_true": float(ratio_true),
                    "borrower_income_ratio": float(ratio_true + g_metro.normal(0.0, 0.03)),
                    "purchase_median_value": float(price[i] * np.exp(g_metro.normal(0.0, 0.015))),
                }
            )
            # Owners who bought at a low rate: originations of 2019 to 2021 under four percent per 100 owners.
            held_low_share[i] += low_rate / owners
        for q in range(1, 5):
            qrate = float(rates.filter((pl.col("year") == year) & (pl.col("quarter") == q))["rate"][0])
            for i in range(n_metros):
                p_q = float(quarter_prices[q - 1, i])
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
            "state": [state_of(i) for i in range(n_metros)],
            "kind": [kind_of(i, n_metros) for i in range(n_metros)],
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
        borrower_ratio_shift=BORROWER_RATIO_SHIFT,
        metros=metros,
    )
    return World(
        condition=condition,
        seed=seed,
        first_year=FIRST_YEAR,
        last_year=LAST_YEAR,
        metro_year=pl.DataFrame(metro_rows).sort(["metro_id", "year"]),
        metro_quarter=pl.DataFrame(quarter_rows).sort(["metro_id", "year", "quarter"]),
        brackets=pl.DataFrame(bracket_rows, schema_overrides={"households": pl.Float64}).sort(
            ["metro_id", "year", "bracket"]
        ),
        loans_year=pl.DataFrame(loans_rows).sort(["metro_id", "year"]),
        rates=rates,
        truth=truth,
    )


def bracket_bounds() -> list[int]:
    return list(INCOME_BRACKETS)


# The renter cost burden by household income group, as table B25074 reports it: seven income groups, the
# renters in each whose rent takes thirty percent or more and fifty percent or more of income. Computed
# exactly from the metro's known log normal renter income distribution, so chapter 3's bracket shares have
# a truth to be graded against.

INCOME_GROUPS: tuple[tuple[str, float, float | None], ...] = (
    ("under_10k", 0.0, 10_000.0),
    ("10k_to_20k", 10_000.0, 20_000.0),
    ("20k_to_35k", 20_000.0, 35_000.0),
    ("35k_to_50k", 35_000.0, 50_000.0),
    ("50k_to_75k", 50_000.0, 75_000.0),
    ("75k_to_100k", 75_000.0, 100_000.0),
    ("100k_plus", 100_000.0, None),
)


def burden_by_income(w: World) -> pl.DataFrame:
    """One row per metro, year and income group with the renters, the burdened and the severely burdened."""
    from math import erf, log, sqrt

    def cdf(x: float, mu: float, sigma: float) -> float:
        if x <= 0:
            return 0.0
        return 0.5 * (1.0 + erf((log(x) - mu) / (sigma * sqrt(2.0))))

    rows: list[dict[str, object]] = []
    for r in w.metro_year.iter_rows(named=True):
        mu = log(float(r["renter_median_income"]))
        sigma = float(r["income_sigma"])
        renters = float(r["renter_households"]) * 0.97
        annual_rent = float(r["median_rent"]) * 12.0
        step = w.truth.burden_step_size if int(r["year"]) >= w.truth.burden_step_year else 0.0
        for order, (name, lo, hi) in enumerate(INCOME_GROUPS, start=1):
            p_lo = cdf(lo, mu, sigma)
            p_hi = cdf(hi, mu, sigma) if hi is not None else 1.0
            mass = max(p_hi - p_lo, 1e-12)
            # burdened when income <= rent / 0.30, severe when income <= rent / 0.50, inside the group
            b_cut = min(annual_rent / 0.30, hi) if hi is not None else annual_rent / 0.30
            s_cut = min(annual_rent / 0.50, hi) if hi is not None else annual_rent / 0.50
            burdened = max(cdf(b_cut, mu, sigma) - p_lo, 0.0) / mass if b_cut > lo else 0.0
            severe = max(cdf(s_cut, mu, sigma) - p_lo, 0.0) / mass if s_cut > lo else 0.0
            burdened = min(burdened + step, 1.0)
            severe = min(severe + step, burdened)
            count = renters * mass
            rows.append(
                {
                    "year": int(r["year"]),
                    "metro_id": str(r["metro_id"]),
                    "income_group": name,
                    "group_order": order,
                    "renters_with_share": count,
                    "renters_burdened": count * burdened,
                    "renters_severe": count * severe,
                }
            )
    return pl.DataFrame(rows).sort(["year", "metro_id", "group_order"])
