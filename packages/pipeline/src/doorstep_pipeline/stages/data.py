"""Stage one: every fetched source into typed, flagged parquet under data/derived and data/hmda.

Each source goes through its contract: the typed frame, the quarantine rules with their counts, and
the digest over fields and rules. The small derived files are committed; the HMDA parquet is rebuilt
from the parts the fetch script wrote. The quarantine report, the ledger of files with their checksums
and the latest period of every source are written here and read by every document.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import polars as pl
from doorstep_contracts import acs, fhfa, geography, hmda, hud, permits, pmms, population
from doorstep_contracts.common import ContractError, write_parquet
from doorstep_core.config import POLICY
from doorstep_core.hashing import file_sha256
from doorstep_core.log import get_logger
from doorstep_core.manifest import Manifest, Scribe
from doorstep_core.paths import Paths

from doorstep_pipeline.common import connect, new_partial, save_partial

log = get_logger("doorstep.data")

LEDGER = Path("data/ingest_ledger.csv")


def _ledger(p: Paths, files: list[Path]) -> list[dict[str, str]]:
    rows = []
    for path in files:
        rows.append(
            {
                "file": path.relative_to(p.root).as_posix(),
                "bytes": str(path.stat().st_size),
                "sha256": file_sha256(path),
            }
        )
    out = p.root / LEDGER
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["file", "bytes", "sha256"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def _fetch_status(p: Paths) -> dict[str, object]:
    """The status files the fetch script wrote beside the data, when they were copied in."""
    out: dict[str, object] = {}
    for name in ("core", "acs", "hmda"):
        path = p.external / f"fetch-status-{name}.json"
        if path.exists():
            out[name] = json.loads(path.read_text(encoding="utf-8-sig"))
    return out


def run(p: Paths) -> Manifest:
    manifest = new_partial("data")
    derived = p.derived
    derived.mkdir(parents=True, exist_ok=True)
    reports: list[pl.DataFrame] = []
    read_files: list[Path] = []
    source_latest: dict[str, str] = {}

    # FHFA
    frame = fhfa.parse(p.external)
    flagged, report = fhfa.quarantine(frame)
    reports.append(report)
    write_parquet(flagged, derived / "fhfa_quarterly.parquet")
    read_files.append(p.external / "fhfa" / "hpi_master.csv")
    fhfa_latest = fhfa.latest_period(flagged)
    source_latest["fhfa"] = fhfa_latest
    s = Scribe(manifest, source="real:fhfa", population="every metropolitan area and division in the FHFA index", origin="data.fhfa")
    s.put("data.fhfa.rows", flagged.height, "int")
    s.put("data.fhfa.areas_all_transactions", flagged.filter(pl.col("flavor") == "all-transactions")["place_id"].n_unique(), "int")
    s.put("data.fhfa.areas_purchase_only", flagged.filter(pl.col("flavor") == "purchase-only")["place_id"].n_unique(), "int")
    s.put("data.fhfa.divisions", flagged.filter(pl.col("is_division"))["place_id"].n_unique(), "int")
    s.put("data.fhfa.latest_period", fhfa_latest, "quarter")
    s.put("data.fhfa.first_year", int(flagged["year"].min()), "int")  # type: ignore[arg-type]
    s.put("data.fhfa.contract_digest", fhfa.DIGEST, "text")
    log.info("fhfa", rows=flagged.height, latest=fhfa_latest)

    # PMMS
    frame = pmms.parse(p.external)
    flagged, report = pmms.quarantine(frame)
    reports.append(report)
    write_parquet(flagged, derived / "pmms_weekly.parquet")
    quarterly = pmms.quarterly(flagged)
    write_parquet(quarterly, derived / "pmms_quarterly.parquet")
    read_files.append(p.external / "pmms" / "historicalweeklydata.xlsx")
    latest_week, latest_rate = pmms.latest(flagged)
    source_latest["pmms"] = latest_week.isoformat()
    s = Scribe(manifest, source="real:pmms", population="every weekly survey since April 1971", origin="data.pmms")
    s.put("data.pmms.weeks", flagged.height, "int")
    s.put("data.pmms.latest_week", latest_week.isoformat(), "text")
    s.put("data.pmms.latest_rate", latest_rate, "rate2")
    s.put("data.pmms.contract_digest", pmms.DIGEST, "text")
    log.info("pmms", weeks=flagged.height, latest=latest_week.isoformat(), rate=latest_rate)

    # HUD
    fmr_latest, fmr_fy = hud.parse_fmr_latest(p.external)
    flagged, report = hud.quarantine_fmr(fmr_latest)
    reports.append(report)
    write_parquet(flagged, derived / "hud_fmr_latest.parquet")
    history = hud.parse_fmr_history(p.external)
    hist_years = 0
    if history is not None:
        write_parquet(history, derived / "hud_fmr_history.parquet")
        hist_years = history["fiscal_year"].n_unique()
    il, il_years = hud.parse_income_limits(p.external)
    flagged_il, report = hud.quarantine_il(il)
    reports.append(report)
    write_parquet(flagged_il, derived / "hud_income_limits.parquet")
    read_files.extend(sorted((p.external / "hud").glob("*.xls*")) + sorted((p.external / "hud").glob("*.csv")))
    source_latest["hud_fmr"] = f"FY{fmr_fy}"
    source_latest["hud_il"] = f"FY{max(il_years)}"
    s = Scribe(manifest, source="real:hud", population="every county HUD publishes a Fair Market Rent or an income limit for", origin="data.hud")
    s.put("data.hud.fmr_fiscal_year", fmr_fy, "int")
    s.put("data.hud.fmr_counties", flagged.height, "int")
    s.put("data.hud.fmr_metros", flagged.filter(pl.col("cbsa_code").is_not_null())["cbsa_code"].n_unique(), "int")
    s.put("data.hud.fmr_history_years", hist_years, "int")
    s.put("data.hud.income_limit_years", len(il_years), "int")
    s.put("data.hud.income_limit_first_year", min(il_years), "int")
    s.put("data.hud.income_limit_last_year", max(il_years), "int")
    s.put("data.hud.contract_digest", hud.DIGEST, "text")

    # Permits
    frame = permits.parse(p.external)
    flagged, report = permits.quarantine(frame)
    reports.append(report)
    write_parquet(flagged, derived / "bps_county.parquet")
    read_files.extend(sorted((p.external / "bps").glob("co*.txt")))
    full_years = flagged.filter(pl.col("partial_through_month").is_null())
    ytd = flagged.filter(pl.col("partial_through_month").is_not_null())
    source_latest["bps"] = (
        f"{int(ytd['year'].max())} through month {int(ytd['partial_through_month'].max())}" if ytd.height else str(int(full_years["year"].max()))  # type: ignore[arg-type]
    )
    s = Scribe(manifest, source="real:bps", population="every permit issuing county", origin="data.bps")
    s.put("data.bps.rows", flagged.height, "int")
    s.put("data.bps.first_year", int(full_years["year"].min()), "int")  # type: ignore[arg-type]
    s.put("data.bps.last_full_year", int(full_years["year"].max()), "int")  # type: ignore[arg-type]
    s.put("data.bps.ytd_year", int(ytd["year"].max()) if ytd.height else None, "int")  # type: ignore[arg-type]
    s.put("data.bps.ytd_month", int(ytd["partial_through_month"].max()) if ytd.height else None, "int")  # type: ignore[arg-type]
    s.put("data.bps.contract_digest", permits.DIGEST, "text")

    # Population
    frame = population.parse_counties(p.external)
    flagged, report = population.quarantine(frame)
    reports.append(report)
    write_parquet(flagged, derived / "popest_county_all_vintages.parquet")
    latest = population.latest_per_year(flagged)
    inter = population.parse_intercensal_totals(p.external)
    if inter is not None:
        latest = latest.join(inter, on=["county_fips", "year"], how="left")
    write_parquet(latest, derived / "popest_county.parquet")
    metros = population.parse_metros(p.external)
    write_parquet(metros, derived / "popest_metro_published.parquet")
    read_files.extend(sorted((p.external / "popest").glob("*.csv")))
    source_latest["popest"] = str(int(latest["year"].max()))  # type: ignore[arg-type]
    s = Scribe(manifest, source="real:popest", population="every county, 2000 to the latest vintage", origin="data.popest")
    s.put("data.popest.rows", latest.height, "int")
    s.put("data.popest.first_year", int(latest["year"].min()), "int")  # type: ignore[arg-type]
    s.put("data.popest.last_year", int(latest["year"].max()), "int")  # type: ignore[arg-type]
    s.put("data.popest.vintages", flagged["vintage"].n_unique(), "int")
    s.put("data.popest.contract_digest", population.DIGEST, "text")

    # Geography
    frame = geography.parse(p.external)
    flagged, report = geography.quarantine(frame)
    reports.append(report)
    write_parquet(flagged, derived / "delineations.parquet")
    gaz = geography.parse_gazetteer(p.external)
    write_parquet(gaz, derived / "gazetteer.parquet")
    read_files.extend(sorted((p.external / "delineations").glob("*.xls*")) + sorted((p.external / "gazetteer").glob("*.zip")))
    latest_v = geography.latest_vintage(flagged)
    s = Scribe(manifest, source="real:omb", population="every county in every delineation vintage the window crosses", origin="data.omb")
    s.put("data.omb.vintages", flagged["vintage"].n_unique(), "int")
    s.put("data.omb.latest_vintage", latest_v, "int")
    s.put("data.omb.metropolitan_areas", geography.areas(flagged, latest_v).filter(pl.col("kind") == "metropolitan").height, "int")
    s.put("data.omb.micropolitan_areas", geography.areas(flagged, latest_v).filter(pl.col("kind") == "micropolitan").height, "int")
    s.put("data.omb.contract_digest", geography.DIGEST, "text")

    # ACS (optional until the fetch lands; the warehouse refuses to build without it)
    acs_dir = p.external / "acs"
    if any(acs_dir.glob("*/*.json")):
        frame = acs.parse(p.external)
        flagged, report = acs.quarantine(frame)
        reports.append(report)
        write_parquet(flagged, derived / "acs_long.parquet")
        cov = acs.coverage(flagged)
        write_parquet(cov, derived / "acs_coverage.parquet")
        read_files.extend(sorted(acs_dir.glob("*/*.json")))
        years = acs.years_present(flagged)
        source_latest["acs"] = str(max(years))
        s = Scribe(manifest, source="real:acs", population="every metropolitan and micropolitan area the one year release covers", origin="data.acs")
        s.put("data.acs.rows", flagged.height, "int")
        s.put("data.acs.years", len(years), "int")
        s.put("data.acs.first_year", min(years), "int")
        s.put("data.acs.last_year", max(years), "int")
        s.put("data.acs.tables", flagged["table"].n_unique(), "int")
        s.put("data.acs.areas_latest", cov.filter(pl.col("year") == max(years))["areas"].max(), "int")
        s.put("data.acs.gap_2020", 1 if 2020 not in years else 0, "int")
        s.put("data.acs.contract_digest", acs.DIGEST, "text")
    else:
        log.info("acs", status="not fetched yet")

    # HMDA (optional until the fetch lands)
    hmda_years = hmda.years_available(p.external)
    if hmda_years:
        con = connect(p, memory_limit="3GB", threads=2)
        p.hmda.mkdir(parents=True, exist_ok=True)
        total_rows = 0
        kept_rows = 0
        fetch_total = 0
        for year in hmda_years:
            summary = hmda.fetch_summary(p.external, year)
            fetch_total += int(summary.get("rows_total", 0))  # type: ignore[arg-type]
            frame = hmda.read_year(con, p.external, year)
            flagged, report = hmda.quarantine(frame)
            reports.append(report)
            write_parquet(flagged, p.hmda / f"lar_{year}.parquet")
            total_rows += flagged.height
            kept_rows += flagged.filter(hmda.analysis_rows()).height
            log.info("hmda", year=year, rows=flagged.height)
        read_files.extend(sorted((p.external / "hmda").glob("*/lar_part*.csv.gz")))
        source_latest["hmda"] = str(max(hmda_years))
        s = Scribe(manifest, source="real:hmda", population="every originated purchase or refinance loan on a principal residence, every year fetched", origin="data.hmda")
        s.put("data.hmda.first_year", min(hmda_years), "int")
        s.put("data.hmda.last_year", max(hmda_years), "int")
        s.put("data.hmda.years", len(hmda_years), "int")
        s.put("data.hmda.rows_in_source_files", fetch_total, "int")
        s.put("data.hmda.rows_after_fetch_filter", total_rows, "int")
        s.put("data.hmda.rows_in_analysis", kept_rows, "int")
        s.put("data.hmda.contract_digest", hmda.DIGEST, "text")
        s.put("data.hmda.filter_fetch", hmda.FILTER["fetch"], "text")
        s.put("data.hmda.filter_ingest", hmda.FILTER["ingest"], "text")
    else:
        log.info("hmda", status="not fetched yet")

    # Quarantine report and the ledger
    quarantine = pl.concat(reports)
    (p.results / "data").mkdir(parents=True, exist_ok=True)
    write_parquet(quarantine, p.results / "data" / "quarantine.parquet")
    totals = quarantine.group_by(["source", "rule"]).agg(pl.col("flagged").sum(), pl.col("rows").sum()).sort(["source", "rule"])
    s = Scribe(manifest, source="mixed", population="every row of every source", origin="data.quarantine")
    s.table(
        "data.quarantine.by_rule",
        ["Source", "Rule", "Flagged", "Rows"],
        ["text", "text", "int", "int"],
        [[r["source"], r["rule"], int(r["flagged"]), int(r["rows"])] for r in totals.iter_rows(named=True)],
    )
    s.put("data.quarantine.rules", totals.height, "int")
    s.put("data.quarantine.flagged_total", int(totals["flagged"].sum()), "int")
    ledger = _ledger(p, read_files)
    s.put("data.ledger.files", len(ledger), "int")
    s.put("data.ledger.bytes", sum(int(r["bytes"]) for r in ledger), "int")
    for name, value in sorted(source_latest.items()):
        s.put(f"data.latest.{name}", value, "text")
    s.put("data.window.start_year", POLICY.window_start_year, "int")
    status = _fetch_status(p)
    s.put("data.fetch.status_files", len(status), "int")
    save_partial(p, "data", manifest)
    return manifest


def require_sources(p: Paths) -> None:
    missing = [name for name in ("fhfa_quarterly", "pmms_quarterly", "acs_long", "bps_county", "popest_county", "delineations") if not (p.derived / f"{name}.parquet").exists()]
    if missing:
        raise ContractError(f"derived sources missing: {missing}; run `doorstep data` after the fetch")
