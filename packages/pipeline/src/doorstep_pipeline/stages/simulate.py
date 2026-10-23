"""The demonstration world: one seeded world of the simulator with its truth tables, committed under data/sim."""

from __future__ import annotations

import json

import polars as pl
from doorstep_core.manifest import Manifest, Scribe
from doorstep_core.paths import Paths
from doorstep_sim.lenders import lender_loans
from doorstep_sim.metros import DEMONSTRATION, burden_by_income, generate

from doorstep_pipeline.common import DEMONSTRATION_SEED, new_partial, save_partial


def run(p: Paths) -> Manifest:
    world = generate(DEMONSTRATION, DEMONSTRATION_SEED)
    p.sim.mkdir(parents=True, exist_ok=True)
    world.metro_year.write_parquet(p.sim / "metro_year.parquet", compression="zstd")
    world.metro_quarter.write_parquet(p.sim / "metro_quarter.parquet", compression="zstd")
    world.brackets.write_parquet(p.sim / "brackets.parquet", compression="zstd")
    world.loans_year.write_parquet(p.sim / "loans_year.parquet", compression="zstd")
    world.rates.write_parquet(p.sim / "rates.parquet", compression="zstd")
    burden_by_income(world).write_parquet(p.sim / "burden_by_income.parquet", compression="zstd")
    loans = lender_loans(world)
    loans.write_parquet(p.sim / "lender_loans.parquet", compression="zstd")
    world.truth.metros.write_parquet(p.sim / "truth_metros.parquet", compression="zstd")
    t = world.truth
    truth_payload = {
        "beta_supply": t.beta_supply,
        "beta_demand": t.beta_demand,
        "reverse": t.reverse,
        "lock_in_response": t.lock_in_response,
        "burden_step_year": t.burden_step_year,
        "burden_step_size": t.burden_step_size,
        "rate_shock_year": t.rate_shock_year,
        "borrower_ratio_shift": t.borrower_ratio_shift,
    }
    (p.sim / "truth.json").write_text(
        json.dumps(truth_payload, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    (p.sim / "spec.json").write_text(
        json.dumps(
            {
                "condition": DEMONSTRATION.model_dump(),
                "seed": DEMONSTRATION_SEED,
                "first_year": world.first_year,
                "last_year": world.last_year,
            },
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    manifest = new_partial("simulate")
    s = Scribe(
        manifest,
        source="simulated",
        population="the demonstration world, sixty simulated metros",
        origin="stages/simulate.py",
        seed=DEMONSTRATION_SEED,
        condition=DEMONSTRATION.name,
    )
    s.put("sim.metros", int(world.metro_year["metro_id"].n_unique()), "int")
    s.put(
        "sim.micropolitan",
        int(world.metro_year.filter(pl.col("kind") == "micropolitan")["metro_id"].n_unique()),
        "int",
    )
    s.put("sim.states", int(world.metro_year["state"].n_unique()), "int")
    s.put("sim.first_year", world.first_year, "int")
    s.put("sim.last_year", world.last_year, "int")
    s.put("sim.years", world.last_year - world.first_year + 1, "int")
    s.put("sim.quarters", int(world.metro_quarter.height / world.metro_year["metro_id"].n_unique()), "int")
    s.put("sim.condition", DEMONSTRATION.name, "text")
    s.put("sim.beta_supply", t.beta_supply, "float3")
    s.put("sim.beta_demand", t.beta_demand, "float3")
    s.put("sim.reverse", t.reverse, "float1")
    s.put("sim.lock_in_response", t.lock_in_response, "float3")
    s.put("sim.burden_step_year", t.burden_step_year, "int")
    s.put("sim.burden_step_size", t.burden_step_size, "pts1")
    s.put("sim.borrower_ratio_shift", t.borrower_ratio_shift, "sfloat2")
    s.put("sim.rate_shock_year", t.rate_shock_year, "int")
    s.put("sim.loans", int(loans.height), "int")
    s.put("sim.lenders", int(loans["lei"].n_unique()), "int")
    s.put("sim.suppressed_cells", int(world.brackets["households"].null_count()), "int")
    s.put("sim.value_bias_sd", float(world.truth.metros["value_bias"].log().std()), "float3")
    save_partial(p, "simulate", manifest)
    return manifest
