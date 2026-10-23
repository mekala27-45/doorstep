"""Cross section and panel regressions with cluster robust standard errors, on top of the fixed effects
solver. The migration chapter regresses two year price growth on migration per hundred residents across
metros with state clusters; the lock in chapter regresses turnover on lock in intensity with metro and
year fixed effects and state clusters; both print a placebo beside the headline. The intervals and p
values use the t distribution with one fewer degree of freedom than there are clusters, the small cluster
convention (Cameron and Miller 2015): with fifteen simulated states or fifty real ones the normal
approximation runs narrow, and the recovery study reports the coverage either way.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from scipy import stats as sp_stats

from doorstep_stats.fe import FitResult, fit

Array = npt.NDArray[np.float64]

Z_95 = 1.959963984540054


@dataclass(frozen=True)
class Coefficient:
    name: str
    estimate: float
    se: float
    low: float
    high: float
    p_value: float
    clusters: int
    cells: int

    def covers(self, value: float) -> bool:
        return self.low <= value <= self.high

    @property
    def excludes_zero(self) -> bool:
        return not self.covers(0.0)


def critical_value(clusters: int, level: float = 0.95) -> float:
    """The t critical value on clusters minus one degrees of freedom; the normal value when there are no clusters."""
    if clusters >= 2:
        return float(sp_stats.t.ppf(0.5 + level / 2.0, df=clusters - 1))
    return float(sp_stats.norm.ppf(0.5 + level / 2.0))


def coefficients(result: FitResult, *, clusters: int, level: float = 0.95) -> list[Coefficient]:
    z = critical_value(clusters, level)
    out: list[Coefficient] = []
    se = result.se
    for i, name in enumerate(result.names):
        est = float(result.coef[i])
        s = float(se[i])
        t = est / s if s > 0 else float("inf")
        if not np.isfinite(t):
            p = 0.0
        elif clusters >= 2:
            p = float(2.0 * sp_stats.t.sf(abs(t), df=clusters - 1))
        else:
            p = float(2.0 * sp_stats.norm.sf(abs(t)))
        out.append(
            Coefficient(name, est, s, est - z * s, est + z * s, p, clusters, int(result.weights.shape[0]))
        )
    return out


def regress(
    y: npt.ArrayLike,
    x: npt.ArrayLike,
    names: Sequence[str],
    *,
    weights: npt.ArrayLike | None = None,
    fixed_effects: Sequence[npt.ArrayLike] = (),
    cluster: npt.ArrayLike,
    level: float = 0.95,
) -> list[Coefficient]:
    """Weighted least squares of y on x with the fixed effects absorbed and a constant when none are
    given, cluster robust by ``cluster``."""
    yv = np.asarray(y, dtype=np.float64)
    xv = np.asarray(x, dtype=np.float64)
    if xv.ndim == 1:
        xv = xv[:, None]
    w = np.ones(yv.shape[0]) if weights is None else np.asarray(weights, dtype=np.float64)
    groups = list(fixed_effects) if fixed_effects else [np.zeros(yv.shape[0], dtype=np.int64)]
    result = fit(yv, xv, w, groups, list(names), cluster=cluster)
    n_clusters = int(np.unique(np.asarray(cluster)).shape[0])
    return coefficients(result, clusters=n_clusters, level=level)


def first(coefs: Sequence[Coefficient], name: str) -> Coefficient:
    for c in coefs:
        if c.name == name:
            return c
    raise KeyError(f"no coefficient named {name!r}")
