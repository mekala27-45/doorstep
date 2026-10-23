"""Did the step run: tests that ask whether a chapter did the work its plan promises, separate from whether
the answer looks right. Every chapter is run once on the demonstration world, with small replicate counts,
and the result is inspected for the counts, the placebos and the searches the plan names."""

from __future__ import annotations

import numpy as np
import pytest
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
from doorstep_chapters.common import ChapterResult
from doorstep_chapters.panel import Panel, from_world
from doorstep_core.config import ANCHOR_YEARS, POLICY
from doorstep_finance.brackets import INCOME_BRACKETS, lognormal_bracket_counts, share_above
from doorstep_sim.metros import DEMONSTRATION, generate


@pytest.fixture(scope="module")
def panel() -> Panel:
    return from_world(generate(DEMONSTRATION, 11), POLICY, with_loans=True)


@pytest.fixture(scope="module")
def results(panel: Panel) -> dict[int, ChapterResult]:
    return {
        1: c1_definition.estimate(panel, POLICY, draws=200),
        2: c2_rate_shock.estimate(panel, POLICY),
        3: c3_burden.estimate(panel, POLICY, replicates=50),
        4: c4_supply.estimate(panel, POLICY),
        5: c5_ranking.estimate(panel, POLICY, draws=200),
        6: c6_buyers.estimate(panel, POLICY, replicates=30),
        7: c7_migration.estimate(panel, POLICY),
        8: c8_decision.estimate(panel, POLICY, draws=50),
    }


def test_every_chapter_publishes_a_message_a_method_and_a_pushback(results: dict[int, ChapterResult]) -> None:
    for number, r in results.items():
        assert r.number == number
        assert r.message and r.branch
        assert r.pushback and "." in r.pushback
        assert r.method and r.method.get("estimator")
        assert r.figure is not None and r.figure.sql.strip().lower().startswith(("select", "with"))
        assert r.reported_years


def test_the_monte_carlo_drew_as_many_times_as_asked(results: dict[int, ChapterResult]) -> None:
    assert results[1].values["ch1.draws"].value == 200
    assert results[5].values["ch5.draws"].value == 200
    assert results[8].values["ch8.draws"].value == 50


def test_the_bootstrap_replicated_as_many_times_as_asked(results: dict[int, ChapterResult]) -> None:
    assert results[3].values["ch3.replicates"].value == 50
    assert results[6].values["ch6.replicates"].value == 30


def test_every_regression_with_a_placebo_evaluated_it(results: dict[int, ChapterResult]) -> None:
    for key in (
        "ch2.placebo.coef",
        "ch2.placebo.low",
        "ch2.placebo.high",
        "ch7.placebo.coef",
        "ch7.placebo.low",
    ):
        number = int(key[2])
        value = results[number].values[key].value
        assert isinstance(value, float) and np.isfinite(value)
    assert results[4].values["ch4.uncontrolled.coef"].value != results[4].values["ch4.controlled.coef"].value


def test_the_synthetic_control_searched_every_donor(results: dict[int, ChapterResult], panel: Panel) -> None:
    r = results[7]
    count = int(r.values["ch7.sc.count"].value)
    assert count == POLICY.synthetic_control_metros
    frame = c7_migration.cross_section(panel, POLICY)
    cutoff = float(frame["migration_shock"].abs().median())
    donors = frame.filter(frame["migration_shock"].abs() <= cutoff).height
    for i in range(1, count + 1):
        searched = int(r.values[f"ch7.sc.{i}.donors"].value)
        assert searched in (donors, donors - 1)
        assert 0.0 <= float(r.values[f"ch7.sc.{i}.p"].value) <= 1.0


def test_the_ranking_counts_every_metropolitan_area_and_excludes_the_micropolitan(
    results: dict[int, ChapterResult], panel: Panel
) -> None:
    r = results[5]
    year = int(r.values["ch5.year"].value)
    rows = panel.metro_year.filter(panel.metro_year["year"] == year)
    metropolitan = rows.filter(rows["kind"] == "metropolitan")
    assert r.values["ch5.metros_ranked"].value == metropolitan.height
    assert r.values["ch5.micropolitan_excluded"].value == rows.filter(rows["kind"] == "micropolitan").height


def test_the_interpolation_touched_every_bracket() -> None:
    counts = lognormal_bracket_counts(np.log(60_000.0), 0.7, 10_000.0)
    assert len(counts) == len(INCOME_BRACKETS) + 1
    shares = [share_above(float(b), counts) for b in INCOME_BRACKETS]
    assert all(0.0 <= s <= 1.0 for s in shares)
    assert all(a >= b for a, b in zip(shares[:-1], shares[1:], strict=True))
    assert share_above(0.0, counts) == 1.0
    assert share_above(10 * INCOME_BRACKETS[-1], counts) < shares[-1]


def test_every_interior_test_printed_its_neighbours(results: dict[int, ChapterResult]) -> None:
    assert {r[0] for r in results[1].tables["ch1.anchor_sensitivity"].rows} == set(ANCHOR_YEARS)
    assert len(results[2].tables["ch2.threshold_interior"].rows) == 3
    assert len(results[3].tables["ch3.line_interior"].rows) == 3
    assert len(results[4].tables["ch4.window_interior"].rows) == 3
    assert len(results[8].tables["ch8.line_interior"].rows) == 4
    assert len(results[8].tables["ch8.down_interior"].rows) == 3
    assert len(results[8].tables["ch8.saving_interior"].rows) == 3
    for number, key in (
        (1, "ch1.anchor_degenerate"),
        (2, "ch2.threshold_degenerate"),
        (3, "ch3.line_degenerate"),
        (4, "ch4.window_degenerate"),
        (8, "ch8.line_degenerate"),
        (8, "ch8.down_degenerate"),
    ):
        assert results[number].values[key].value in ("stable", "degenerate")


def test_results_are_identical_across_hash_seeds(panel: Panel) -> None:
    """The chapter on the same panel twice, in processes with different PYTHONHASHSEED values, agrees to the byte."""
    import json
    import os
    import subprocess
    import sys

    code = (
        "import json, sys\n"
        "from doorstep_chapters import c5_ranking\n"
        "from doorstep_chapters.panel import from_world\n"
        "from doorstep_sim.metros import DEMONSTRATION, generate\n"
        "r = c5_ranking.estimate(from_world(generate(DEMONSTRATION, 11)), draws=100)\n"
        "print(json.dumps({k: v.value for k, v in sorted(r.values.items())}, sort_keys=True))\n"
    )
    outputs = []
    for seed in ("0", "12345"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        proc = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, env=env, check=True
        )
        outputs.append(json.loads(proc.stdout.strip().splitlines()[-1]))
    assert outputs[0] == outputs[1]
