"""The vectorised breakeven equals the scalar engine path by path, and the hand computed case holds."""

from __future__ import annotations

import numpy as np
from doorstep_finance.breakeven import CostModel, breakeven, breakeven_year, breakeven_years_vectorised


def test_vectorised_matches_scalar_engine_path_by_path() -> None:
    rng = np.random.default_rng(7)
    cost = CostModel()
    app = rng.normal(0.03, 0.05, (40, 30))
    rg = rng.normal(0.03, 0.03, (40, 30))
    vec = breakeven_years_vectorised(420_000, 26_000, 6.4, 0.10, 30, app, rg, cost)
    scalar = [
        breakeven_year(breakeven(420_000, 26_000, 6.4, 0.10, 30, 30, list(app[i]), list(rg[i]), cost), 30)
        for i in range(40)
    ]
    assert vec == scalar


def test_vectorised_rejects_mismatched_paths() -> None:
    import pytest
    from doorstep_finance.mortgage import FinanceError

    with pytest.raises(FinanceError):
        breakeven_years_vectorised(1.0, 1.0, 5.0, 0.1, 30, np.zeros((2, 5)), np.zeros((3, 5)), CostModel())
