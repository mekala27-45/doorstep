"""Synthetic control with in space placebo inference (Abadie, Diamond and Hainmueller, 2010).

For a metro that gained many people in the pandemic, the question is what its prices would have done
without the shock. The synthetic control is the convex combination of other metros (the donor pool)
whose pre period price index path lies closest to the treated metro's; its post period path is the
counterfactual and the gap is the effect. Inference is in space: every donor is treated in turn as if
it had received the shock, the ratio of its post period to pre period root mean squared prediction
error is computed beside the mean post period gap, and the treated metro's rank among the placebo gaps
is the p value (the ratio is reported beside it; it is fragile when a donor's pre period fit is near
perfect, which the simulator's metros make common). The weights are found by constrained least squares
on the simplex (SLSQP), and the test checks that a treated series that is itself a convex combination of
donors is recovered to floating tolerance.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from scipy.optimize import minimize

Array = npt.NDArray[np.float64]


class SyntheticControlError(ValueError):
    pass


@dataclass(frozen=True)
class SyntheticControl:
    treated: str
    donors: list[str]
    weights: Array
    pre_periods: int
    post_periods: int
    actual: Array
    synthetic: Array
    gap: Array
    pre_rmspe: float
    post_rmspe: float
    ratio: float
    placebo_ratios: Array
    placebo_gaps: Array  # (donors, pre + post) gaps when each donor is treated in turn
    p_value: float
    donors_searched: int

    @property
    def post_gap_mean(self) -> float:
        return float(self.gap[self.pre_periods :].mean())

    def top_weights(self, k: int = 5) -> list[tuple[str, float]]:
        order = np.argsort(-self.weights, kind="stable")
        return [(self.donors[i], float(self.weights[i])) for i in order[:k] if self.weights[i] > 1e-6]


def simplex_weights(target_pre: Array, donors_pre: Array) -> Array:
    """Weights on the simplex minimising the pre period squared distance."""
    j = donors_pre.shape[1]
    if j < 2:
        raise SyntheticControlError("at least two donors are needed")
    x0 = np.full(j, 1.0 / j)

    def objective(w: Array) -> float:
        r = target_pre - donors_pre @ w
        return float(r @ r)

    def gradient(w: Array) -> Array:
        r = target_pre - donors_pre @ w
        return -2.0 * donors_pre.T @ r

    result = minimize(
        objective,
        x0,
        jac=gradient,
        bounds=[(0.0, 1.0)] * j,
        constraints=[{"type": "eq", "fun": lambda w: float(w.sum() - 1.0), "jac": lambda w: np.ones(j)}],
        method="SLSQP",
        options={"maxiter": 500, "ftol": 1e-12},
    )
    w = np.clip(result.x, 0.0, None)
    total = w.sum()
    if total <= 0:
        raise SyntheticControlError("the weights collapsed to zero")
    return np.asarray(w / total, dtype=np.float64)


def _rmspe(actual: Array, synthetic: Array) -> float:
    return float(np.sqrt(np.mean((actual - synthetic) ** 2)))


def synthetic_control(
    treated: str,
    series: dict[str, Array],
    *,
    pre_periods: int,
) -> SyntheticControl:
    """``series`` maps every unit, treated included, to its path (pre periods first). Every other unit is a
    donor and every donor is searched as a placebo."""
    if treated not in series:
        raise SyntheticControlError(f"{treated} is not in the series")
    names = sorted(k for k in series if k != treated)
    if len(names) < 2:
        raise SyntheticControlError("at least two donors are needed")
    length = series[treated].shape[0]
    if pre_periods < 2 or pre_periods >= length:
        raise SyntheticControlError("the pre period must have at least two periods and leave a post period")
    for k in names:
        if series[k].shape[0] != length:
            raise SyntheticControlError(f"{k} has a different number of periods")
    matrix = np.column_stack([series[k] for k in names])
    actual = np.asarray(series[treated], dtype=np.float64)
    weights = simplex_weights(actual[:pre_periods], matrix[:pre_periods])
    synthetic = matrix @ weights
    gap = actual - synthetic
    pre = _rmspe(actual[:pre_periods], synthetic[:pre_periods])
    post = _rmspe(actual[pre_periods:], synthetic[pre_periods:])
    ratio = post / pre if pre > 0 else float("inf")
    placebo_ratios = np.empty(len(names))
    placebo_gaps = np.empty((len(names), length))
    for j in range(len(names)):
        others = np.delete(matrix, j, axis=1)
        target = matrix[:, j]
        w = simplex_weights(target[:pre_periods], others[:pre_periods])
        synth_j = others @ w
        placebo_gaps[j] = target - synth_j
        pre_j = _rmspe(target[:pre_periods], synth_j[:pre_periods])
        post_j = _rmspe(target[pre_periods:], synth_j[pre_periods:])
        placebo_ratios[j] = post_j / pre_j if pre_j > 0 else float("inf")
    # The p value counts the treated unit itself, as the permutation test does: the share of placebo units whose
    # mean post period gap is at least as large in absolute value as the treated unit's.
    treated_gap = abs(float(gap[pre_periods:].mean()))
    placebo_mean_gaps = np.abs(placebo_gaps[:, pre_periods:].mean(axis=1))
    p_value = float((1 + int(np.sum(placebo_mean_gaps >= treated_gap))) / (len(names) + 1))
    return SyntheticControl(
        treated=treated,
        donors=names,
        weights=weights,
        pre_periods=pre_periods,
        post_periods=length - pre_periods,
        actual=actual,
        synthetic=synthetic,
        gap=gap,
        pre_rmspe=pre,
        post_rmspe=post,
        ratio=ratio,
        placebo_ratios=placebo_ratios,
        placebo_gaps=placebo_gaps,
        p_value=p_value,
        donors_searched=len(names),
    )


def placebo_band(result: SyntheticControl, *, level: float = 0.90) -> tuple[Array, Array]:
    """The band the placebo gaps fill at each period, for the chart."""
    alpha = (1.0 - level) / 2.0
    return (
        np.quantile(result.placebo_gaps, alpha, axis=0),
        np.quantile(result.placebo_gaps, 1.0 - alpha, axis=0),
    )
