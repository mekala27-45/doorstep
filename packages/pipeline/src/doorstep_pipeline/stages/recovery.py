"""The recovery study over every condition and seed, summarised for the data page and the method notes."""

from __future__ import annotations

from typing import Any

import polars as pl
from doorstep_core.frames import num
from doorstep_core.manifest import Manifest, Scribe
from doorstep_core.paths import Paths
from doorstep_evaluation.recovery import ESTIMATOR_NOTES, by_estimator, run_study, summarise
from doorstep_sim.metros import conditions

from doorstep_pipeline.common import new_partial, save_partial

SEEDS = 20

# Which estimators the page groups under each chapter, in the order the small multiples are drawn.
CHAPTER_ESTIMATORS: dict[int, tuple[str, ...]] = {
    1: ("anchored_payment_share", "anchored_level", "self_report_correction"),
    2: ("lock_in_did", "lock_in_placebo"),
    3: ("burden_changepoint", "severe_share"),
    4: ("supply_controlled", "supply_uncontrolled"),
    5: ("ranking_adjusted", "bracket_interpolation"),
    6: ("borrower_ratio_shift", "under_35_shift"),
    7: ("migration_effect", "migration_placebo"),
    8: ("breakeven_horizon",),
}

FORMATS: dict[str, tuple[str, str]] = {
    # estimator: (format of the estimate and bias, format of the truth)
    "anchored_payment_share": ("pts2", "pct1"),
    "anchored_level": ("sfloat3", "float1"),
    "self_report_correction": ("sfloat3", "float3"),
    "lock_in_did": ("sfloat4", "sfloat3"),
    "lock_in_placebo": ("sfloat4", "sfloat3"),
    "burden_changepoint": ("sfloat1", "int"),
    "severe_share": ("pts2", "pct1"),
    "supply_controlled": ("sfloat4", "sfloat3"),
    "supply_uncontrolled": ("sfloat4", "sfloat3"),
    "ranking_adjusted": ("sfloat3", "float1"),
    "bracket_interpolation": ("apts1", "pct0"),
    "borrower_ratio_shift": ("sfloat3", "sfloat2"),
    "under_35_shift": ("pts2", "pct0"),
    "migration_effect": ("spct2", "pct1"),
    "migration_placebo": ("spct2", "pct1"),
    "breakeven_horizon": ("float2", "float1"),
}


