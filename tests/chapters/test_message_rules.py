"""Every message rule has a branch for every outcome, including the null, and a test per branch. The
rules take intervals and coefficients, so each branch is reached with values built for it."""

from __future__ import annotations

from doorstep_chapters import (
    c1_definition,
    c2_rate_shock,
    c3_burden,
    c4_supply,
    c5_ranking,
    c6_buyers,
    c7_migration,
    c8_decision,
)
from doorstep_stats.bootstrap import Interval
from doorstep_stats.regression import Coefficient


def coef(estimate: float, low: float, high: float) -> Coefficient:
    return Coefficient("x", estimate, (high - low) / 4.0, low, high, 0.5, 15, 100)


def interval(estimate: float, low: float, high: float) -> Interval:
    return Interval(estimate, low, high, 100, 60)


# Chapter 1


def test_definition_branches() -> None:
    assert c1_definition.message_rule(0.01, 0.03, None, 2024, 0.02).name == "exceeds"
    assert c1_definition.message_rule(-0.03, -0.01, None, 2024, -0.02).name == "below_2006"
    assert c1_definition.message_rule(-0.01, 0.01, None, 2024, 0.0).name == "null"
    fails = c1_definition.message_rule(0.01, 0.03, 2007, 2024, 0.02)
    assert fails.name == "fails_year" and "2007" in fails.text


# Chapter 2


def test_rate_shock_branches() -> None:
    froze = c2_rate_shock.message_rule(coef(-0.05, -0.08, -0.02), coef(0.0, -0.02, 0.02), "2022Q3")
    assert froze.name == "froze" and "2022Q3" in froze.text
    assert c2_rate_shock.message_rule(coef(-0.05, -0.08, -0.02), coef(0.03, 0.01, 0.05), "2022Q3").name == "pre_trend"
    assert c2_rate_shock.message_rule(coef(0.05, 0.02, 0.08), coef(0.0, -0.02, 0.02), "2022Q3").name == "reverse"
    null = c2_rate_shock.message_rule(coef(-0.01, -0.05, 0.03), coef(0.0, -0.02, 0.02), None)
    assert null.name == "null" and "never overtook" in null.text


# Chapter 3


def test_burden_branches() -> None:
    severe_high = interval(0.25, 0.23, 0.27)
    assert c3_burden.message_rule(0.8, severe_high, 0.20, 2024, [2013]).name == "median_hides"
    assert c3_burden.message_rule(0.3, severe_high, 0.20, 2024, []).name == "median_burdened"
    assert c3_burden.message_rule(0.8, interval(0.20, 0.18, 0.22), 0.20, 2024, []).name == "at_line"
    assert c3_burden.message_rule(0.8, interval(0.15, 0.13, 0.17), 0.20, 2024, []).name == "below_line"
    assert "no changepoint" in c3_burden.message_rule(0.8, severe_high, 0.20, 2024, []).text


# Chapter 4


def test_supply_branches() -> None:
    kept = c4_supply.message_rule(coef(-0.02, -0.03, -0.01), coef(-0.015, -0.025, -0.005), 5)
    assert kept.name == "kept_pace" and "without the demand control" in kept.text
    assert c4_supply.message_rule(coef(0.02, 0.01, 0.03), coef(0.015, 0.005, 0.025), 5).name == "demand_dominates"
    assert c4_supply.message_rule(coef(0.0, -0.01, 0.01), coef(0.0, -0.01, 0.01), 5).name == "null"


# Chapter 5


def test_ranking_branches() -> None:
    changed = c5_ranking.message_rule(3, 20, [("A", 10, 4)], [("B", 2, 9)], 0.9)
    assert changed.name == "changes" and "A from 10 to 4" in changed.text and "B from 2 to 9" in changed.text
    assert c5_ranking.message_rule(0, 20, [], [], 0.99).name == "unchanged"


# Chapter 6


def test_buyers_branches() -> None:
    richer = interval(0.08, 0.06, 0.10)
    flat_ratio = interval(0.0, -0.02, 0.02)
    older = interval(-0.03, -0.05, -0.01)
    flat_age = interval(0.0, -0.01, 0.01)
    assert c6_buyers.message_rule(richer, older, 2024, [("A", 0.2)]).name == "richer_older"
    assert c6_buyers.message_rule(richer, flat_age, 2024, []).name == "richer"
    assert c6_buyers.message_rule(flat_ratio, older, 2024, []).name == "older"
    assert c6_buyers.message_rule(flat_ratio, flat_age, 2024, []).name == "null"


# Chapter 7


def test_migration_branches() -> None:
    main = coef(0.015, 0.010, 0.020)
    assert c7_migration.message_rule(main, coef(0.0, -0.004, 0.004)).name == "prices_followed"
    rising = c7_migration.message_rule(main, coef(0.006, 0.002, 0.010))
    assert rising.name == "already_rising" and "upper bound" in rising.text and "already rising" in rising.text
    lagging = c7_migration.message_rule(main, coef(-0.006, -0.010, -0.002))
    assert lagging.name == "already_rising" and "lower bound" in lagging.text
    assert c7_migration.message_rule(coef(0.002, -0.004, 0.008), coef(0.0, -0.004, 0.004)).name == "null"


# Chapter 8


def test_decision_branches() -> None:
    biggest = [("A", 31.0), ("B", 12.0)]
    never = c8_decision.message_rule(31.0, 20.0, 31.0, 0.7, 30, 4.0, biggest)
    assert never.name == "never" and "beyond 30 years" in never.text
    assert c8_decision.message_rule(1.5, 1.0, 3.0, 0.0, 30, 2.0, biggest).name == "immediate"
    years = c8_decision.message_rule(12.0, 6.0, 20.0, 0.1, 30, 3.5, biggest)
    assert years.name == "years" and "12.0 years" in years.text
