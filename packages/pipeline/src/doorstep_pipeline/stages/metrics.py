"""The metric layer's reconcile over the warehouse, and the headline values of every metric.

Run after the warehouse: every metric in metrics/metrics.yml is evaluated over its grain table and
over the shipped mart at four grains and the two are diffed. Any disagreement fails the stage; the
counts and each metric's overall value go into the manifest.
"""

from __future__ import annotations

import json

import duckdb
from doorstep_core.manifest import Manifest, Scribe
from doorstep_core.paths import Paths

from doorstep_pipeline.common import new_partial, save_partial
from doorstep_pipeline.metric_layer import Metric, MetricError, grain_table, load, reconcile


def shipped_connection(p: Paths, metrics: list[Metric]) -> duckdb.DuckDBPyConnection:
    """The grain table from the warehouse; every mart from the parquet actually shipped in results/marts,
    which is what the site, the workbook and the BI extracts read."""
    con = duckdb.connect()
    con.execute("set enable_progress_bar = false")
    con.execute(f"attach '{p.warehouse_db.as_posix()}' as wh (read_only)")
    for source in sorted({m.grain_source for m in metrics}):
        con.execute(f"create view {grain_table(source)} as select * from wh.{source}")
    for source in sorted({m.mart_source for m in metrics}):
        shipped = p.marts / f"{source}.parquet"
        if not shipped.exists():
            raise MetricError(f"{shipped} is missing: run the warehouse stage before reconciling")
        con.execute(f"create view {source} as select * from read_parquet('{shipped.as_posix()}')")
    return con


def run(p: Paths, *, stages: tuple[str, ...] = ("warehouse",)) -> Manifest:
    metrics = [m for m in load(p.root / "metrics" / "metrics.yml") if m.stage in stages]
    con = shipped_connection(p, metrics)
    report = reconcile(con, metrics)
    if not report.ok:
        lines = [
            f"{d.metric} [{d.grain}] {d.key}: grain {d.grain_value} against mart {d.mart_value}"
            for d in report.disagreements[:20]
        ]
        raise MetricError("the metric layer does not reconcile:\n" + "\n".join(lines))
    values = {}
    for metric in metrics:
        sql = f"select {metric.grain} from {grain_table(metric.grain_source)}"
        row = con.execute(sql).fetchone()
        values[metric.name] = None if not row or row[0] is None else float(row[0])
    # The workbook's summary opens on the latest full year; these are the values it must compute.
    full = con.execute("select max(year) from mart_metro_year where acs_year_complete").fetchone()
    summary_year = int(full[0]) if full and full[0] is not None else None
    year_values: dict[str, float | None] = {}
    if summary_year is not None:
        for metric in metrics:
            row = con.execute(
                f"select {metric.grain} from {grain_table(metric.grain_source)} where year = {summary_year}"
            ).fetchone()
            year_values[metric.name] = None if not row or row[0] is None else float(row[0])
    con.close()
    out = p.results / "metrics"
    out.mkdir(parents=True, exist_ok=True)
    (out / "reconcile.json").write_text(
        json.dumps(
            {
                "metrics": report.metrics,
                "grains": report.grains,
                "cells": report.cells,
                "disagreements": 0,
                "values": values,
            },
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = new_partial("metrics")
    s = Scribe(
        manifest,
        source="mixed",
        population="every metro and year in the window, through the metric layer",
        origin="stages/metrics.py",
    )
    s.put("metrics.count", report.metrics, "int")
    s.put("metrics.grains", report.grains, "int")
    s.put("metrics.cells", report.cells, "int")
    s.put("metrics.disagreements", len(report.disagreements), "int")
    for metric in metrics:
        s.put(f"metric.{metric.name}", values[metric.name], metric.fmt)
    s.put("metrics.summary_year", str(summary_year) if summary_year is not None else "none", "text")
    for metric in metrics:
        s.put(f"metric_sql.{metric.name}.grain", metric.grain, "text")
        s.put(f"metric_sql.{metric.name}.mart", metric.mart, "text")
    for metric in metrics:
        if metric.name in year_values:
            s.put(f"metric.{metric.name}.summary_year", year_values[metric.name], metric.fmt)
    s.table(
        "metrics.definitions",
        ["Metric", "Over the grain", "Over the mart"],
        ["text", "text", "text"],
        [[m.name.replace("_", " "), m.grain, m.mart] for m in metrics],
    )
    save_partial(p, "metrics", manifest)
    return manifest