def run(p: Paths, *, seeds: int = SEEDS, workers: int = 2, use_cache: bool = True) -> Manifest:
    cache = p.scratch / "recovery" if use_cache else None
    records = pl.DataFrame(run_study(seeds, workers=workers, cache_dir=cache), infer_schema_length=None)
    out = p.results / "recovery"
    out.mkdir(parents=True, exist_ok=True)
    records = records.sort(["estimator", "condition", "seed"])
    records.write_parquet(out / "records.parquet", compression="zstd")
    summary = summarise(records)
    summary.write_parquet(out / "summary.parquet", compression="zstd")
    estimators = by_estimator(summary)
    estimators.write_parquet(out / "estimators.parquet", compression="zstd")

    manifest = new_partial("recovery")
    s = Scribe(
        manifest,
        source="simulated",
        population="the recovery study, every condition and seed",
        origin="stages/recovery.py",
        seeds=seeds,
    )
    s.put("recovery.seeds", seeds, "int")
    s.put("recovery.conditions", len(conditions()), "int")
    s.put("recovery.worlds", int(records.select(["condition", "seed"]).unique().height), "int")
    s.put("recovery.estimators", int(records["estimator"].n_unique()), "int")
    s.put("recovery.grades", records.height, "int")
    for row in estimators.iter_rows(named=True):
        name = str(row["estimator"])
        fmt_est, fmt_truth = FORMATS.get(name, ("float3", "float3"))
        s.put(f"recovery.{name}.mean_bias", num(row["mean_bias"]), fmt_est)
        s.put(
            f"recovery.{name}.mean_rmse",
            num(row["mean_rmse"]),
            fmt_est.replace("s", "", 1) if fmt_est.startswith("s") else fmt_est,
        )
        s.put(f"recovery.{name}.mean_coverage", row["mean_coverage"], "pct0")
        s.put(f"recovery.{name}.mean_flag_rate", row["mean_flag_rate"], "pct0")
        s.put(f"recovery.{name}.worst_bias", num(row["worst_bias"]), fmt_est)
        s.put(f"recovery.{name}.worst_bias_condition", str(row["worst_bias_condition"]), "text")
        s.put(f"recovery.{name}.lowest_coverage", row["lowest_coverage"], "pct0")
        s.put(
            f"recovery.{name}.lowest_coverage_condition",
            str(row["lowest_coverage_condition"] or "none"),
            "text",
        )
        s.put(f"recovery.{name}.note", ESTIMATOR_NOTES.get(name, ""), "text")
        truth = summary.filter(pl.col("estimator") == name)["truth"].mean()
        s.put(f"recovery.{name}.truth", num(truth) if truth is not None else None, fmt_truth)
    # The reverse causality contrast the migration chapter has to admit in print
    mig = summary.filter(pl.col("estimator") == "migration_effect")
    for level in ("none", "mild", "strong"):
        sub = mig.filter(pl.col("reverse_causality") == level)
        s.put(f"recovery.migration.{level}.bias", num(sub["bias"].mean()) if sub.height else None, "spct2")
        s.put(
            f"recovery.migration.{level}.coverage",
            num(sub["coverage"].mean()) if sub.height else None,
            "pct0",
        )
        s.put(
            f"recovery.migration.{level}.flag_rate",
            num(sub["flag_rate"].mean()) if sub.height else None,
            "pct0",
        )
    sup = summary.filter(pl.col("estimator").is_in(["supply_controlled", "supply_uncontrolled"]))
    for level in ("weak", "strong"):
        for est in ("supply_controlled", "supply_uncontrolled"):
            sub = sup.filter((pl.col("demand_strength") == level) & (pl.col("estimator") == est))
            s.put(
                f"recovery.{est}.{level}_demand.bias",
                num(sub["bias"].mean()) if sub.height else None,
                "sfloat4",
            )
    rank = summary.filter(pl.col("estimator") == "ranking_adjusted")
    s.put("recovery.ranking.adjusted", num(rank["estimate"].mean()) if rank.height else None, "float3")
    s.put("recovery.ranking.raw", num(rank["flag_rate"].mean()) if rank.height else None, "float3")
    worst = estimators.sort("lowest_coverage", nulls_last=True).row(0, named=True)
    s.put("recovery.worst.estimator", str(worst["estimator"]), "text")
    s.put("recovery.worst.condition", str(worst["lowest_coverage_condition"]), "text")

    rows: list[list[Any]] = []
    for row in summary.sort(["estimator", "condition"]).iter_rows(named=True):
        rows.append(
            [
                row["estimator"],
                row["condition"],
                int(row["seeds"]),
                row["bias"],
                row["rmse"],
                row["coverage"],
                row["flag_rate"],
            ]
        )
    s.table(
        "recovery.by_condition",
        ["Estimator", "Condition", "Seeds", "Bias", "RMSE", "Coverage", "Flag rate"],
        ["text", "text", "int", "sfloat4", "float4", "pct0", "pct0"],
        rows,
    )
    est_rows = [
        [
            r["estimator"],
            r["mean_bias"],
            r["mean_rmse"],
            r["mean_coverage"],
            r["mean_flag_rate"],
            r["worst_bias_condition"],
            r["lowest_coverage"],
            r["lowest_coverage_condition"],
        ]
        for r in estimators.iter_rows(named=True)
    ]
    s.table(
        "recovery.by_estimator",
        [
            "Estimator",
            "Mean bias",
            "Mean RMSE",
            "Mean coverage",
            "Mean flag rate",
            "Worst bias under",
            "Lowest coverage",
            "Lowest coverage under",
        ],
        ["text", "sfloat4", "float4", "pct0", "pct0", "text", "pct0", "text"],
        est_rows,
    )
    save_partial(p, "recovery", manifest)
    return manifest
