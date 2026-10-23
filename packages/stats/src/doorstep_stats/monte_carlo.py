"""Monte Carlo propagation of survey margins of error.

The census publishes every estimate with a ninety percent margin of error. A payment share divides an
anchored value by a median income, and a ranking sorts those shares, so the margin on each input has to
be carried through to the output rather than quoted beside it. Each input is drawn from a normal with
the published estimate as its mean and the margin over 1.645 as its standard deviation, the output is
computed on every draw, and the interval is the percentile interval over the draws. The index is held
fixed, because the regulator publishes it without a margin; the pushback says what that leaves out.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

Array = npt.NDArray[np.float64]

Z_90 = 1.6448536269514722


@dataclass(frozen=True)
class Draws:
    """``values[name]`` has shape (draws, n): one row per draw, one column per unit."""

    values: dict[str, Array]
    draws: int


def _rng(seed: int, label: str) -> np.random.Generator:
    stream = int.from_bytes(label.encode("utf-8")[:8].ljust(8, b"\0"), "little") % (2**31)
    return np.random.default_rng(np.random.SeedSequence([seed, stream]))


def draw_inputs(
    estimates: Mapping[str, npt.ArrayLike],
    margins: Mapping[str, npt.ArrayLike],
    *,
    draws: int,
    seed: int,
    label: str,
    floor: float = 1.0,
) -> Draws:
    """Normal draws around each estimate with the margin as a ninety percent half width. Inputs are
    floored at ``floor`` so a drawn income or value never goes to zero or negative."""
    if draws < 1:
        raise ValueError("at least one draw")
    rng = _rng(seed, label)
    out: dict[str, Array] = {}
    for name in sorted(estimates):
        est = np.asarray(estimates[name], dtype=np.float64)
        moe = np.asarray(margins[name], dtype=np.float64)
        if est.shape != moe.shape:
            raise ValueError(f"{name}: estimates and margins differ in shape")
        sd = np.where(np.isfinite(moe), np.abs(moe) / Z_90, 0.0)
        sample = est[None, :] + rng.standard_normal((draws, est.shape[0])) * sd[None, :]
        out[name] = np.maximum(sample, floor)
    return Draws(out, draws)


def propagate(
    inputs: Draws, function: Callable[[Mapping[str, Array]], Array], *, level: float = 0.95
) -> tuple[Array, Array, Array]:
    """Apply a vectorised function to every draw; returns (median, low, high) per unit."""
    result = np.asarray(function(inputs.values), dtype=np.float64)
    if result.shape[0] != inputs.draws:
        raise ValueError("the function must return one row per draw")
    alpha = (1.0 - level) / 2.0
    low = np.nanquantile(result, alpha, axis=0)
    high = np.nanquantile(result, 1.0 - alpha, axis=0)
    mid = np.nanmedian(result, axis=0)
    return mid, low, high


def rank_rows(values: Array) -> Array:
    """Rank 1 is the largest value in each row; ties broken by column order, stably."""
    order = np.argsort(-values, axis=1, kind="stable")
    ranks = np.empty_like(order)
    rows = np.arange(values.shape[0])[:, None]
    ranks[rows, order] = np.arange(1, values.shape[1] + 1)[None, :]
    return ranks.astype(np.float64)
