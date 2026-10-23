"""Stage: the workbook, the BI extracts and specifications, and the CSV bundle, under exports/.

Reads the chapter tables from the chapters stage's manifest and the calculator marts, so it runs after
the chapters and before the manifest is assembled; its own counts go into the exports partial manifest,
which the documents quote.
"""

from __future__ import annotations

import json

import polars as pl
from doorstep_core.manifest import Manifest, Scribe
from doorstep_core.paths import Paths
from doorstep_exports import bi, workbook

from doorstep_pipeline.common import new_partial, save_partial
from doorstep_pipeline.metric_layer import load

CHAPTER_TABLES: tuple[tuple[str, str], ...] = (
    ("ch1.series", "Ch1 payment share by year"),
    ("ch1.anchor_sensitivity", "Ch1 anchor sensitivity"),
    ("ch1.line_interior", "Ch1 line interior test"),
    ("ch2.decomposition", "Ch2 rate shock by quarter"),
    ("ch2.threshold_interior", "Ch2 lock in thresholds"),
    ("ch3.bands", "Ch3 burden bands"),
    ("ch3.by_income_group", "Ch3 burden by income"),
    ("ch3.line_interior", "Ch3 line interior test"),
    ("ch4.specifications", "Ch4 supply specifications"),
    ("ch4.window_interior", "Ch4 window interior test"),
    ("ch5.largest", "Ch5 fair ranking"),
    ("ch6.by_year", "Ch6 borrowers by year"),
    ("ch6.largest_metros", "Ch6 borrowers by metro"),
    ("ch7.regression", "Ch7 migration regression"),
    ("ch7.synthetic_controls", "Ch7 synthetic controls"),
    ("ch8.largest", "Ch8 reader decision"),
    ("ch8.line_interior", "Ch8 line interior test"),
    ("ch8.down_interior", "Ch8 down payment interior"),
    ("ch8.saving_interior", "Ch8 saving rate interior"),
    ("recovery.by_estimator", "Recovery by estimator"),
    ("recovery.by_condition", "Recovery by condition"),
    ("metrics.definitions", "Metric definitions"),
)


def _partials(p: Paths) -> Manifest:
    merged = Manifest(as_of="", seed=0)
    for stage in ("recovery", "metrics", "chapters"):
        path = p.results / stage / "manifest.json"
        if path.exists():
            loaded = Manifest.load(path)
            merged.as_of, merged.seed = loaded.as_of, loaded.seed
            merged.merge(loaded)
    return merged


def run(p: Paths) -> Manifest:
    source = _partials(p)
    out = p.exports
    metros = pl.read_parquet(p.marts / "calc_metros.parquet")
    meta = json.loads((p.marts / "calc_meta.json").read_text(encoding="utf-8"))
    built = workbook.build(
        out / "workbook.xlsx",
        source,
        metros,
        chapter_tables=CHAPTER_TABLES,
        rate_default=float(meta["rate_default"]),
    )
    extracts = bi.tableau(p.marts, out / "tableau")
    metrics = load(p.root / "metrics" / "metrics.yml")
    ranked = len(source.tables["ch5.largest"].rows) if "ch5.largest" in source.tables else 0
    measures = bi.powerbi(metrics, out / "powerbi", ranked)
    extra = {}
    for name in ("mart_metro_year", "ch5_ranking", "ch8_metros"):
        path = p.marts / f"{name}.parquet"
        if path.exists():
            extra[name] = pl.read_parquet(path)
    bundle = bi.csv_bundle(source, [k for k, _ in CHAPTER_TABLES], out / "csv", extra)
    manifest = new_partial("exports")
    s = Scribe(
        manifest,
        source="mixed",
        population="the exports, from the marts and the chapter tables",
        origin="stages/exports.py",
    )
    s.put("exports.workbook.sheets", built["sheets"], "int")
    s.put("exports.workbook.chapter_sheets", built["chapter_sheets"], "int")
    s.put("exports.workbook.metros", built["metros"], "int")
    s.put("exports.workbook.formulas", built["formulas"], "int")
    s.put("exports.workbook.named_ranges", built["named_ranges"], "int")
    s.put("exports.workbook.default_metro", str(built["default_metro"]), "text")
    for name, rows in extracts.items():
        s.put(f"exports.tableau.{name}.rows", rows, "int")
    s.put("exports.tableau.views", len(bi.TABLEAU_VIEWS), "int")
    s.put("exports.powerbi.measures", measures, "int")
    s.put("exports.csv.files", len(bundle), "int")
    s.put("exports.csv.rows", sum(bundle.values()), "int")
    save_partial(p, "exports", manifest)
    return manifest
