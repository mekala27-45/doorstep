"""The Excel workbook with live formulas.

One sheet per chapter table, a Metros sheet with every metro's latest median home, income, rent and
rate, and a Model sheet where a manager picks a metro from a validated list and types an income, a
rate, a down payment share, a tax rate and an insurance rate: PMT and INDEX/MATCH formulas produce the
payment, the payment share, the affordable price, the monthly cost with taxes and insurance, and a
360 row amortisation table, all as formulas that recalculate in Excel or LibreOffice. Named ranges
carry the inputs. A test recalculates the file with LibreOffice when it is present and checks the
model sheet against the calculator for three metros.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl
from doorstep_core.config import POLICY
from doorstep_core.manifest import Manifest
from doorstep_core.statements import RATE_ATTRIBUTION, STATEMENT
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

NUMBER_FORMATS = {
    "int": "#,##0",
    "float1": "0.0",
    "float2": "0.00",
    "float3": "0.000",
    "float4": "0.0000",
    "sfloat1": "+0.0;-0.0;0.0",
    "sfloat2": "+0.00;-0.00;0.00",
    "sfloat3": "+0.000;-0.000;0.000",
    "sfloat4": "+0.0000;-0.0000;0.0000",
    "pct0": "0%",
    "pct1": "0.0%",
    "pct2": "0.00%",
    "spct1": "+0.0%;-0.0%;0.0%",
    "spct2": "+0.00%;-0.00%;0.00%",
    "pts1": "+0.0%;-0.0%;0.0%",
    "pts2": "+0.00%;-0.00%;0.00%",
    "apts1": "0.0%",
    "usd0": "$#,##0",
    "susd0": "+$#,##0;-$#,##0;$0",
    "usdk": "$#,##0",
    "years1": "0.0",
    "years0": "0",
    "ratio1": "0.0",
    "ratio2": "0.00",
    "rate2": "0.00",
    "quarter": "@",
    "text": "@",
}

HEADER_FILL = PatternFill("solid", fgColor="E8ECE9")
INPUT_FILL = PatternFill("solid", fgColor="FFF4DE")
BOLD = Font(bold=True)


def _title(ws: Any, text: str) -> None:
    ws["A1"] = text
    ws["A1"].font = Font(bold=True, size=13)


def _header(ws: Any, row: int, columns: list[str]) -> None:
    for j, name in enumerate(columns, start=1):
        cell = ws.cell(row=row, column=j, value=name)
        cell.font = BOLD
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="top")


def _autosize(ws: Any, widths: dict[int, float] | None = None) -> None:
    for j in range(1, ws.max_column + 1):
        letter = get_column_letter(j)
        ws.column_dimensions[letter].width = (widths or {}).get(j, 16)


def chapter_sheet(wb: Workbook, title: str, key: str, manifest: Manifest) -> int:
    entry = manifest.tables[key]
    ws = wb.create_sheet(title[:31])
    _title(ws, f"{key}: {manifest.label(key)}")
    _header(ws, 3, entry.columns)
    for i, row in enumerate(entry.rows, start=4):
        for j, (value, fmt) in enumerate(zip(row, entry.formats, strict=True), start=1):
            cell = ws.cell(row=i, column=j, value=value)
            cell.number_format = NUMBER_FORMATS.get(fmt, "General")
    ws.freeze_panes = "A4"
    _autosize(ws)
    return len(entry.rows)


def metros_sheet(wb: Workbook, metros: pl.DataFrame) -> int:
    ws = wb.create_sheet("Metros")
    _title(
        ws,
        "Every metropolitan area the calculator covers: the latest anchored median home, the census median income and rent, and the latest quarterly rate",
    )
    columns = [
        "Code",
        "Metro",
        "Households",
        "Median home",
        "Median income",
        "Median rent (monthly)",
        "Latest quarter",
        "Latest rate",
        "Income year",
    ]
    _header(ws, 3, columns)
    rows = metros.sort("cbsa_title").select(
        "cbsa_code",
        "cbsa_title",
        "households",
        "value_latest",
        "median_income",
        "median_rent",
        "latest_period",
        "rate_latest",
        "income_year",
    )
    for i, r in enumerate(rows.iter_rows(), start=4):
        for j, value in enumerate(r, start=1):
            cell = ws.cell(row=i, column=j, value=value)
            if j in (3,):
                cell.number_format = "#,##0"
            elif j in (4, 5, 6):
                cell.number_format = "$#,##0"
            elif j == 8:
                cell.number_format = "0.00"
    ws.freeze_panes = "A4"
    _autosize(ws, {2: 44})
    n = rows.height
    wb.defined_names["MetroNames"] = DefinedName("MetroNames", attr_text=f"Metros!$B$4:$B${3 + n}")
    wb.defined_names["MetroTable"] = DefinedName("MetroTable", attr_text=f"Metros!$A$4:$I${3 + n}")
    return n


def model_sheet(
    wb: Workbook, metros: pl.DataFrame, *, default_metro: str, rate_default: float
) -> dict[str, int]:
    ws = wb.create_sheet("Model", 0)
    _title(
        ws,
        "The affordability model: pick a metro, type an income, a rate, a down payment share, a tax rate and an insurance rate. Yellow cells are inputs; everything else is a formula.",
    )
    ws["A3"], ws["B3"] = "Metro", default_metro
    ws["A4"], ws["B4"] = "Annual household income", 85000
    ws["A5"], ws["B5"] = "Mortgage rate (percent)", rate_default
    ws["A6"], ws["B6"] = "Down payment share", POLICY.down_payment_share
    ws["A7"], ws["B7"] = "Property tax rate (share of value per year)", 0.011
    ws["A8"], ws["B8"] = "Insurance rate (share of value per year)", 0.004
    ws["A9"], ws["B9"] = "Loan term (years)", POLICY.loan_term_years
    ws["A10"], ws["B10"] = "Affordable line (share of income)", POLICY.affordable_line
    for row in range(3, 11):
        ws[f"B{row}"].fill = INPUT_FILL
        ws[f"A{row}"].font = BOLD
    ws["B4"].number_format = "$#,##0"
    ws["B5"].number_format = "0.00"
    for row in (6, 7, 8, 10):
        ws[f"B{row}"].number_format = "0.0%"
    dv = DataValidation(type="list", formula1="=MetroNames", allow_blank=False)
    ws.add_data_validation(dv)
    dv.add("B3")
    names = {
        "Income": "Model!$B$4",
        "Rate": "Model!$B$5",
        "DownShare": "Model!$B$6",
        "TaxRate": "Model!$B$7",
        "InsuranceRate": "Model!$B$8",
        "TermYears": "Model!$B$9",
        "AffordableLine": "Model!$B$10",
        "MetroPick": "Model!$B$3",
    }
    for name, ref in names.items():
        wb.defined_names[name] = DefinedName(name, attr_text=ref)

    ws["D3"], ws["E3"] = (
        "Median home (latest quarter)",
        "=INDEX(Metros!$D$4:$D$5000,MATCH(MetroPick,MetroNames,0))",
    )
    ws["D4"], ws["E4"] = "Metro median income", "=INDEX(Metros!$E$4:$E$5000,MATCH(MetroPick,MetroNames,0))"
    ws["D5"], ws["E5"] = (
        "Metro median rent (monthly)",
        "=INDEX(Metros!$F$4:$F$5000,MATCH(MetroPick,MetroNames,0))",
    )
    ws["D6"], ws["E6"] = "Latest quarter", "=INDEX(Metros!$G$4:$G$5000,MATCH(MetroPick,MetroNames,0))"
    ws["D8"], ws["E8"] = "Loan amount", "=E3*(1-DownShare)"
    ws["D9"], ws["E9"] = "Monthly payment (principal and interest)", "=-PMT(Rate/100/12,TermYears*12,E8)"
    ws["D10"], ws["E10"] = "Payment share of income", "=12*E9/Income"
    ws["D11"], ws["E11"] = (
        "Affordable price at the line",
        "=-PV(Rate/100/12,TermYears*12,AffordableLine*Income/12)/(1-DownShare)",
    )
    ws["D12"], ws["E12"] = "Monthly cost with taxes and insurance", "=E9+E3*(TaxRate+InsuranceRate)/12"
    ws["D13"], ws["E13"] = "Full cost share of income", "=12*E12/Income"
    ws["D14"], ws["E14"] = "Income needed for the median home at the line", "=12*E9/AffordableLine"
    ws["D15"], ws["E15"] = "Rent share of income at the metro median rent", "=12*E5/Income"
    ws["D16"], ws["E16"] = "Can the income carry the median home at the line", '=IF(E11>=E3,"yes","no")'
    for row in (3, 4, 5, 8, 9, 11, 12, 14):
        ws[f"E{row}"].number_format = "$#,##0"
    for row in (10, 13, 15):
        ws[f"E{row}"].number_format = "0.0%"
    for row in range(3, 17):
        ws[f"D{row}"].font = BOLD
    wb.defined_names["MedianHome"] = DefinedName("MedianHome", attr_text="Model!$E$3")
    wb.defined_names["Payment"] = DefinedName("Payment", attr_text="Model!$E$9")
    wb.defined_names["PaymentShare"] = DefinedName("PaymentShare", attr_text="Model!$E$10")
    wb.defined_names["AffordablePrice"] = DefinedName("AffordablePrice", attr_text="Model!$E$11")

    # The amortisation table: 360 rows of formulas
    ws["A19"] = "Amortisation"
    ws["A19"].font = BOLD
    _header(ws, 20, ["Month", "Payment", "Interest", "Principal", "Balance"])
    ws["A21"], ws["B21"], ws["C21"], ws["D21"], ws["E21"] = (
        1,
        "=Payment",
        "=E8*Rate/100/12",
        "=B21-C21",
        "=E8-D21",
    )
    for row in range(22, 21 + POLICY.loan_term_years * 12):
        ws[f"A{row}"] = f"=A{row - 1}+1"
        ws[f"B{row}"] = f"=IF(A{row}<=TermYears*12,Payment,0)"
        ws[f"C{row}"] = f"=E{row - 1}*Rate/100/12"
        ws[f"D{row}"] = f"=B{row}-C{row}"
        ws[f"E{row}"] = f"=MAX(E{row - 1}-D{row},0)"
    for row in range(21, 21 + POLICY.loan_term_years * 12):
        for col in "BCDE":
            ws[f"{col}{row}"].number_format = "$#,##0.00"
    ws["G20"], ws["H20"] = "Total interest over the term", f"=SUM(C21:C{20 + POLICY.loan_term_years * 12})"
    ws["H20"].number_format = "$#,##0"
    ws["G21"], ws["H21"] = "Total paid", f"=SUM(B21:B{20 + POLICY.loan_term_years * 12})"
    ws["H21"].number_format = "$#,##0"
    ws["G23"] = STATEMENT
    ws["G24"] = RATE_ATTRIBUTION
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["D"].width = 44
    ws.column_dimensions["E"].width = 18
    ws.column_dimensions["G"].width = 30
    ws.freeze_panes = "A3"
    formulas = 14 + 5 * POLICY.loan_term_years * 12 + 2
    return {"formulas": formulas, "named_ranges": len(wb.defined_names)}


def checks_sheet(
    wb: Workbook, metros: pl.DataFrame, *, rate_default: float, count: int = 3
) -> list[dict[str, Any]]:
    """Three metros with the model's formulas side by side, so one recalculation checks three answers against
    the calculator; the test reads this sheet back after LibreOffice has recalculated the file."""
    ws = wb.create_sheet("Checks")
    _title(ws, "Three metros through the same formulas as the Model sheet, for the recalculation test")
    _header(
        ws,
        3,
        [
            "Metro",
            "Income",
            "Rate",
            "Down share",
            "Median home",
            "Payment",
            "Payment share",
            "Affordable price",
        ],
    )
    chosen = metros.sort("households", descending=True).head(count)
    rows: list[dict[str, Any]] = []
    for i, r in enumerate(chosen.iter_rows(named=True), start=4):
        income = round(float(r["median_income"]) / 1000.0) * 1000
        ws[f"A{i}"] = str(r["cbsa_title"])
        ws[f"B{i}"] = income
        ws[f"C{i}"] = rate_default
        ws[f"D{i}"] = POLICY.down_payment_share
        ws[f"E{i}"] = f"=INDEX(Metros!$D$4:$D$5000,MATCH(A{i},MetroNames,0))"
        ws[f"F{i}"] = f"=-PMT(C{i}/100/12,TermYears*12,E{i}*(1-D{i}))"
        ws[f"G{i}"] = f"=12*F{i}/B{i}"
        ws[f"H{i}"] = f"=-PV(C{i}/100/12,TermYears*12,AffordableLine*B{i}/12)/(1-D{i})"
        rows.append(
            {
                "row": i,
                "cbsa_code": str(r["cbsa_code"]),
                "cbsa_title": str(r["cbsa_title"]),
                "income": income,
                "rate": rate_default,
                "median_home": float(r["value_latest"]),
            }
        )
    _autosize(ws, {1: 44})
    return rows


def readme_sheet(wb: Workbook, manifest: Manifest) -> None:
    ws = wb.create_sheet("Read me", 1)
    lines = [
        "doorstep: can anyone still afford a home. Every number on the chapter sheets is rendered from results/manifest.json, the same file the site and the memo read.",
        "",
        "Model sheet: pick a metro in B3 (a validated list from the Metros sheet), type an income in B4, a rate in B5 (percent), a down payment share in B6, and tax and insurance rates in B7 and B8.",
        "The payment is PMT on the loan at the monthly rate over the term; the payment share is twelve payments over the income; the affordable price is PV of the line share of income over the term, grossed up for the down payment.",
        "The amortisation table recalculates for every input. The headline figures of the story use principal and interest only, with taxes and insurance as workbook inputs, as the definitions document says.",
        "",
        "Metros sheet: the latest anchored median home (FHFA all transactions index anchored to the census median value in the anchor year), the census median household income and median gross rent of the latest one year release, and the latest quarterly PMMS rate.",
        "",
        STATEMENT,
        RATE_ATTRIBUTION,
        f"Manifest as of {manifest.as_of}.",
    ]
    for i, line in enumerate(lines, start=1):
        ws.cell(row=i, column=1, value=line).alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 120


def build(
    path: Path,
    manifest: Manifest,
    metros: pl.DataFrame,
    *,
    chapter_tables: tuple[tuple[str, str], ...],
    rate_default: float,
) -> dict[str, Any]:
    wb = Workbook()
    wb.remove(wb.active)
    n_metros = metros_sheet(wb, metros)
    largest = metros.sort("households", descending=True).row(0, named=True)
    model = model_sheet(wb, metros, default_metro=str(largest["cbsa_title"]), rate_default=rate_default)
    checks = checks_sheet(wb, metros, rate_default=rate_default)
    readme_sheet(wb, manifest)
    chapter_sheets = 0
    for key, title in chapter_tables:
        if key in manifest.tables:
            chapter_sheet(wb, title, key, manifest)
            chapter_sheets += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return {
        "sheets": len(wb.sheetnames),
        "chapter_sheets": chapter_sheets,
        "metros": n_metros,
        "formulas": model["formulas"],
        "named_ranges": model["named_ranges"],
        "default_metro": str(largest["cbsa_title"]),
        "checks": checks,
    }
