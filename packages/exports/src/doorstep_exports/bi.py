"""The BI extracts and specifications, and the CSV bundle with its data dictionary.

Tableau: CSV extracts of the metro by quarter and metro by year marts with a committed workbook
specification listing the views the companion workbook shows. Power BI: a model specification with the
tables, relationships and DAX measures, committed as text, to be opened on Windows. The CSV bundle holds
every chapter table with a dictionary that lists every column.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import polars as pl
from doorstep_core.manifest import Manifest
from doorstep_core.statements import RATE_ATTRIBUTION, STATEMENT

TABLEAU_VIEWS: tuple[dict[str, str], ...] = (
    {
        "name": "Payment share over time",
        "extract": "metro_year",
        "marks": "line by cbsa_title, year on columns, payment_share on rows",
        "reference": "constant line at 0.30, the HUD standard",
    },
    {
        "name": "Price against income",
        "extract": "metro_year",
        "marks": "scatter of median_income (columns) against value_anchored (rows) for the latest year, size by households, color by payment_share",
        "reference": "diagonal at price to income 4",
    },
    {
        "name": "Rank slope",
        "extract": "ranking",
        "marks": "slope chart from raw_rank to adjusted_rank for the twenty largest metros, color by moves",
        "reference": "rank 1 at the top",
    },
    {
        "name": "Rent burden bars",
        "extract": "burden_bands",
        "marks": "stacked bars by year of under_30, from_30_to_50 and over_50",
        "reference": "lines at 30 and 50 percent",
    },
    {
        "name": "Permits against price growth",
        "extract": "supply_cells",
        "marks": "scatter of permits_rate (columns) against annual_growth (rows), trend line with confidence band",
        "reference": "the controlled slope from the manifest",
    },
)

MART_EXTRACTS: dict[str, str] = {
    "metro_year": "mart_metro_year",
    "metro_quarter": "mart_metro_quarter",
    "national_year": "mart_national_year",
    "ranking": "ch5_ranking",
    "burden_bands": "ch3_national_bands",
    "supply_cells": "ch4_cells",
}

POWERBI_MEASURES: tuple[tuple[str, str, str], ...] = (
    ("Payment share", "DIVIDE(12 * SUM(metro_year[payment]), SUM(metro_year[median_income]))", "pct"),
    ("Price to income", "DIVIDE(SUM(metro_year[value_anchored]), SUM(metro_year[median_income]))", "ratio"),
    ("Affordable share", "AVERAGE(ranking[affordable_share])", "pct"),
    (
        "Cost burdened share",
        "DIVIDE(SUM(metro_year[renters_burdened]), SUM(metro_year[renters_with_share]))",
        "pct",
    ),
    (
        "Severely burdened share",
        "DIVIDE(SUM(metro_year[renters_severe]), SUM(metro_year[renters_with_share]))",
        "pct",
    ),
    (
        "Permits per 100 households",
        "DIVIDE(100 * SUM(metro_year[permits]), SUM(metro_year[households]))",
        "ratio",
    ),
    (
        "Lock in share",
        "DIVIDE(100 * CALCULATE(SUM(metro_year[low_rate_originations]), metro_year[year] IN {2019, 2020, 2021}), CALCULATE(SUM(metro_year[owner_households]), metro_year[year] = 2021))",
        "ratio",
    ),
    (
        "Turnover per 100 owners",
        "DIVIDE(100 * SUM(metro_year[purchase_loans]), SUM(metro_year[owner_households]))",
        "ratio",
    ),
    (
        "Borrower income ratio",
        "DIVIDE(SUM(metro_year[purchase_median_income]), SUM(metro_year[median_income]))",
        "ratio",
    ),
    (
        "Domestic migration per 100",
        "DIVIDE(100 * SUM(metro_year[domestic_migration]), SUM(metro_year[population]))",
        "ratio",
    ),
)


def _write_csv(frame: pl.DataFrame, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_csv(path)
    return frame.height


def tableau(marts: Path, out: Path) -> dict[str, int]:
    out.mkdir(parents=True, exist_ok=True)
    rows: dict[str, int] = {}
    for name, mart in MART_EXTRACTS.items():
        source = marts / f"{mart}.parquet"
        if not source.exists():
            continue
        rows[name] = _write_csv(pl.read_parquet(source), out / f"{name}.csv")
    spec = {
        "statement": STATEMENT,
        "rate_attribution": RATE_ATTRIBUTION,
        "extracts": {name: f"{name}.csv" for name in rows},
        "views": list(TABLEAU_VIEWS),
        "companion": "Open the extracts in Tableau Public, build the five views as listed, publish, and put the link on the data page. The companion reads the same marts the site reads; the manifest holds every headline.",
    }
    (out / "workbook_spec.json").write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")
    lines = [
        "# Tableau companion specification",
        "",
        "Extracts: " + ", ".join(f"`{n}.csv`" for n in rows),
        "",
    ]
    for v in TABLEAU_VIEWS:
        lines.append(f"- **{v['name']}** ({v['extract']}): {v['marks']}; reference: {v['reference']}.")
    lines += ["", STATEMENT, "", RATE_ATTRIBUTION, ""]
    (out / "workbook_spec.md").write_text("\n".join(lines), encoding="utf-8")
    return rows


def powerbi(metrics: list[Any], out: Path, metros_ranked: int) -> int:
    out.mkdir(parents=True, exist_ok=True)
    tables = {
        "metro_year": {
            "source": "tableau/metro_year.csv",
            "key": ["cbsa_code", "year"],
            "columns": "every column of mart_metro_year",
        },
        "metro_quarter": {
            "source": "tableau/metro_quarter.csv",
            "key": ["cbsa_code", "period"],
            "columns": "index, anchored value, rate, payment, payment share",
        },
        "ranking": {
            "source": "tableau/ranking.csv",
            "key": ["cbsa_code"],
            "columns": f"the raw and adjusted ranks of {metros_ranked} metros with intervals",
        },
        "metros": {
            "source": "tableau/metro_year.csv (distinct cbsa_code, cbsa_title, kind, states)",
            "key": ["cbsa_code"],
            "columns": "the dimension",
        },
        "years": {"source": "generated", "key": ["year"], "columns": "a date table from 2000"},
    }
    relationships = [
        {"from": "metro_year[cbsa_code]", "to": "metros[cbsa_code]", "cardinality": "many to one"},
        {"from": "metro_quarter[cbsa_code]", "to": "metros[cbsa_code]", "cardinality": "many to one"},
        {"from": "ranking[cbsa_code]", "to": "metros[cbsa_code]", "cardinality": "one to one"},
        {"from": "metro_year[year]", "to": "years[year]", "cardinality": "many to one"},
    ]
    measures = [{"name": n, "dax": d, "format": f} for n, d, f in POWERBI_MEASURES]
    spec = {
        "statement": STATEMENT,
        "rate_attribution": RATE_ATTRIBUTION,
        "tables": tables,
        "relationships": relationships,
        "measures": measures,
        "metric_layer": [getattr(m, "name", str(m)) for m in metrics],
    }
    (out / "model_spec.json").write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")
    lines = ["# Power BI model specification", "", "## Tables", ""]
    for name, t in tables.items():
        lines.append(f"- `{name}` from {t['source']}; key {', '.join(t['key'])}; {t['columns']}.")
    lines += ["", "## Relationships", ""]
    for r in relationships:
        lines.append(f"- {r['from']} to {r['to']} ({r['cardinality']}).")
    lines += ["", "## Measures (DAX)", ""]
    for n, d, f in POWERBI_MEASURES:
        lines.append(f"- **{n}** ({f}): `{d}`")
    lines += [
        "",
        "Build the model on Windows from these tables and measures and commit the .pbip; the companion reads the same marts the site reads.",
        "",
        STATEMENT,
        "",
        RATE_ATTRIBUTION,
        "",
    ]
    (out / "model_spec.md").write_text("\n".join(lines), encoding="utf-8")
    return len(measures)


def csv_bundle(
    manifest: Manifest, tables: list[str], out: Path, extra: dict[str, pl.DataFrame] | None = None
) -> dict[str, int]:
    out.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    dictionary: list[dict[str, str]] = []
    for key in tables:
        if key not in manifest.tables:
            continue
        entry = manifest.tables[key]
        name = key.replace(".", "_")
        with (out / f"{name}.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(entry.columns)
            writer.writerows(entry.rows)
        counts[name] = len(entry.rows)
        for column, fmt in zip(entry.columns, entry.formats, strict=True):
            dictionary.append(
                {
                    "file": f"{name}.csv",
                    "column": column,
                    "format": fmt,
                    "source": entry.provenance.source,
                    "population": entry.provenance.population,
                }
            )
    for name, frame in (extra or {}).items():
        counts[name] = _write_csv(frame, out / f"{name}.csv")
        for column, dtype in zip(frame.columns, frame.dtypes, strict=True):
            dictionary.append(
                {
                    "file": f"{name}.csv",
                    "column": column,
                    "format": str(dtype),
                    "source": "mart",
                    "population": "the shipped mart",
                }
            )
    with (out / "data_dictionary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["file", "column", "format", "source", "population"])
        writer.writeheader()
        writer.writerows(dictionary)
    (out / "README.md").write_text(
        "# CSV bundle\n\nEvery chapter table rendered from results/manifest.json, with data_dictionary.csv listing every column.\n\n"
        + STATEMENT
        + "\n\n"
        + RATE_ATTRIBUTION
        + "\n",
        encoding="utf-8",
    )
    return counts
