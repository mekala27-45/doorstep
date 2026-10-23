"""The analysis policy: every threshold, window and split the chapters share, stated once.

The policy is a frozen model so it can be hashed into each chapter's pre-registered plan;
changing a threshold after registration changes the plan's hash and fails the gate. Every
operating point here has an interior test: the chapter prints its headline under the
neighbours of the chosen value and the word degenerate when the headline turns at the first one.
"""

from __future__ import annotations

from doorstep_core.model import StrictModel

# The ACS household income brackets of table B19001, upper bounds in dollars; the last is open.
INCOME_BRACKETS: tuple[int, ...] = (
    10_000, 15_000, 20_000, 25_000, 30_000, 35_000, 40_000, 45_000, 50_000,
    60_000, 75_000, 100_000, 125_000, 150_000, 200_000,
)  # fmt: skip

# The rent burden bands of table B25070, as the share of income the rent takes, left closed.
BURDEN_BANDS: tuple[tuple[float, float | None], ...] = (
    (0.0, 0.30),
    (0.30, 0.50),
    (0.50, None),
)

# Neighbours for the interior tests, in the order the pages print them.
AFFORDABLE_LINES: tuple[float, ...] = (0.25, 0.28, 0.30, 0.35)
DOWN_PAYMENT_SHARES: tuple[float, ...] = (0.05, 0.10, 0.20)
ANCHOR_YEARS: tuple[int, ...] = (2015, 2017, 2019, 2023)
LOCK_IN_THRESHOLDS: tuple[float, ...] = (3.0, 3.5, 4.0)
SUPPLY_WINDOWS: tuple[int, ...] = (3, 5, 7)
SAVING_RATES: tuple[float, ...] = (0.05, 0.10, 0.15)
SEVERE_LINES: tuple[float, ...] = (0.15, 0.20, 0.25)


class Policy(StrictModel):
    window_start_year: int = 2000
    acs_first_year: int = 2005
    hmda_first_year: int = 2018
    fit_first_year: int = 2005
    fit_last_year: int = 2019
    test_first_year: int = 2021
    anchor_year: int = 2019
    affordable_line: float = 0.30
    affordable_sensitivity: float = 0.28
    severe_line: float = 0.50
    severe_share_line: float = 0.20
    down_payment_share: float = 0.10
    loan_term_years: int = 30
    saving_rate: float = 0.10
    lock_in_threshold: float = 4.0
    lock_in_years: tuple[int, int] = (2019, 2021)
    turnover_base_years: tuple[int, int] = (2018, 2019)
    turnover_test_first_year: int = 2023
    supply_window_years: int = 5
    migration_years: tuple[int, int] = (2020, 2021)
    migration_pre_years: tuple[int, int] = (2017, 2018)
    migration_window: tuple[str, str] = ("2019Q4", "2021Q4")
    migration_placebo_window: tuple[str, str] = ("2016Q4", "2018Q4")
    synthetic_control_first_period: str = "2015Q1"
    synthetic_control_metros: int = 3
    breakeven_horizon_years: int = 30
    breakeven_cost_model: dict[str, float] = {
        "buy_closing_share": 0.03,
        "sell_closing_share": 0.06,
        "property_tax_share": 0.011,
        "insurance_share": 0.004,
        "maintenance_share": 0.01,
        "pmi_rate_under_20": 0.006,
        "investment_return": 0.045,
        "rent_to_price_default": 0.06,
    }
    bootstrap_replicates: int = 400
    monte_carlo_draws: int = 10_000
    bh_q: float = 0.05
    interval_level: float = 0.95
    min_metro_households: int = 20_000
    largest_metros: int = 20
    seed: int = 20261022


POLICY = Policy()


def is_fit_year(year: int, policy: Policy = POLICY) -> bool:
    return policy.fit_first_year <= year <= policy.fit_last_year


def is_test_year(year: int, policy: Policy = POLICY) -> bool:
    return year >= policy.test_first_year
