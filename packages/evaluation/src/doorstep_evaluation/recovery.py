"""The recovery study: every estimator graded on simulated metros with known truth, by condition and seed.

Each chapter module exposes ``simulate_estimate(world)`` returning ``Grade`` rows: the estimate, the
truth, the interval when the estimator gives one, and a per world flag the study averages (the placebo
flagged the condition, the changepoint was found, the interval covered). The study generates a world
per condition and seed, runs every estimator on it, and summarises per condition and estimator: the
bias (mean error), the root mean squared error, the coverage of the interval and the mean flag. Worlds
are cached by a digest of the condition, the seed and the code version of the simulator, so a rerun
with the same inputs is a cache hit and a changed input a miss; one thread per worker, and each worker
re-imports what the parent registered.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Iterable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any

import polars as pl
from doorstep_chapters import (
    c1_definition,
    c2_rate_shock,
    c3_burden,
    c4_supply,
    c5_ranking,
    c6_buyers,
    c7_migration,
    c8_decision,
)
from doorstep_chapters.common import Grade
from doorstep_sim import metros as sim_metros
from doorstep_sim.metros import Condition, World, conditions, generate

Estimator = Callable[[World], list[Grade]]

ESTIMATORS: dict[str, Estimator] = {
    "chapter1": lambda w: c1_definition.simulate_estimate(w, draws=500),
    "chapter2": c2_rate_shock.simulate_estimate,
    "chapter3": c3_burden.simulate_estimate,
    "chapter4": c4_supply.simulate_estimate,
    "chapter5": lambda w: c5_ranking.simulate_estimate(w, draws=500),
    "chapter6": lambda w: c6_buyers.simulate_estimate(w, replicates=100),
    "chapter7": c7_migration.simulate_estimate,
    "chapter8": lambda w: c8_decision.simulate_estimate(w, draws=200),
}

# What each estimator's rows mean on the page, and which condition knob it is expected to fail under.
ESTIMATOR_NOTES: dict[str, str] = {
    "anchored_payment_share": "the national payment share in the latest year; the interval is the Monte Carlo over the census margins",
    "self_report_correction": "the census value over the transaction value against the planted self report factor",
    "anchored_level": "the anchored national value over the true one in the latest year",
    "lock_in_did": "turnover on lock in intensity with metro and year effects; the flag is the placebo covering zero",
    "lock_in_placebo": "the pre period placebo of the lock in regression against zero",
    "burden_changepoint": "the PELT changepoint nearest the planted step; the flag is a hit within a year",
    "severe_share": "the severely burdened share with its block bootstrap interval",
    "supply_controlled": "the building rate coefficient with the demand control",
    "supply_uncontrolled": "the building rate coefficient without the demand control",
    "ranking_adjusted": "rank correlation of the adjusted ranking with the true one; the flag is the raw ranking's",
    "bracket_interpolation": "mean absolute error of the affordable share against the exact share",
    "borrower_ratio_shift": "the borrower income ratio shift after the shock with its lender bootstrap interval",
    "under_35_shift": "the under 35 share shift after the shock with its lender bootstrap interval",
    "migration_effect": "the price response to the migration shock; the flag is the placebo excluding zero",
    "migration_placebo": "the pre trend placebo of the migration regression against zero",
    "migration_naive": "growth on the pandemic migration level with no pre pandemic control, against the same truth",
    "breakeven_horizon": "mean absolute error of the breakeven year against the realised path; the flag is the interval coverage",
}


def _code_digest() -> str:
    """A digest of the simulator source, so a changed generator misses the cache."""
    path = Path(sim_metros.__file__)
    h = hashlib.sha256(path.read_bytes())
    for module in (
        c1_definition,
        c2_rate_shock,
        c3_burden,
        c4_supply,
        c5_ranking,
        c6_buyers,
        c7_migration,
        c8_decision,
    ):
        h.update(Path(module.__file__).read_bytes())
    return h.hexdigest()[:12]


def cache_key(condition: Condition, seed: int, code: str) -> str:
    return hashlib.sha256(
        json.dumps({"condition": condition.model_dump(), "seed": seed, "code": code}, sort_keys=True).encode()
    ).hexdigest()[:20]


def grade_world(condition: Condition, seed: int) -> list[dict[str, Any]]:
    world = generate(condition, seed)
    rows: list[dict[str, Any]] = []
    for name, estimator in sorted(ESTIMATORS.items()):
        for g in estimator(world):
            row = asdict(g)
            row.update(
                {
                    "chapter": name,
                    "condition": condition.name,
                    "seed": seed,
                    "error": g.error,
                    "covered": g.covered,
                }
            )
            row.update(
                {
                    k: getattr(condition, k)
                    for k in ("demand_strength", "supply_dispersion", "reverse_causality", "noise")
                }
            )
            rows.append(row)
    return rows


def _job(args: tuple[dict[str, Any], int, str | None, str]) -> list[dict[str, Any]]:
    condition_payload, seed, cache_dir, code = args
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("POLARS_MAX_THREADS", "1")
    condition = Condition(**condition_payload)
    if cache_dir is not None:
        path = Path(cache_dir) / f"{cache_key(condition, seed, code)}.json"
        if path.exists():
            loaded: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
            return loaded
    rows = grade_world(condition, seed)
    if cache_dir is not None:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        (Path(cache_dir) / f"{cache_key(condition, seed, code)}.json").write_text(
            json.dumps(rows, sort_keys=True), encoding="utf-8"
        )
    return rows


def run_study(
    seeds: int,
    *,
    workers: int = 2,
    cache_dir: Path | None = None,
    which: Iterable[Condition] | None = None,
    first_seed: int = 1,
) -> list[dict[str, Any]]:
    conds = list(which) if which is not None else conditions()
    code = _code_digest()
    jobs = [
        (c.model_dump(), s, str(cache_dir) if cache_dir else None, code)
        for c in conds
        for s in range(first_seed, first_seed + seeds)
    ]
    rows: list[dict[str, Any]] = []
    if workers <= 1:
        for job in jobs:
            rows.extend(_job(job))
        return rows
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(_job, jobs, chunksize=1):
            rows.extend(result)
    return rows


def summarise(records: pl.DataFrame) -> pl.DataFrame:
    """Per condition and estimator: bias, root mean squared error, coverage, mean flag, seeds."""
    return (
        records.with_columns(pl.col("covered").cast(pl.Float64), pl.col("flag").cast(pl.Float64))
        .group_by(
            ["condition", "demand_strength", "supply_dispersion", "reverse_causality", "noise", "estimator"]
        )
        .agg(
            pl.len().alias("seeds"),
            pl.col("error").mean().alias("bias"),
            (pl.col("error") ** 2).mean().sqrt().alias("rmse"),
            pl.col("error").abs().mean().alias("mae"),
            pl.col("covered").mean().alias("coverage"),
            pl.col("flag").mean().alias("flag_rate"),
            pl.col("truth").mean().alias("truth"),
            pl.col("estimate").mean().alias("estimate"),
        )
        .sort(["estimator", "condition"])
    )


def by_estimator(summary: pl.DataFrame) -> pl.DataFrame:
    """Across conditions: the worst bias and the lowest coverage per estimator, with the condition named."""
    rows: list[dict[str, Any]] = []
    for name, sub in sorted(summary.group_by("estimator"), key=lambda kv: str(kv[0][0])):
        worst_bias = sub.sort(pl.col("bias").abs(), descending=True, nulls_last=True).row(0, named=True)
        with_cov = sub.filter(pl.col("coverage").is_not_null())
        worst_cov = with_cov.sort("coverage").row(0, named=True) if with_cov.height else None
        rows.append(
            {
                "estimator": str(name[0]),
                "conditions": sub.height,
                "mean_bias": float(sub["bias"].mean()),
                "mean_rmse": float(sub["rmse"].mean()),
                "mean_coverage": float(with_cov["coverage"].mean()) if with_cov.height else None,
                "mean_flag_rate": float(sub["flag_rate"].mean())
                if sub["flag_rate"].is_not_null().any()
                else None,
                "worst_bias": float(worst_bias["bias"]),
                "worst_bias_condition": str(worst_bias["condition"]),
                "lowest_coverage": float(worst_cov["coverage"]) if worst_cov else None,
                "lowest_coverage_condition": str(worst_cov["condition"]) if worst_cov else None,
            }
        )
    return pl.DataFrame(rows)
