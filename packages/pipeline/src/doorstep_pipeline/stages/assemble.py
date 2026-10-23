"""Stage: merge every stage's partial manifest into results/manifest.json.

Each stage writes results/<stage>/manifest.json so a rerun of one stage never touches another's
numbers. This stage merges them in a fixed order, adds the policy constants, the palette validator's
summary, the separate client verification of the live API, the load test, the live browser check and
the build's own facts as recorded values, and lists the chapters the story includes. It writes the one
file every document, the story, the memo and the site render from.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from doorstep_core.config import (
    AFFORDABLE_LINES,
    ANCHOR_YEARS,
    DOWN_PAYMENT_SHARES,
    LOCK_IN_THRESHOLDS,
    POLICY,
    SAVING_RATES,
    SEVERE_LINES,
    SUPPLY_WINDOWS,
)
from doorstep_core.manifest import Manifest, Scribe
from doorstep_core.paths import Paths

from doorstep_pipeline import checklist
from doorstep_pipeline.common import DEMONSTRATION_SEED, as_of

ORDER = ("data", "simulate", "recovery", "warehouse", "metrics", "chapters", "exports")
"""The stage order the pipeline runs in. The Makefile's pipeline target and the rederive follow it."""

STORY_CHAPTERS = ("definition", "rate_shock", "burden", "supply", "ranking", "buyers", "migration", "decision")


def run(p: Paths) -> Manifest:
    merged = Manifest(as_of=as_of(), seed=DEMONSTRATION_SEED)
    present: list[str] = []
    for name in ORDER:
        path = p.results / name / "manifest.json"
        if path.exists():
            merged.merge(Manifest.load(path))
            present.append(name)
    _policy(merged)
    _palette(merged, p.root)
    _deploy(merged, p.results / "deploy" / "verification.json", p.results / "deploy" / "replay.json")
    _latency(merged, p.results / "latency")
    _live_check(merged, p.results / "live_check.json")
    _story(merged)
    _build(merged, p.root, present)
    _checklist(merged, p.root)
    merged.save(p.manifest)
    return merged


def _checklist(manifest: Manifest, root: Path) -> None:
    """The eighteen lines of the definition of done, each marked with its evidence."""
    facts = checklist.repository_facts(root)
    items = checklist.evaluate(manifest, facts)
    w = Scribe(
        manifest, source="mixed", population="the definition of done", origin="doorstep_pipeline.checklist"
    )
    for item in items:
        w.put(f"checklist.{item.number}.status", "done" if item.done else "not done", "text")
        w.put(f"checklist.{item.number}.text", item.text, "text")
        w.put(f"checklist.{item.number}.evidence", item.evidence, "text")
    missing = checklist.missing_steps(items)
    w.put("checklist.done", len(items) - len(missing), "int")
    w.put("checklist.total", len(items), "int")
    w.put("checklist.missing", ", ".join(str(n) for n in missing) if missing else "none", "text")
    w.put("build.commits", int(facts["commits"]), "int")
    w.put("build.decisions", int(facts["decisions"]), "int")
    w.put("build.reversals", int(facts["reversals"]), "int")


