"""Fixed effects on cells against a row level fit, the cluster robust regression, PELT and synthetic control."""

from __future__ import annotations

import numpy as np
import pytest
from doorstep_stats.fe import fit
from doorstep_stats.pelt import bic_penalty, estimate_sigma, pelt
from doorstep_stats.regression import first, regress
from doorstep_stats.synthetic import SyntheticControlError, placebo_band, simplex_weights, synthetic_control


def test_weighted_cell_fit_reproduces_the_row_level_fit() -> None:
    rng = np.random.default_rng(11)
    n = 4000
    metro = rng.integers(0, 40, n)
    year = rng.integers(0, 6, n)
    x = rng.choice([-1.0, 0.0, 1.0, 2.0], n) + 0.3 * metro / 40
    y = 0.5 * x + 0.1 * metro + 0.2 * year + rng.normal(0, 1, n)
    rows = fit(y, x[:, None], np.ones(n), [metro, year], ["x"])
    # collapse to cells: the mean within (metro, year, x), where x is constant, with counts as weights
    key = np.round(x, 6)
    cells: dict[tuple[int, int, float], list[int]] = {}
    for i in range(n):
        cells.setdefault((int(metro[i]), int(year[i]), float(key[i])), []).append(i)
    cy = np.array([y[idx].mean() for idx in cells.values()])
    cx = np.array([x[idx].mean() for idx in cells.values()])
    cw = np.array([len(idx) for idx in cells.values()], dtype=float)
    cm = np.array([k[0] for k in cells])
    cyr = np.array([k[1] for k in cells])
    cell = fit(cy, cx[:, None], cw, [cm, cyr], ["x"])
    assert cell.coef[0] == pytest.approx(rows.coef[0], abs=1e-9)


def test_cluster_robust_regression_recovers_a_slope_and_counts_clusters() -> None:
    rng = np.random.default_rng(2)
    n = 300
    state = rng.integers(0, 30, n)
    x = rng.normal(0, 1, n)
    y = 2.0 + 0.7 * x + rng.normal(0, 0.5, n) + 0.2 * rng.normal(0, 1, 30)[state]
    coefs = regress(y, x, ["x"], cluster=state)
    c = first(coefs, "x")
    assert c.clusters == 30 and c.covers(0.7) and c.excludes_zero
    with pytest.raises(KeyError):
        first(coefs, "missing")


def test_pelt_finds_a_planted_step() -> None:
    rng = np.random.default_rng(4)
    series = np.concatenate([rng.normal(0.20, 0.003, 9), rng.normal(0.24, 0.003, 11)])
    penalty = bic_penalty(series.size, estimate_sigma(series), n_params=2)
    assert pelt(series, penalty, min_size=3) == [9]


def test_pelt_flat_series_has_no_changepoints() -> None:
    assert pelt(np.full(20, 0.3), 1.0, min_size=3) == []


def test_synthetic_control_recovers_a_convex_combination() -> None:
    rng = np.random.default_rng(8)
    t = 30
    donors = {f"d{i}": np.cumsum(rng.normal(0.01, 0.02, t)) for i in range(6)}
    w = np.array([0.5, 0.3, 0.2, 0.0, 0.0, 0.0])
    treated = sum(w[i] * donors[f"d{i}"] for i in range(6))
    treated = treated + np.concatenate([np.zeros(20), np.full(10, 0.05)])
    series = {"treated": treated, **donors}
    sc = synthetic_control("treated", series, pre_periods=20)
    assert sc.pre_rmspe < 1e-6
    assert sc.post_gap_mean == pytest.approx(0.05, abs=1e-5)
    assert sc.donors_searched == 6 and sc.placebo_gaps.shape == (6, t)
    low, high = placebo_band(sc)
    assert low.shape == (t,) and (low <= high).all()
    top = dict(sc.top_weights(3))
    assert top["d0"] == pytest.approx(0.5, abs=1e-4)


def test_synthetic_control_rejects_bad_inputs() -> None:
    with pytest.raises(SyntheticControlError):
        simplex_weights(np.zeros(3), np.zeros((3, 1)))
    with pytest.raises(SyntheticControlError):
        synthetic_control("a", {"a": np.zeros(5), "b": np.zeros(5), "c": np.zeros(5)}, pre_periods=5)
