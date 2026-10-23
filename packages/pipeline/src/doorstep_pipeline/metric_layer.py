"""The metric layer: load metrics/metrics.yml, evaluate each metric two ways, and fail on any disagreement.

The grain expression reads the warehouse's finest table. The mart expression reads the shipped
mart. Both come from the same file and neither is derived from the other, so agreement is evidence.
Four grains are checked: a metric can agree in total and disagree everywhere underneath, which is
the usual shape of a grain bug. The reconcile refuses an empty mart, which would agree with an empty
query about everything.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import yaml

RELATIVE_TOLERANCE = 1e-9
ABSOLUTE_TOLERANCE = 1e-9
GRAINS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("overall", ()),
    ("by year", ("year",)),
    ("by kind", ("kind",)),
    ("by year and kind", ("year", "kind")),
)
DEFAULT_GRAIN_SOURCE = "fct_metro_year"
DEFAULT_MART_SOURCE = "mart_metro_year"


class MetricError(ValueError):
    pass


@dataclass(frozen=True)
class Metric:
    name: str
    kind: str
    fmt: str
    description: str
    grain: str
    mart: str
    grain_source: str
    mart_source: str
    stage: str

    def dax(self, table: str = "metro_year") -> str:
        """The mart expression as a DAX measure over the BI model's table."""
        text = re.sub(r"sum\((\w+)\)", lambda m: f"SUM('{table}'[{m.group(1)}])", self.mart)
        if "/" in text:
            numerator, denominator = text.rsplit("/", 1)
            if numerator.strip().startswith("1 -"):
                return f"1 - DIVIDE({numerator.strip()[3:].strip()}, {denominator.strip()})"
            return f"DIVIDE({numerator.strip()}, {denominator.strip()})"
        return text


def load(path: Path) -> list[Metric]:
    payload: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    metrics = []
    for item in payload.get("metrics", []):
        metrics.append(
            Metric(
                name=item["name"],
                kind=item["kind"],
                fmt=item["fmt"],
                description=" ".join(str(item["description"]).split()),
                grain=item["grain"],
                mart=item["mart"],
                grain_source=item.get("grain_source", DEFAULT_GRAIN_SOURCE),
                mart_source=item.get("mart_source", DEFAULT_MART_SOURCE),
                stage=item.get("stage", "warehouse"),
            )
        )
    names = [m.name for m in metrics]
    if len(set(names)) != len(names):
        raise MetricError("a metric is defined twice")
    if not metrics:
        raise MetricError("the metric layer defines no metrics")
    return metrics


@dataclass(frozen=True)
class Disagreement:
    metric: str
    grain: str
    key: str
    grain: float | None
    mart: float | None


@dataclass(frozen=True)
class Report:
    metrics: int
    grains: int
    cells: int
    disagreements: list[Disagreement]

    @property
    def ok(self) -> bool:
        return not self.disagreements


def close(a: float | None, b: float | None) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if math.isnan(a) and math.isnan(b):
        return True
    return math.isclose(a, b, rel_tol=RELATIVE_TOLERANCE, abs_tol=ABSOLUTE_TOLERANCE)


def _mart_sql(metric: Metric, dims: tuple[str, ...]) -> str:
    select_dims = ", ".join(dims)
    group = f" group by {select_dims}" if dims else ""
    prefix = f"{select_dims}, " if dims else ""
    return f"select {prefix}{metric.mart} as value from {metric.mart_source}{group}"


def _grain_sql(metric: Metric, dims: tuple[str, ...]) -> str:
    select_dims = ", ".join(dims)
    prefix = f"{select_dims}, " if dims else ""
    group = f" group by {select_dims}" if dims else ""
    return f"select {prefix}{metric.grain} as value from {metric.grain_source}{group}"


def reconcile_metric(con: duckdb.DuckDBPyConnection, metric: Metric) -> tuple[int, list[Disagreement]]:
    empty = con.execute(f"select count(*) from {metric.mart_source}").fetchone()
    if not empty or int(empty[0]) == 0:
        raise MetricError(
            f"{metric.mart_source} is empty: there is nothing to reconcile {metric.name} against"
        )
    out: list[Disagreement] = []
    cells = 0
    for label, dims in GRAINS:
        grain = _grain_sql(metric, dims)
        mart = _mart_sql(metric, dims)
        if dims:
            on = " and ".join(f"f.{d} is not distinct from m.{d}" for d in dims)
            keys = ", ".join(f"coalesce(f.{d}, m.{d}) as {d}" for d in dims)
            rows = con.execute(
                f"with f as ({grain}), m as ({mart}) select {keys}, f.value, m.value from f full outer join m on {on}"
            ).fetchall()
            for row in rows:
                cells += 1
                fv = None if row[-2] is None else float(row[-2])
                mv = None if row[-1] is None else float(row[-1])
                if not close(fv, mv):
                    key = ", ".join(f"{d}={v}" for d, v in zip(dims, row[: len(dims)], strict=True))
                    out.append(Disagreement(metric.name, label, key, fv, mv))
        else:
            cells += 1
            fr = con.execute(grain).fetchone()
            mr = con.execute(mart).fetchone()
            fv = None if not fr or fr[0] is None else float(fr[0])
            mv = None if not mr or mr[0] is None else float(mr[0])
            if not close(fv, mv):
                out.append(Disagreement(metric.name, label, "all", fv, mv))
    return cells, out


def reconcile(con: duckdb.DuckDBPyConnection, metrics: list[Metric]) -> Report:
    if not metrics:
        raise MetricError("no metrics to reconcile")
    cells = 0
    disagreements: list[Disagreement] = []
    for metric in metrics:
        n, found = reconcile_metric(con, metric)
        cells += n
        disagreements.extend(found)
    return Report(len(metrics), len(GRAINS), cells, disagreements)
