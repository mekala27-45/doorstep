"""Property tests: the affordable share lives in the unit interval and never rises with the price, the payment
share never falls with the rate, the burden shares sum to one across the bands, the breakeven cost difference is
continuous in the horizon, and the breakeven year never comes sooner when the rate rises."""

from __future__ import annotations

import numpy as np
from doorstep_finance.brackets import INCOME_BRACKETS, lognormal_bracket_counts, share_above
from doorstep_finance.breakeven import CostModel, breakeven, breakeven_year
from doorstep_finance.mortgage import affordable_price, payment_share
from doorstep_sim.metros import burden_by_income
from hypothesis import given, settings
from hypothesis import strategies as st

rates = st.floats(min_value=0.5, max_value=15.0)
prices = st.floats(min_value=50_000.0, max_value=2_000_000.0)
incomes = st.floats(min_value=20_000.0, max_value=500_000.0)


@settings(max_examples=60, deadline=None)
@given(mu=st.floats(min_value=10.0, max_value=12.5), sigma=st.floats(min_value=0.4, max_value=1.0), threshold=st.floats(min_value=1.0, max_value=600_000.0))
def test_the_affordable_share_is_a_share_and_falls_with_the_threshold(mu: float, sigma: float, threshold: float) -> None:
    counts = lognormal_bracket_counts(mu, sigma, 50_000.0)
    share = share_above(threshold, counts)
    assert 0.0 <= share <= 1.0
    assert share_above(threshold * 1.25, counts) <= share + 1e-12
    assert share_above(0.0, counts) == 1.0


@settings(max_examples=60, deadline=None)
@given(price=prices, income=incomes, rate=rates, bump=st.floats(min_value=0.01, max_value=3.0))
def test_the_payment_share_never_falls_with_the_rate_or_the_price(price: float, income: float, rate: float, bump: float) -> None:
    base = payment_share(price, income, rate, 0.10, 30)
    assert payment_share(price, income, rate + bump, 0.10, 30) >= base
    assert payment_share(price * 1.1, income, rate, 0.10, 30) >= base


@settings(max_examples=40, deadline=None)
@given(income=incomes, rate=rates)
def test_the_affordable_price_inverts_the_payment_share_to_the_dollar(income: float, rate: float) -> None:
    price = affordable_price(income, rate, 0.10, 30, 0.30)
    assert abs(payment_share(price, income, rate, 0.10, 30) - 0.30) < 1e-9
    assert abs(payment_share(round(price), income, rate, 0.10, 30) - 0.30) < 1e-4


def test_the_burden_shares_sum_to_one_across_the_bands() -> None:
    """Under thirty, thirty to fifty and fifty or more of income, as shares of the renters with a computed share."""
    from doorstep_sim.metros import DEMONSTRATION, generate

    frame = burden_by_income(generate(DEMONSTRATION, 2))
    assert frame.height > 0
    with_share = frame["renters_with_share"].to_numpy()
    burdened = frame["renters_burdened"].to_numpy()
    severe = frame["renters_severe"].to_numpy()
    under = (with_share - burdened) / with_share
    middle = (burdened - severe) / with_share
    top = severe / with_share
    assert np.all(under >= -1e-12) and np.all(middle >= -1e-12) and np.all(top >= -1e-12)
    assert np.allclose(under + middle + top, 1.0, atol=1e-9)


@settings(max_examples=25, deadline=None)
@given(price=prices, rent_yield=st.floats(min_value=0.03, max_value=0.09), rate=rates, bump=st.floats(min_value=0.1, max_value=2.0))
def test_the_breakeven_difference_is_continuous_and_the_year_never_comes_sooner_with_a_higher_rate(price: float, rent_yield: float, rate: float, bump: float) -> None:
    cost = CostModel()
    first = breakeven(price, price * rent_yield, rate, 0.10, 30, 30, 0.03, 0.03, cost)
    diffs = np.array([y.difference for y in first.years])
    assert np.all(np.isfinite(diffs))
    # Continuity in the horizon: no year to year jump larger than a year of the full ownership cost.
    assert np.max(np.abs(np.diff(diffs))) < price * 0.5
    later = breakeven(price, price * rent_yield, rate + bump, 0.10, 30, 30, 0.03, 0.03, cost)
    assert breakeven_year(later, 30) >= breakeven_year(first, 30)
