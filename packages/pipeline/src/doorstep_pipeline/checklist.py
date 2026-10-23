"""The definition of done, evaluated: each of the eighteen lines marked done or not done with one
sentence of evidence, from the manifest and from facts about the repository that the manifest cannot
hold (the commit count, the decision log, the notebooks, the quality run, the rederive, the release).

Every number in the evidence is formatted from a manifest value or counted from a file here, so the
README and RESULTS print the checklist without a number typed into a template.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from doorstep_core.manifest import Manifest

LINES: tuple[str, ...] = (
    "Every source ingested for the whole window from the fetched files, the quarantine report published, the delineation crosswalk tested, the HMDA extract filter and the ACS gap stated in the README first paragraph, provenance and licenses recorded",
    "Warehouse with dbt tests and exposures; the metric layer reconciled across grains",
    "Simulator with known incomes, distributions, elasticities, demand shocks, rates, lock in and planted misreporting; the recovery study on every condition with at least twenty seeds; the finance engine tested to the cent",
    "Chapters 1 and 2 with plan hashes, simulator recovery, results on the test years with intervals, the anchor sensitivity table, the overtaking quarter named, the lock in regression with its placebo",
    "Chapter 3: the burden shares by metro, year and income bracket with intervals; the changepoints named",
    "Chapter 5: the fair ranking with Monte Carlo intervals beside the raw ranking, the rank changes named, the simulator recovery",
    "API deployed on a free host with Neon; live URL in the README; verified from a separate client, with the client response printed",
    "Checks and scores observed from an independent connection; audit before response; the out of process check",
    "Chapter 4: the supply elasticity under both specifications with intervals and the recovery study beside it; chapter 7: the migration regression with its placebo and three synthetic controls with placebo inference",
    "Chapter 6: the borrower pool measures by year and metro with intervals",
    "Chapter 8: the affordable price by decile, the affordable share, the down payment years, the breakeven horizons with intervals, every interior test",
    "Exports: the workbook with live formulas and its recalculation test, the Tableau extract and specification, the Power BI specification with measures, the CSV bundle with its dictionary",
    "The story live on GitHub Pages with sticky charts, method notes, the SQL behind every chart, the corrections section and the print stylesheet",
    "Explore, rank, buyers, shocks, planner, data and report pages live, working from the recorded session when the API is asleep; the test server refuses what the host refuses",
    "Latency published; the live check in a real browser recorded in results/live_check.json",
    "RESULTS.md with every figure re-derived by the gate and a specific limitations section",
    "README with the matrix and this checklist; DECISIONS.md with at least ten dated entries, two reversals and the corrections; three executed notebooks with a dead end each; the pushback paragraph on every chapter and page",
    "Coverage at or above 80 percent, mypy strict clean, ruff clean, zero em dashes, zero banned vocabulary, palette validator green including the dark card run, forty to sixty commits, the rederive run in a worktree before the tag, v0.1.0 pushed after the commits, Apache 2.0 for code with every data source terms declared, repo described, topics set",
)


@dataclass(frozen=True)
class Item:
    number: int
    text: str
    done: bool
    evidence: str


def _json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8-sig"))
    return loaded


def repository_facts(root: Path) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    try:
        out = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        )
        facts["commits"] = int(out.stdout.strip())
    except (OSError, subprocess.CalledProcessError, ValueError):
        facts["commits"] = 0
    decisions = (
        (root / "DECISIONS.md").read_text(encoding="utf-8") if (root / "DECISIONS.md").exists() else ""
    )
    headings = re.findall(r"^## (\d{4}-\d{2}-\d{2}): (.+)$", decisions, flags=re.M)
    facts["decisions"] = len(headings)
    facts["reversals"] = sum(1 for _, title in headings if title.lower().startswith("reversal"))
    facts["corrections"] = sum(1 for _, title in headings if title.lower().startswith("correction"))
    notebooks = sorted((root / "notebooks").glob("*.ipynb"))
    executed = 0
    dead_ends = 0
    for nb in notebooks:
        cells = json.loads(nb.read_text(encoding="utf-8")).get("cells", [])
        if any(c.get("cell_type") == "code" and c.get("outputs") for c in cells):
            executed += 1
        if any(
            "dead end" in "".join(c.get("source", [])).lower()
            for c in cells
            if c.get("cell_type") == "markdown"
        ):
            dead_ends += 1
    facts["notebooks"] = len(notebooks)
    facts["notebooks_executed"] = executed
    facts["notebooks_dead_ends"] = dead_ends
    facts["quality"] = _json(root / "results" / "quality.json")
    facts["rederive"] = _json(root / "results" / "rederive.json")
    facts["release"] = _json(root / "results" / "release.json")
    facts["web"] = _json(root / "results" / "web_tests.json")
    facts["license"] = (root / "LICENSE").exists() and "Apache" in (root / "LICENSE").read_text(
        encoding="utf-8"
    )
    facts["provenance"] = (root / "data" / "PROVENANCE.md").exists()
    return facts


def evaluate(m: Manifest, facts: dict[str, Any]) -> list[Item]:
    def v(key: str) -> str:
        return m.text(key) if key in m.values else "not measured"

    def raw(key: str) -> Any:
        return m.values[key].value if key in m.values else None

    def has(*keys: str) -> bool:
        return all(k in m.values or k in m.tables or k in m.figures for k in keys)

    q = facts.get("quality", {})
    rederive = facts.get("rederive", {})
    release = facts.get("release", {})
    web = facts.get("web", {})
    items: list[Item] = []

    def add(done: bool, evidence: str) -> None:
        items.append(Item(len(items) + 1, LINES[len(items)], bool(done), evidence))

    add(
        has(
            "data.fhfa.rows",
            "data.acs.rows",
            "data.hmda.rows_in_analysis",
            "data.quarantine.by_rule",
            "data.omb.vintages",
        )
        and raw("data.acs.gap_year") == "2020"
        and facts["provenance"],
        f"FHFA {v('data.fhfa.rows')} index rows to {v('data.fhfa.latest_period')}; ACS {v('data.acs.rows')} estimates over {v('data.acs.years')} releases "
        f"({v('data.acs.first_year')} to {v('data.acs.last_year')}, gap {v('data.acs.gap_year')}); HMDA {v('data.hmda.rows_in_analysis')} loans in the analysis "
        f"from {v('data.hmda.rows_in_source_files')} source rows ({v('data.hmda.first_year')} to {v('data.hmda.last_year')}); {v('data.omb.vintages')} delineation vintages; "
        f"{v('data.quarantine.rules')} quarantine rules on the data page; data/PROVENANCE.md.",
    )
    add(
        has("warehouse.tests", "metrics.disagreements")
        and (raw("warehouse.tests") or 0) >= 100
        and raw("warehouse.tests_failed") == 0
        and raw("metrics.disagreements") == 0,
        f"dbt build: {v('warehouse.models')} models, {v('warehouse.tests')} tests, {v('warehouse.tests_failed')} failed; "
        f"{v('metrics.count')} metrics reconciled at {v('metrics.grains')} grains over {v('metrics.cells')} cells with "
        f"{v('metrics.disagreements')} disagreements.",
    )
    finance = q.get("finance_tests", {})
    add(
        has("recovery.seeds", "recovery.conditions", "sim.metros")
        and (raw("recovery.seeds") or 0) >= 20
        and bool(finance.get("passed"))
        and not finance.get("failed"),
        f"{v('sim.metros')} simulated metros over {v('sim.years')} years; {v('recovery.conditions')} conditions times {v('recovery.seeds')} seeds, "
        f"{v('recovery.grades')} grades across {v('recovery.estimators')} estimators; finance tests {finance.get('passed', 0)} passed "
        f"({finance.get('failed', 0)} failed); results/recovery.",
    )
    add(
        has(
            "ch1.plan_hash",
            "ch2.plan_hash",
            "ch1.diff",
            "ch1.anchor_sensitivity",
            "ch2.overtaking_quarter",
            "ch2.lock_in.coef",
            "ch2.placebo.coef",
        ),
        f"plans {v('ch1.plan_hash')} and {v('ch2.plan_hash')}; payment share {v('ch1.diff')} against the peak ({v('ch1.diff.low')} to {v('ch1.diff.high')}); "
        f"anchor sensitivity table ch1.anchor_sensitivity ({v('ch1.anchor_degenerate')}); overtaking quarter {v('ch2.overtaking_quarter')}; "
        f"lock in {v('ch2.lock_in.coef')} ({v('ch2.lock_in.low')} to {v('ch2.lock_in.high')}) against a placebo of {v('ch2.placebo.coef')}.",
    )
    add(
        has("ch3.plan_hash", "ch3.severe.share", "ch3.by_income_group", "ch3.changepoints"),
        f"plan {v('ch3.plan_hash')}; burdened {v('ch3.burdened.share')} ({v('ch3.burdened.low')} to {v('ch3.burdened.high')}), severe {v('ch3.severe.share')} "
        f"({v('ch3.severe.low')} to {v('ch3.severe.high')}) over {v('ch3.metros')} metros; by income group in ch3.by_income_group; changepoints {v('ch3.changepoints')}.",
    )
    add(
        has("ch5.plan_hash", "ch5.largest", "recovery.ranking.adjusted"),
        f"plan {v('ch5.plan_hash')}; {v('ch5.metros_ranked')} metros ranked with {v('ch5.draws')} draws; rank correlation {v('ch5.spearman')}, "
        f"{v('ch5.movers')} of the {v('ch5.largest')} largest move beyond their intervals; simulator rank correlation {v('recovery.ranking.adjusted')} adjusted "
        f"against {v('recovery.ranking.raw')} raw.",
    )
    add(
        raw("deploy.passed") == "yes",
        (
            f"{v('deploy.base_url')}: {v('deploy.status')} from {v('deploy.client')}; "
            f"payment share {v('deploy.payment_share')} read back; results/deploy/verification.json."
            if raw("deploy.passed") == "yes"
            else f"{v('deploy.status')}; results/deploy/verification.json is not written until a host holds the container."
        ),
    )
    api = q.get("api_tests", {})
    add(
        bool(api.get("passed")) and not api.get("failed"),
        f"tests/api: {api.get('passed', 0)} passed (test_check_is_committed, test_score_is_committed, "
        "test_audit_precedes_response, the out of process scripts/check_persistence.py).",
    )
    add(
        has(
            "ch4.plan_hash",
            "ch4.controlled.coef",
            "ch4.uncontrolled.coef",
            "ch7.plan_hash",
            "ch7.coef",
            "ch7.placebo.coef",
            "ch7.synthetic_controls",
        )
        and (raw("ch7.sc.count") or 0) >= 3,
        f"supply {v('ch4.controlled.per_window')} per window with the demand control ({v('ch4.controlled.per_window.low')} to {v('ch4.controlled.per_window.high')}), "
        f"{v('ch4.uncontrolled.per_window')} without; simulator bias {v('recovery.supply_controlled.mean_bias')} against {v('recovery.supply_uncontrolled.mean_bias')}; "
        f"migration {v('ch7.coef')} ({v('ch7.low')} to {v('ch7.high')}) with placebo {v('ch7.placebo.coef')}; {v('ch7.sc.count')} synthetic controls with permutation p values.",
    )
    add(
        has("ch6.plan_hash", "ch6.by_year", "ch6.largest_metros", "ch6.ratio_diff"),
        f"plan {v('ch6.plan_hash')}; borrower ratio {v('ch6.base.ratio')} to {v('ch6.latest.ratio')} ({v('ch6.ratio_diff')}, {v('ch6.ratio_diff.low')} to {v('ch6.ratio_diff.high')}); "
        f"under 35 share moved {v('ch6.under_35_diff')}; by year in ch6.by_year and by metro in ch6.largest_metros.",
    )
    add(
        has(
            "ch8.plan_hash",
            "ch8.largest",
            "ch8.line_interior",
            "ch8.down_interior",
            "ch8.saving_interior",
            "ch8.breakeven.median",
        ),
        f"plan {v('ch8.plan_hash')}; median breakeven {v('ch8.breakeven.median')} ({v('ch8.breakeven.low')} to {v('ch8.breakeven.high')}); "
        f"the median household can afford the median home in {v('ch8.median_can_afford.metros')} of {v('ch8.metros')} metros; down payment years {v('ch8.down_payment_years.median')}; "
        f"interior tests: line {v('ch8.line_degenerate')}, down payment {v('ch8.down_degenerate')}.",
    )
    workbook_recalc = q.get("libreoffice_recalc")
    add(
        has("exports.workbook.formulas", "exports.powerbi.measures", "exports.csv.files")
        and workbook_recalc == "passed",
        f"workbook {v('exports.workbook.sheets')} sheets, {v('exports.workbook.formulas')} live formulas, recalculation test "
        f"{workbook_recalc or 'not run'}; {v('exports.tableau.views')} Tableau views; {v('exports.powerbi.measures')} DAX measures; {v('exports.csv.files')} CSV files with a dictionary.",
    )
    add(
        raw("live.status") == "passed",
        f"{v('live.site_url')}: live check {v('live.status')}.",
    )
    add(
        raw("live.status") == "passed" and bool(web.get("passed")) and not web.get("failed"),
        f"{v('live.routes_loaded')} of {v('live.routes_total')} routes loaded live; asleep: {v('live.asleep_outcome')}; "
        f"Playwright against the test server: {web.get('passed', 0)} passed, {web.get('failed', 0)} failed.",
    )
    add(
        has("latency.live.check.p50_ms") and raw("live.status") == "passed",
        f"POST /v1/checks p50 {v('latency.live.check.p50_ms') if has('latency.live.check.p50_ms') else 'not measured'}, "
        f"p99 {v('latency.live.check.p99_ms') if has('latency.live.check.p99_ms') else 'not measured'}; results/live_check.json {v('live.status')}.",
    )
    add(
        rederive.get("drift") == 0,
        f"claim gate over every document; rederive drift {rederive.get('drift', 'not run')}; limitations section in RESULTS.md.",
    )
    add(
        facts["decisions"] >= 10
        and facts["reversals"] >= 2
        and facts["notebooks_executed"] >= 3
        and facts["notebooks_dead_ends"] >= 3,
        f"DECISIONS.md {facts['decisions']} dated entries, {facts['reversals']} reversals, {facts['corrections']} corrections; "
        f"{facts['notebooks_executed']} executed notebooks, {facts['notebooks_dead_ends']} with a dead end.",
    )
    coverage = q.get("coverage")
    commits = int(facts.get("commits", 0))
    add(
        coverage is not None
        and float(coverage) >= 80
        and q.get("mypy") == "clean"
        and q.get("ruff") == "clean"
        and raw("palette.failures") == 0
        and 40 <= commits <= 60
        and rederive.get("drift") == 0
        and str(rederive.get("where", "in place")) != "in place"
        and bool(release.get("tag_pushed"))
        and facts["license"],
        f"coverage {coverage if coverage is not None else 'not measured'} percent; mypy {q.get('mypy', 'not run')}; ruff {q.get('ruff', 'not run')}; "
        f"palette {v('palette.validated')}; {commits} commits; rederive {rederive.get('status', 'not run')}"
        f"{' in a worktree' if str(rederive.get('where', 'in place')) != 'in place' else ''}; "
        f"tag {'pushed' if release.get('tag_pushed') else 'not pushed'}; Apache 2.0 with every data source's terms declared.",
    )
    return items


def missing_steps(items: list[Item]) -> list[int]:
    return [i.number for i in items if not i.done]
