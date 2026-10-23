"""The share of households whose income clears a threshold, from the census income brackets.

The ACS publishes household counts by income bracket (table B19001), not the incomes themselves, so
the share of households above a threshold has to be interpolated inside the bracket the threshold
falls in. Inside a closed bracket the households are taken as spread evenly across it, which the
simulator's known log normal distributions show is accurate to a fraction of a point for the
brackets the census uses. The open top bracket ($200,000 and over) is given a Pareto tail whose
shape is fitted so that the tail's mean matches the mean income the bracket counts imply when a
mean is known, and a stated default shape otherwise; the recovery study grades the whole
interpolation against the exact share on the known distributions.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from doorstep_core.config import INCOME_BRACKETS

DEFAULT_PARETO_SHAPE = 2.5


class BracketError(ValueError):
    pass


def validate(counts: Sequence[float], bounds: Sequence[int] = INCOME_BRACKETS) -> None:
    if len(counts) != len(bounds) + 1:
        raise BracketError(f"{len(bounds) + 1} bracket counts are needed, got {len(counts)}")
    if any(c < 0 for c in counts):
        raise BracketError("bracket counts cannot be negative")
    if sum(counts) <= 0:
        raise BracketError("the brackets hold no households")


def share_above(
    threshold: float,
    counts: Sequence[float],
    bounds: Sequence[int] = INCOME_BRACKETS,
    *,
    pareto_shape: float = DEFAULT_PARETO_SHAPE,
) -> float:
    """The share of households with income at or above ``threshold``."""
    validate(counts, bounds)
    if pareto_shape <= 1.0:
        raise BracketError("the Pareto shape must exceed one for the tail to have a mean")
    total = float(sum(counts))
    if threshold <= 0:
        return 1.0
    edges = [0.0, *[float(b) for b in bounds]]
    above = 0.0
    for i, count in enumerate(counts[:-1]):
        lo, hi = edges[i], edges[i + 1]
        if threshold <= lo:
            above += count
        elif threshold < hi:
            above += count * (hi - threshold) / (hi - lo)
    top = counts[-1]
    top_lo = edges[-1]
    if threshold <= top_lo:
        above += top
    else:
        above += top * (top_lo / threshold) ** pareto_shape
    return float(min(1.0, max(0.0, above / total)))


def median_from_brackets(
    counts: Sequence[float], bounds: Sequence[int] = INCOME_BRACKETS, *, pareto_shape: float = DEFAULT_PARETO_SHAPE
) -> float:
    """The median implied by the brackets, for the test that holds the interpolation to the published median."""
    return quantile_from_brackets(0.5, counts, bounds, pareto_shape=pareto_shape)


def quantile_from_brackets(
    q: float, counts: Sequence[float], bounds: Sequence[int] = INCOME_BRACKETS, *, pareto_shape: float = DEFAULT_PARETO_SHAPE
) -> float:
    validate(counts, bounds)
    if not 0.0 < q < 1.0:
        raise BracketError("a quantile lies strictly inside (0, 1)")
    total = float(sum(counts))
    target = q * total
    edges = [0.0, *[float(b) for b in bounds]]
    cumulative = 0.0
    for i, count in enumerate(counts[:-1]):
        if cumulative + count >= target:
            lo, hi = edges[i], edges[i + 1]
            if count == 0:
                return lo
            return lo + (hi - lo) * (target - cumulative) / count
        cumulative += count
    top = counts[-1]
    remaining = target - cumulative
    if top <= 0:
        return edges[-1]
    tail_share_above = 1.0 - remaining / top
    tail_share_above = min(max(tail_share_above, 1e-9), 1.0)
    return edges[-1] * tail_share_above ** (-1.0 / pareto_shape)


def decile_incomes(
    counts: Sequence[float], bounds: Sequence[int] = INCOME_BRACKETS, *, pareto_shape: float = DEFAULT_PARETO_SHAPE
) -> list[float]:
    """The income at each decile boundary, 10th to 90th."""
    return [quantile_from_brackets(d / 10.0, counts, bounds, pareto_shape=pareto_shape) for d in range(1, 10)]


def exact_share_above_lognormal(threshold: float, mu: float, sigma: float) -> float:
    """The exact share above a threshold for a log normal with the given parameters; the truth the
    simulator hands the recovery study."""
    from math import erf, log, sqrt

    if threshold <= 0:
        return 1.0
    z = (log(threshold) - mu) / sigma
    return float(0.5 * (1.0 - erf(z / sqrt(2.0))))


def lognormal_bracket_counts(mu: float, sigma: float, households: float, bounds: Sequence[int] = INCOME_BRACKETS) -> list[float]:
    """Bracket counts a log normal population would report: the generator's census table."""
    from math import erf, log, sqrt

    def cdf(x: float) -> float:
        if x <= 0:
            return 0.0
        return 0.5 * (1.0 + erf((log(x) - mu) / (sigma * sqrt(2.0))))

    edges = [0.0, *[float(b) for b in bounds]]
    counts = [households * (cdf(edges[i + 1]) - cdf(edges[i])) for i in range(len(bounds))]
    counts.append(households * (1.0 - cdf(edges[-1])))
    return [float(c) for c in counts]


def pareto_shape_from_mean(top_lo: float, tail_mean: float) -> float:
    """The Pareto shape whose mean above ``top_lo`` equals ``tail_mean``: alpha = m / (m - x_min)."""
    if tail_mean <= top_lo:
        raise BracketError("the tail mean must exceed the bracket's lower bound")
    return float(tail_mean / (tail_mean - top_lo))


def interpolation_error(mu: float, sigma: float, households: float, thresholds: Sequence[float]) -> float:
    """Largest absolute error of the bracket interpolation against the exact share, over thresholds."""
    counts = lognormal_bracket_counts(mu, sigma, households)
    errors = [
        abs(share_above(t, counts) - exact_share_above_lognormal(t, mu, sigma)) for t in thresholds
    ]
    return float(np.max(errors)) if errors else 0.0
