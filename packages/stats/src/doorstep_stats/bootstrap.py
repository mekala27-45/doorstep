"""The block bootstrap: resample whole blocks, never single rows.

Quarters of one metro share a market, lenders share a year's rate path and a metro's households share a
survey, so the rows inside a block are not independent and a row level bootstrap would print intervals
far too narrow. Every interval in the story resamples whole blocks: quarters for a time series, metros
for a cross section, lenders for the borrower pool. The statistic is computed from per block sufficient
statistics (sums and counts), blocks are drawn with replacement, and the interval is the percentile
interval of the replicates. Blocks are sorted before the draw, so the same seed gives the same interval
whatever order a query returned the blocks in.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

Statistic = Callable[[npt.NDArray[np.float64]], float]


@dataclass(frozen=True)
class Interval:
    estimate: float
    low: float
    high: float
    replicates: int
    blocks: int

    def covers(self, value: float) -> bool:
        return self.low <= value <= self.high

    @property
    def width(self) -> float:
        return self.high - self.low


def _rng(seed: int, label: str) -> np.random.Generator:
    stream = int.from_bytes(label.encode("utf-8")[:8].ljust(8, b"\0"), "little") % (2**31)
    return np.random.default_rng(np.random.SeedSequence([seed, stream]))


def block_bootstrap(
    block_keys: npt.ArrayLike,
    sums: npt.NDArray[np.float64],
    statistic: Statistic,
    *,
    replicates: int,
    seed: int,
    label: str,
    level: float = 0.95,
    strata: npt.ArrayLike | None = None,
) -> Interval:
    """Resample blocks. ``sums`` holds one row of sufficient statistics per block; ``statistic`` maps the
    column sums of a resampled set of blocks to the number being estimated. With ``strata`` (a year, say)
    blocks are drawn within each stratum, so a change between two years keeps each year's block count."""
    keys = np.asarray(block_keys)
    values = np.asarray(sums, dtype=np.float64)
    if values.ndim == 1:
        values = values[:, None]
    if keys.shape[0] != values.shape[0]:
        raise ValueError("one row of sums per block")
    if keys.shape[0] < 2:
        raise ValueError("the block bootstrap needs at least two blocks")
    if replicates < 1:
        raise ValueError("at least one replicate")
    groups = (
        np.zeros(keys.shape[0], dtype=np.int64)
        if strata is None
        else np.unique(np.asarray(strata), return_inverse=True)[1]
    )
    order = np.lexsort((keys, groups))
    values = values[order]
    groups = groups[order]
    n = values.shape[0]
    estimate = statistic(values.sum(axis=0))
    rng = _rng(seed, label)
    bounds = [
        (int(np.searchsorted(groups, g, "left")), int(np.searchsorted(groups, g, "right")))
        for g in np.unique(groups)
    ]
    draws = np.empty(replicates)
    for b in range(replicates):
        counts = np.zeros(n)
        for lo, hi in bounds:
            counts[lo:hi] = np.bincount(rng.integers(0, hi - lo, hi - lo), minlength=hi - lo)
        draws[b] = statistic(counts @ values)
    finite = draws[np.isfinite(draws)]
    if finite.size == 0:
        raise ValueError("every replicate was undefined")
    alpha = (1.0 - level) / 2.0
    low, high = np.quantile(finite, [alpha, 1.0 - alpha])
    return Interval(float(estimate), float(low), float(high), replicates, n)


def resample_blocks(n_blocks: int, *, replicates: int, seed: int, label: str) -> npt.NDArray[np.int64]:
    """Replicate by block multiplicity counts, for statistics that are not sums (a median over a histogram
    or a regression). Row b holds how many times each block appears in replicate b."""
    if n_blocks < 2:
        raise ValueError("the block bootstrap needs at least two blocks")
    rng = _rng(seed, label)
    out = np.empty((replicates, n_blocks), dtype=np.int64)
    for b in range(replicates):
        out[b] = np.bincount(rng.integers(0, n_blocks, n_blocks), minlength=n_blocks)
    return out


def percentile_interval(
    estimate: float, draws: npt.ArrayLike, *, level: float = 0.95, blocks: int = 0
) -> Interval:
    values = np.asarray(draws, dtype=np.float64)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        raise ValueError("every draw was undefined")
    alpha = (1.0 - level) / 2.0
    low, high = np.quantile(finite, [alpha, 1.0 - alpha])
    return Interval(float(estimate), float(low), float(high), int(values.size), blocks)


def ratio(numerator: int = 0, denominator: int = 1) -> Statistic:
    def inner(total: npt.NDArray[np.float64]) -> float:
        return float(total[numerator] / total[denominator]) if total[denominator] else float("nan")

    return inner


def difference_of_ratios(a: tuple[int, int], b: tuple[int, int]) -> Statistic:
    def inner(total: npt.NDArray[np.float64]) -> float:
        return float(total[a[0]] / total[a[1]] - total[b[0]] / total[b[1]])

    return inner


def mean(column: int = 0, count: int = 1) -> Statistic:
    return ratio(column, count)


def histogram_quantile(edges: npt.ArrayLike, counts: npt.ArrayLike, q: float) -> float:
    """A quantile from a histogram with the mass spread evenly inside each bin. ``edges`` has one more
    entry than ``counts``. Incomes reported in thousands make the bins exact to the thousand."""
    e = np.asarray(edges, dtype=np.float64)
    c = np.asarray(counts, dtype=np.float64)
    if e.shape[0] != c.shape[0] + 1:
        raise ValueError("edges must have one more entry than counts")
    total = c.sum()
    if total <= 0:
        return float("nan")
    target = q * total
    cumulative = np.cumsum(c)
    i = int(np.searchsorted(cumulative, target, side="left"))
    i = min(i, c.shape[0] - 1)
    before = cumulative[i - 1] if i > 0 else 0.0
    inside = c[i]
    if inside <= 0:
        return float(e[i])
    return float(e[i] + (e[i + 1] - e[i]) * (target - before) / inside)