def _policy(manifest: Manifest) -> None:
    w = Scribe(
        manifest, source="static", population="the analysis policy", origin="doorstep_core.config.POLICY"
    )
    w.put("policy.window_start_year", str(POLICY.window_start_year), "text")
    w.put("policy.acs_first_year", str(POLICY.acs_first_year), "text")
    w.put("policy.hmda_first_year", str(POLICY.hmda_first_year), "text")
    w.put("policy.fit_years", f"{POLICY.fit_first_year} to {POLICY.fit_last_year}", "text")
    w.put("policy.test_first_year", str(POLICY.test_first_year), "text")
    w.put("policy.anchor_year", str(POLICY.anchor_year), "text")
    w.put("policy.affordable_line", POLICY.affordable_line, "pct0")
    w.put("policy.affordable_sensitivity", POLICY.affordable_sensitivity, "pct0")
    w.put("policy.severe_line", POLICY.severe_line, "pct0")
    w.put("policy.severe_share_line", POLICY.severe_share_line, "pct0")
    w.put("policy.down_payment_share", POLICY.down_payment_share, "pct0")
    w.put("policy.loan_term_years", POLICY.loan_term_years, "int")
    w.put("policy.saving_rate", POLICY.saving_rate, "pct0")
    w.put("policy.lock_in_threshold", POLICY.lock_in_threshold, "rate2")
    w.put("policy.lock_in_years", f"{POLICY.lock_in_years[0]} to {POLICY.lock_in_years[1]}", "text")
    w.put(
        "policy.turnover_base_years",
        f"{POLICY.turnover_base_years[0]} and {POLICY.turnover_base_years[1]}",
        "text",
    )
    w.put("policy.turnover_test_first_year", str(POLICY.turnover_test_first_year), "text")
    w.put("policy.supply_window_years", POLICY.supply_window_years, "int")
    w.put("policy.migration_years", f"{POLICY.migration_years[0]} and {POLICY.migration_years[1]}", "text")
    w.put(
        "policy.migration_pre_years",
        f"{POLICY.migration_pre_years[0]} and {POLICY.migration_pre_years[1]}",
        "text",
    )
    w.put("policy.migration_window", f"{POLICY.migration_window[0]} to {POLICY.migration_window[1]}", "text")
    w.put(
        "policy.migration_placebo_window",
        f"{POLICY.migration_placebo_window[0]} to {POLICY.migration_placebo_window[1]}",
        "text",
    )
    w.put("policy.synthetic_control_first_period", POLICY.synthetic_control_first_period, "text")
    w.put("policy.synthetic_control_metros", POLICY.synthetic_control_metros, "int")
    w.put("policy.breakeven_horizon_years", POLICY.breakeven_horizon_years, "int")
    for key, value in POLICY.breakeven_cost_model.items():
        w.put(f"policy.cost.{key}", value, "pct1" if key != "rent_to_price_default" else "pct1")
    w.put("policy.bootstrap_replicates", POLICY.bootstrap_replicates, "int")
    w.put("policy.monte_carlo_draws", POLICY.monte_carlo_draws, "int")
    w.put("policy.bh_q", POLICY.bh_q, "float2")
    w.put("policy.interval_level", POLICY.interval_level, "pct0")
    w.put("policy.min_metro_households", POLICY.min_metro_households, "int")
    w.put("policy.largest_metros", POLICY.largest_metros, "int")
    w.put("policy.seed", str(POLICY.seed), "text")
    w.put("policy.anchor_years", _listed([str(y) for y in ANCHOR_YEARS]), "text")
    w.put("policy.affordable_lines", _listed([f"{x:.0%}" for x in AFFORDABLE_LINES]), "text")
    w.put("policy.down_payment_shares", _listed([f"{x:.0%}" for x in DOWN_PAYMENT_SHARES]), "text")
    w.put("policy.lock_in_thresholds", _listed([f"{x:.1f}%" for x in LOCK_IN_THRESHOLDS]), "text")
    w.put("policy.supply_windows", _listed([str(x) for x in SUPPLY_WINDOWS]), "text")
    w.put("policy.saving_rates", _listed([f"{x:.0%}" for x in SAVING_RATES]), "text")
    w.put("policy.severe_lines", _listed([f"{x:.0%}" for x in SEVERE_LINES]), "text")


