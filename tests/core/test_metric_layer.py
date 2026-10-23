"""The metric layer's reconcile: it agrees with itself, it fails on a mart that dropped a filter, and it
refuses an empty mart rather than reporting a pass over nothing."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
from doorstep_pipeline.metric_layer import Metric, MetricError, close, grain_table, load, reconcile

ROOT = Path(__file__).resolve().parents[2]


def _metric(mart_expr: str = "sum(permits)") -> Metric:
    return Metric("permits", "sum", "int", "units permitted", "sum(permits)", mart_expr, "grain_counties", "mart_metro_year", "warehouse")


def _connection(mart_rows: str = "select * from counties") -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(
        "create table counties as select * from (values ('A', 2020, 'metropolitan', 10), ('A', 2021, 'metropolitan', 12), "
        "('B', 2020, 'micropolitan', 3)) t(cbsa_code, year, kind, permits)"
    )
    con.execute(f"create view {grain_table('grain_counties')} as select * from counties")
    con.execute(f"create view mart_metro_year as {mart_rows}")
    return con


def test_the_reconcile_passes_a_mart_that_matches_its_grain() -> None:
    report = reconcile(_connection(), [_metric()])
    assert report.ok and report.metrics == 1 and report.grains == 4 and report.cells > 0


def test_the_reconcile_fails_a_mart_that_dropped_a_filter() -> None:
    report = reconcile(_connection("select * from counties where kind = 'metropolitan'"), [_metric()])
    assert not report.ok
    assert {d.grain for d in report.disagreements} >= {"overall", "by kind"}


def test_the_reconcile_refuses_an_empty_mart() -> None:
    with pytest.raises(MetricError, match="empty"):
        reconcile(_connection("select * from counties where 1 = 0"), [_metric()])


def test_the_reconcile_is_symmetric_in_its_tolerance() -> None:
    assert close(1.0, 1.0 + 1e-12) and close(1.0 + 1e-12, 1.0)
    assert not close(1.0, 1.01) and not close(1.01, 1.0)
    assert close(None, None) and not close(None, 1.0)


def test_the_committed_layer_loads_with_two_expressions_per_metric_and_a_dax_measure() -> None:
    metrics = load(ROOT / "metrics" / "metrics.yml")
    assert len(metrics) >= 14
    names = [m.name for m in metrics]
    assert len(set(names)) == len(names)
    for m in metrics:
        assert m.grain and m.mart and m.fmt
    ratio = next(m for m in metrics if m.name == "renter_burdened_share")
    assert ratio.dax().startswith("DIVIDE(")
    with pytest.raises(FileNotFoundError):
        load(ROOT / "metrics" / "does_not_exist.yml")
