"""Known truth tests on the simulator: under the clean condition (no price noise, no reverse causality) every
estimator recovers what the generator planted, within a stated tolerance, and the generator itself is
deterministic in its seed. The recovery study, not these tests, grades the estimators under noise."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest
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
from doorstep_chapters.panel import from_world
from doorstep_sim.lenders import lender_loans
from doorstep_sim.metros import DEMONSTRATION, Condition, burden_by_income, conditions, generate

CLEAN = Condition(
    name="clean", demand_strength="strong", supply_dispersion="narrow", reverse_causality="none", noise="none"
)


@pytest.fixture(scope="module")
def world():  # type: ignore[no-untyped-def]
    return generate(CLEAN, 3)


def test_generator_is_deterministic_in_its_seed() -> None:
    a = generate(CLEAN, 1)
    b = generate(CLEAN, 1)
    c = generate(CLEAN, 2)
    assert a.metro_year.equals(b.metro_year)
    assert not a.metro_year.equals(c.metro_year)
    assert len(conditions()) == 24


def test_world_shape_and_planted_defects(world) -> None:  # type: ignore[no-untyped-def]
    my = world.metro_year
    assert my["metro_id"].n_unique() == 60
    assert my.filter(pl.col("kind") == "micropolitan")["metro_id"].n_unique() == 6
    assert world.brackets["households"].null_count() > 0  # suppressed cells
    assert (world.truth.metros["value_bias"] != 1.0).any()  # planted self report bias
    assert world.metro_quarter.height == 60 * 20 * 4


def test_annual_price_is_the_mean_of_its_quarters(world) -> None:  # type: ignore[no-untyped-def]
    q = (
        world.metro_quarter.group_by(["metro_id", "year"])
        .agg(pl.col("value_true").mean())
        .sort(["metro_id", "year"])
    )
    m = world.metro_year.select(["metro_id", "year", "median_value_true"]).sort(["metro_id", "year"])
    assert np.allclose(q["value_true"].to_numpy(), m["median_value_true"].to_numpy())


def test_lock_in_recovers_the_planted_response(world) -> None:  # type: ignore[no-untyped-def]
    grades = {g.estimator: g for g in c2_rate_shock.simulate_estimate(world)}
    assert abs(grades["lock_in_did"].error) < 0.012
    assert grades["lock_in_did"].covered


def test_supply_elasticity_recovered_with_the_demand_control(world) -> None:  # type: ignore[no-untyped-def]
    grades = {g.estimator: g for g in c4_supply.simulate_estimate(world)}
    # Within a tenth of the planted value; the residual is the annual index being the mean of its quarters.
    assert abs(grades["supply_controlled"].error) < 0.0025


def test_supply_estimator_attenuates_when_builders_answer_the_growth_they_are_regressed_on() -> None:
    """The caveat the chapter prints: permits respond to price growth inside the window, so under price noise the
    coefficient is pulled toward zero. The recovery study quantifies it by condition; this test pins the direction."""
    noisy = Condition(
        name="noisy", demand_strength="strong", supply_dispersion="narrow", reverse_causality="none", noise="high"
    )
    errors = [
        {g.estimator: g for g in c4_supply.simulate_estimate(generate(noisy, seed))}["supply_controlled"].error
        for seed in range(4)
    ]
    assert np.mean(errors) > 0.0  # toward zero from a negative truth


def test_migration_effect_recovered_and_placebo_near_zero(world) -> None:  # type: ignore[no-untyped-def]
    grades = {g.estimator: g for g in c7_migration.simulate_estimate(world)}
    assert abs(grades["migration_effect"].error) < 0.004
    assert grades["migration_placebo"].covered


def test_adjusted_ranking_beats_the_raw_ranking(world) -> None:  # type: ignore[no-untyped-def]
    grades = {g.estimator: g for g in c5_ranking.simulate_estimate(world, draws=200)}
    adjusted = grades["ranking_adjusted"]
    assert adjusted.estimate > 0.93
    assert adjusted.flag is not None and adjusted.estimate > adjusted.flag
    assert grades["bracket_interpolation"].estimate < 0.005


def test_self_report_correction_recovers_the_planted_factor(world) -> None:  # type: ignore[no-untyped-def]
    grades = {g.estimator: g for g in c1_definition.simulate_estimate(world, draws=200)}
    assert grades["self_report_correction"].flag is not None and grades["self_report_correction"].flag < 0.03
    assert abs(grades["anchored_level"].error) < 0.02
    # The Monte Carlo interval carries the survey margins, not the planted self report bias, so it is not asked
    # to cover the truth here; the recovery study reports its coverage and the chapter's pushback says why.
    assert abs(grades["anchored_payment_share"].error) < 0.01


def test_changepoint_found_at_the_planted_year(world) -> None:  # type: ignore[no-untyped-def]
    grades = {g.estimator: g for g in c3_burden.simulate_estimate(world)}
    assert grades["burden_changepoint"].flag == 1.0


def test_borrower_pool_shift_recovered(world) -> None:  # type: ignore[no-untyped-def]
    grades = {g.estimator: g for g in c6_buyers.simulate_estimate(world, replicates=60)}
    assert abs(grades["borrower_ratio_shift"].error) < 0.02
    assert abs(grades["under_35_shift"].error) < 0.02


def test_breakeven_graded_as_late_arriving_truth(world) -> None:  # type: ignore[no-untyped-def]
    grades = {g.estimator: g for g in c8_decision.simulate_estimate(world, draws=50)}
    assert np.isfinite(grades["breakeven_horizon"].estimate)
    assert grades["breakeven_horizon"].flag is not None


def test_lender_loans_have_the_planted_income_ratio(world) -> None:  # type: ignore[no-untyped-def]
    loans = lender_loans(world, scale=0.1)
    assert set(loans.columns) >= {
        "year",
        "cbsa_code",
        "lei",
        "income_k",
        "under_35",
        "value_to_income",
        "rate_spread",
    }
    assert loans["lei"].n_unique() == 12
    assert int(loans["year"].min()) == 2018


def test_burden_by_income_groups_are_consistent(world) -> None:  # type: ignore[no-untyped-def]
    b = burden_by_income(world)
    assert (b["renters_severe"] <= b["renters_burdened"] + 1e-9).all()
    assert (b["renters_burdened"] <= b["renters_with_share"] + 1e-9).all()
    assert b["group_order"].max() == 7


def test_panel_from_world_anchors_like_the_warehouse(world) -> None:  # type: ignore[no-untyped-def]
    panel = from_world(world)
    anchor = panel.metro_year.filter(pl.col("year") == panel.anchor_year)
    assert np.allclose(anchor["value_anchored"].to_numpy(), anchor["value_reported"].to_numpy())
    assert (
        panel.metro_year.filter(pl.col("year") == 2020).height == 60
    )  # the simulator has no census gap; the warehouse carries it
    other = panel.with_anchor(2017)
    assert other.anchor_year == 2017


def test_demonstration_condition_is_one_of_the_study_cells() -> None:
    assert DEMONSTRATION.knobs()["reverse"] == 0.6
