"""The finance engine against closed forms and hand computed cases, to the cent."""

from __future__ import annotations

import math

import pytest
from doorstep_finance import (
    FinanceError,
    affordable_price,
    balance_after,
    down_payment_years,
    income_needed,
    payment,
    payment_share,
    principal_for_payment,
    schedule,
)
from doorstep_finance.brackets import (
    exact_share_above_lognormal,
    interpolation_error,
    lognormal_bracket_counts,
    median_from_brackets,
    quantile_from_brackets,
    share_above,
)
from doorstep_finance.breakeven import CostModel, breakeven
from hypothesis import given, settings
from hypothesis import strategies as st


def test_payment_matches_a_bank_calculator_to_the_cent() -> None:
    # $300,000 at 6.5 percent over 30 years: the figure every amortisation calculator prints.
    assert round(payment(300_000, 6.5, 30), 2) == 1896.20
    # $200,000 at 3 percent over 15 years.
    assert round(payment(200_000, 3.0, 15), 2) == 1381.16


def test_zero_rate_is_straight_line() -> None:
    assert payment(120_000, 0.0, 10) == pytest.approx(1000.0)


def test_schedule_sums_to_the_principal_and_ends_at_zero() -> None:
    rows = schedule(250_000, 7.0, 30)
    assert len(rows) == 360
    assert round(sum(r.principal for r in rows), 2) == 250_000.00
    assert rows[-1].balance == 0.0
    assert round(rows[0].interest, 2) == round(250_000 * 0.07 / 12, 2)


def test_balance_after_matches_the_schedule() -> None:
    rows = schedule(250_000, 7.0, 30)
    for months in (1, 12, 120, 359):
        assert balance_after(250_000, 7.0, 30, months) == pytest.approx(rows[months - 1].balance, abs=0.01)


def test_affordable_price_inverts_the_payment_share() -> None:
    price = affordable_price(90_000, 6.5, 0.10, 30, 0.30)
    assert payment_share(price, 90_000, 6.5, 0.10, 30) == pytest.approx(0.30, abs=1e-12)
    assert round(income_needed(price, 6.5, 0.10, 30, 0.30), 2) == 90_000.00


def test_principal_for_payment_is_the_inverse_of_payment() -> None:
    assert principal_for_payment(payment(312_345.67, 5.25, 30), 5.25, 30) == pytest.approx(312_345.67, abs=1e-6)


@given(st.floats(min_value=50_000, max_value=2_000_000), st.floats(min_value=0.5, max_value=12.0))
@settings(max_examples=60)
def test_payment_share_is_monotonic_in_rate_and_price(price: float, rate: float) -> None:
    income = 100_000.0
    assert payment_share(price, income, rate, 0.1, 30) <= payment_share(price * 1.01, income, rate, 0.1, 30)
    assert payment_share(price, income, rate, 0.1, 30) <= payment_share(price, income, rate + 0.25, 0.1, 30)


def test_down_payment_years() -> None:
    assert down_payment_years(400_000, 0.10, 60_000, 0.10) == pytest.approx(400_000 * 0.1 / 6_000)


def test_rejects_nonsense() -> None:
    with pytest.raises(FinanceError):
        payment(-1, 5.0, 30)
    with pytest.raises(FinanceError):
        payment(100, 5.0, 0)
    with pytest.raises(FinanceError):
        affordable_price(0, 5.0, 0.1, 30, 0.3)
    with pytest.raises(FinanceError):
        payment_share(100_000, 50_000, 5.0, 1.0, 30)


def test_bracket_share_is_exact_at_bracket_edges_and_monotonic() -> None:
    counts = lognormal_bracket_counts(11.2, 0.75, 100_000)
    assert share_above(0, counts) == 1.0
    edges = [10_000, 50_000, 200_000]
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        assert share_above(lo, counts) >= share_above(hi, counts)
    # At a bracket edge the share is the exact sum of the brackets above it.
    above_50k = sum(counts[9:]) / sum(counts)
    assert share_above(50_000, counts) == pytest.approx(above_50k, abs=1e-12)


def test_bracket_interpolation_error_is_small_on_a_known_distribution() -> None:
    thresholds = [35_000, 72_500, 110_000, 180_000, 260_000]
    assert interpolation_error(11.2, 0.75, 100_000, thresholds) < 0.01


def test_median_from_brackets_near_the_known_median() -> None:
    mu, sigma = 11.2, 0.75
    counts = lognormal_bracket_counts(mu, sigma, 100_000)
    assert median_from_brackets(counts) == pytest.approx(math.exp(mu), rel=0.03)
    assert quantile_from_brackets(0.9, counts) > quantile_from_brackets(0.5, counts)


def test_exact_share_above_lognormal_matches_the_median() -> None:
    assert exact_share_above_lognormal(math.exp(11.0), 11.0, 0.5) == pytest.approx(0.5)


def test_breakeven_hand_case_and_monotone_in_rate() -> None:
    cost = CostModel()
    r = breakeven(400_000, 24_000, 6.5, 0.10, 30, 30, 0.03, 0.03, cost)
    assert r.horizon == 30
    # Year one: the owner has paid closing costs and faces selling costs, so renting is ahead.
    assert r.years[0].difference > 0
    assert r.breakeven_year is not None and 1 < r.breakeven_year <= 30
    cheaper = breakeven(400_000, 24_000, 4.0, 0.10, 30, 30, 0.03, 0.03, cost)
    assert cheaper.breakeven_year is not None
    assert cheaper.breakeven_year <= r.breakeven_year
    # The difference curve is continuous: no year jumps by more than a year of payments plus rent.
    steps = [abs(b.difference - a.difference) for a, b in zip(r.years[:-1], r.years[1:], strict=True)]
    assert max(steps) < 24_000 + 12 * payment(360_000, 6.5, 30) + 400_000 * 0.03


def test_breakeven_never_when_the_home_loses_value() -> None:
    r = breakeven(400_000, 12_000, 7.5, 0.05, 30, 10, -0.03, 0.0, CostModel())
    assert r.breakeven_year is None
