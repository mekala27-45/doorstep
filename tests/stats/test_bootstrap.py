"""The block bootstrap, the Monte Carlo propagation, the histogram quantile and Benjamini-Hochberg."""

from __future__ import annotations

import numpy as np
import pytest
from doorstep_stats.bootstrap import (
    block_bootstrap,
    histogram_quantile,
    percentile_interval,
    ratio,
    resample_blocks,
)
from doorstep_stats.monte_carlo import draw_inputs, propagate, rank_rows
from doorstep_stats.multiple import bh_adjust, bh_reject


def test_block_bootstrap_interval_covers_the_population_ratio() -> None:
    rng = np.random.default_rng(3)
    blocks = 200
    num = rng.poisson(30, blocks).astype(float)
    den = np.full(blocks, 100.0)
    iv = block_bootstrap(
        np.arange(blocks), np.column_stack([num, den]), ratio(0, 1), replicates=300, seed=1, label="t"
    )
    assert iv.low <= iv.estimate <= iv.high
    assert iv.low <= 0.30 <= iv.high
    assert iv.replicates == 300 and iv.blocks == blocks


def test_block_bootstrap_is_order_independent() -> None:
    rng = np.random.default_rng(5)
    keys = np.arange(50)
    sums = np.column_stack([rng.normal(10, 2, 50), np.ones(50)])
    a = block_bootstrap(keys, sums, ratio(0, 1), replicates=100, seed=9, label="x")
    perm = rng.permutation(50)
    b = block_bootstrap(keys[perm], sums[perm], ratio(0, 1), replicates=100, seed=9, label="x")
    assert (a.low, a.high) == (b.low, b.high)


def test_block_bootstrap_rejects_one_block() -> None:
    with pytest.raises(ValueError):
        block_bootstrap(np.array([1]), np.array([[1.0, 1.0]]), ratio(0, 1), replicates=10, seed=1, label="x")


def test_resample_blocks_keeps_the_block_count() -> None:
    m = resample_blocks(12, replicates=5, seed=2, label="r")
    assert m.shape == (5, 12)
    assert (m.sum(axis=1) == 12).all()


def test_histogram_quantile_interpolates_inside_bins() -> None:
    edges = [0.0, 10.0, 20.0, 30.0]
    counts = [10.0, 10.0, 10.0]
    assert histogram_quantile(edges, counts, 0.5) == pytest.approx(15.0)
    assert histogram_quantile(edges, counts, 0.1) == pytest.approx(3.0)
    assert np.isnan(histogram_quantile(edges, [0.0, 0.0, 0.0], 0.5))


def test_percentile_interval_ignores_undefined_draws() -> None:
    iv = percentile_interval(1.0, [0.5, 1.5, float("nan"), 1.0], blocks=3)
    assert iv.low == pytest.approx(0.525) and iv.high == pytest.approx(1.475)
    assert iv.replicates == 4 and iv.blocks == 3


def test_monte_carlo_draws_respect_the_margin_and_the_floor() -> None:
    d = draw_inputs({"v": [100.0, 200.0]}, {"v": [16.45, 0.0]}, draws=4000, seed=1, label="m", floor=1.0)
    sd = d.values["v"][:, 0].std()
    assert abs(sd - 10.0) < 0.5
    assert (d.values["v"][:, 1] == 200.0).all()
    mid, low, high = propagate(d, lambda x: x["v"] * 2.0)
    assert low[0] < mid[0] < high[0]


def test_rank_rows_breaks_ties_stably() -> None:
    r = rank_rows(np.array([[3.0, 1.0, 3.0], [1.0, 2.0, 3.0]]))
    assert r.tolist() == [[1.0, 3.0, 2.0], [3.0, 2.0, 1.0]]


def test_benjamini_hochberg_known_case() -> None:
    adjusted = bh_adjust([0.01, 0.04, 0.03, 0.20])
    assert adjusted == pytest.approx([0.04, 0.04 * 4 / 3, 0.04 * 4 / 3, 0.20])
    assert bh_reject([0.01, 0.04, 0.03, 0.20], 0.05) == [True, False, False, False]
    assert bh_reject([0.01, 0.04, 0.03, 0.20], 0.06) == [True, True, True, False]
    with pytest.raises(ValueError):
        bh_adjust([])