def _listed(items: list[str]) -> str:
    """Items joined the way prose lists them: a, b and c."""
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _palette(manifest: Manifest, root: Path) -> None:
    script = root / "scripts" / "validate_palette.js"
    config = root / "web" / "src" / "theme" / "palette.json"
    w = Scribe(
        manifest,
        source="static",
        population="web/src/theme/palette.json",
        origin="scripts/validate_palette.js",
    )
    if not script.exists() or not config.exists():
        w.put("palette.validated", "not run", "text")
        return
    try:
        proc = subprocess.run(
            ["node", str(script), "--config", str(config), "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        summary = json.loads(proc.stdout)
    except (OSError, json.JSONDecodeError):
        w.put("palette.validated", "validator did not return a summary", "text")
        return
    failures = int(summary.get("failures", 0))
    w.put("palette.failures", failures, "int")
    w.put("palette.validated", "green" if failures == 0 else "failing", "text")
    for mode in ("light", "dark"):
        m = summary.get("modes", {}).get(mode, {})
        for key, fmt in (
            ("worstAdjacentCvd", "float1"),
            ("worstAdjacentNormal", "float1"),
            ("worstSlotContrast", "float2"),
            ("worstCardContrast", "float2"),
            ("firstThreeAllPairsCvd", "float1"),
        ):
            if key in m:
                w.put(f"palette.{mode}.{key}", float(m[key]), fmt)


def _deploy(manifest: Manifest, path: Path, replay: Path) -> None:
    """The separate client verification of the live API, recorded as it was seen."""
    w = Scribe(
        manifest,
        source="recorded",
        population="the live API, checked from a separate client",
        origin="deploy/verify.ps1",
    )
    if not path.exists():
        w.put("deploy.status", "not yet deployed", "text")
        w.put("deploy.base_url", "not yet deployed", "text")
        w.put("deploy.passed", "no", "text")
        return
    seen = json.loads(path.read_text(encoding="utf-8-sig"))
    w.put("deploy.status", "deployed and verified" if seen.get("passed") else "verification failed", "text")
    for key in ("base_url", "client", "checked_at", "check_id", "metro", "cbsa_code", "quarter"):
        w.put(f"deploy.{key}", str(seen.get(key, "")), "text")
    health = seen.get("health", {})
    w.put("deploy.health_status", str(health.get("status", "")), "text")
    w.put("deploy.health_database", str(health.get("database", "")), "text")
    w.put("deploy.model_version", str(health.get("model_version", "")), "text")
    w.put("deploy.metros", int(health.get("metros", 0) or 0), "int")
    w.put("deploy.latest_period", str(health.get("latest_period", "")), "text")
    rate = health.get("rate_default")
    w.put("deploy.rate_default", float(rate) if rate is not None else None, "rate2")
    w.put("deploy.income", float(seen.get("income", 0.0) or 0.0), "usd0")
    w.put("deploy.payment_share", float(seen.get("payment_share", 0.0) or 0.0), "pct1")
    w.put("deploy.affordable_price", float(seen.get("affordable_price", 0.0) or 0.0), "usd0")
    share = seen.get("affordable_share")
    w.put("deploy.affordable_share", float(share) if share is not None else None, "pct0")
    years = seen.get("breakeven_years")
    w.put("deploy.breakeven_years", float(years) if years is not None else None, "years1")
    score = seen.get("score") or {}
    realized = score.get("realized_payment_share") if score else None
    w.put("deploy.realized_payment_share", float(realized) if realized is not None else None, "pct1")
    error = score.get("absolute_error") if score else None
    w.put("deploy.absolute_error", float(error) if error is not None else None, "pts1")
    w.put("deploy.audit_before_response", "yes" if seen.get("audit_before_response") else "no", "text")
    w.put("deploy.statement_present", "yes" if seen.get("statement_present") else "no", "text")
    w.put("deploy.passed", "yes" if seen.get("passed") else "no", "text")
    if replay.exists():
        r = json.loads(replay.read_text(encoding="utf-8-sig"))
        w.put("deploy.demo_checks", int(r.get("checks_made", 0)), "int")
        card = r.get("scorecard", {})
        w.put("deploy.demo_scored", int(card.get("scored", 0) or 0), "int")
        mae = card.get("mean_absolute_error")
        w.put("deploy.demo_mae", float(mae) if mae is not None else None, "pts1")
        price_move = card.get("mean_price_move")
        w.put("deploy.demo_price_move", float(price_move) if price_move is not None else None, "pct1")


def _latency(manifest: Manifest, folder: Path) -> None:
    found = 0
    for label in ("local", "live"):
        path = folder / f"{label}.json"
        w = Scribe(
            manifest,
            source="recorded",
            population=f"the {label} API under the load test",
            origin="scripts/load_test.py",
        )
        if not path.exists():
            w.put(f"latency.{label}.status", "not measured", "text")
            continue
        found += 1
        seen = json.loads(path.read_text(encoding="utf-8-sig"))
        w.put(f"latency.{label}.status", "measured", "text")
        w.put(f"latency.{label}.base_url", str(seen["base_url"]), "text")
        w.put(f"latency.{label}.measured_at", str(seen["measured_at"]), "text")
        w.put(f"latency.{label}.requests", int(seen["requests"]), "int")
        w.put(f"latency.{label}.concurrency", int(seen["concurrency"]), "int")
        w.put(f"latency.{label}.metros", int(seen.get("metros", 0) or 0), "int")
        w.put(f"latency.{label}.first_request_ms", float(seen["first_request_ms"]), "ms")
        for kind in ("check", "read"):
            for stat in ("p50_ms", "p99_ms", "max_ms"):
                w.put(f"latency.{label}.{kind}.{stat}", float(seen[kind][stat]), "ms")
        w.put(f"latency.{label}.burst_max_ms", float(seen["burst_check_max_ms"]), "ms")
    Scribe(
        manifest, source="recorded", population="the load test files found", origin="stages/assemble.py"
    ).put("latency.measurements", found, "int")


def _live_check(manifest: Manifest, path: Path) -> None:
    """The live site and API opened in a real browser after the deploy, as recorded."""
    w = Scribe(
        manifest,
        source="recorded",
        population="the live site and API in a real browser",
        origin="scripts/live_check.py",
    )
    seen = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    w.put(
        "live.status",
        ("passed" if seen.get("passed") else "failed") if path.exists() else "not checked",
        "text",
    )
    w.put("live.checked_at", str(seen.get("checked_at", "")) or "not yet", "text")
    w.put("live.browser", str(seen.get("browser", "")) or "no browser yet", "text")
    w.put("live.site_url", str(seen.get("site_url", "")) or "not yet published", "text")
    w.put("live.routes_loaded", int(seen.get("routes_loaded", 0)), "int")
    w.put("live.routes_total", int(seen.get("routes_total", 0)), "int")
    w.put("live.check_id", str(seen.get("check_id", "")) or "none", "text")
    w.put("live.asleep_outcome", str(seen.get("asleep_outcome", "")) or "not observed", "text")


def _story(manifest: Manifest) -> None:
    w = Scribe(manifest, source="static", population="the story's chapter list", origin="stages/assemble.py")
    included = [c for c in STORY_CHAPTERS if f"chart.{c}" in manifest.figures]
    for i, chapter in enumerate(included, start=1):
        w.put(f"story.chapter.{i}", chapter, "text")
    w.put("story.chapters", len(included), "int")


def _build(manifest: Manifest, root: Path, present: list[str]) -> None:
    w = Scribe(manifest, source="static", population="the repository", origin="stages/assemble.py")
    w.put("build.stages_present", ", ".join(present) if present else "none", "text")
    w.put("build.stages_missing", ", ".join(s for s in ORDER if s not in present) or "none", "text")
    import tomllib

    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8")).get("project", {})
    w.put("build.version", f"v{project.get('version', '0.0.0')}", "text")
