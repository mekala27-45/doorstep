"""HUD: Fair Market Rents and income limits, at the county grain HUD publishes them.

Fair Market Rents come as one history file (every county, every fiscal year since 1983, all bedroom
sizes) when it is present, and as the current fiscal year's county file in every case; the current
file also carries the HUD area code, which embeds the CBSA code for metropolitan areas
(``METRO33860M33860``) and names the county for the rest. Income limits come one workbook per fiscal
year, with layouts that drift across two decades: the module finds the median family income column by
its ``median<year>`` name and the four person limits by theirs, and records the years whose file was
not published under a name the fetch script tried.
"""

from __future__ import annotations

import re
from pathlib import Path

import polars as pl
from doorstep_core.scalars import num

from doorstep_contracts.common import ContractError, Rule, apply_rules, contract_digest

FMR_FIELDS = (
    "county_fips",
    "fiscal_year",
    "hud_area_code",
    "hud_area_name",
    "cbsa_code",
    "fmr_0",
    "fmr_1",
    "fmr_2",
    "fmr_3",
    "fmr_4",
)
IL_FIELDS = (
    "county_fips",
    "fiscal_year",
    "hud_area_code",
    "hud_area_name",
    "cbsa_code",
    "median_family_income",
    "l30_4",
    "l50_4",
    "l80_4",
)

FMR_RULES = (
    Rule("non_positive_rent", "a two bedroom FMR at or below zero", lambda f: pl.col("fmr_2") <= 0),
    Rule(
        "bedroom_order",
        "a larger unit cheaper than a smaller one",
        lambda f: (pl.col("fmr_2") < pl.col("fmr_1")) | (pl.col("fmr_3") < pl.col("fmr_2")),
    ),
)
IL_RULES = (
    Rule(
        "non_positive_income",
        "a median family income at or below zero",
        lambda f: pl.col("median_family_income") <= 0,
    ),
    Rule(
        "limit_order",
        "the 50 percent limit above the 80 percent limit",
        lambda f: (pl.col("l80_4").is_not_null()) & (pl.col("l50_4") > pl.col("l80_4")),
    ),
)

DIGEST = contract_digest("hud", FMR_FIELDS + IL_FIELDS, FMR_RULES + IL_RULES)

_METRO_CODE = re.compile(r"^METRO(\d{5})")


def cbsa_from_hud_code(code: str | None) -> str | None:
    if not code:
        return None
    m = _METRO_CODE.match(code)
    return m.group(1) if m else None


def _load_xlsx(path: Path):  # type: ignore[no-untyped-def]
    """openpyxl, with the document properties stripped when they are malformed (one HUD workbook
    carries a modification date with a space in it, which the strict ISO parser refuses)."""
    import io
    import zipfile

    import openpyxl

    try:
        return openpyxl.load_workbook(path, read_only=True, data_only=True)
    except ValueError:
        buffer = io.BytesIO()
        with zipfile.ZipFile(path) as src, zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as dst:
            for item in src.infolist():
                if item.filename == "docProps/core.xml":
                    continue
                dst.writestr(item, src.read(item.filename))
        buffer.seek(0)
        return openpyxl.load_workbook(buffer, read_only=True, data_only=True)


def _sheet_rows(path: Path) -> tuple[list[str], list[list[object]]]:
    if path.suffix.lower() == ".xlsx":
        wb = _load_xlsx(path)
        ws = wb.worksheets[0]
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
    else:
        import xlrd

        with open("/dev/null", "w") as quiet:
            book = xlrd.open_workbook(path, logfile=quiet)
            sheet = book.sheet_by_index(0)
            rows = [sheet.row_values(r) for r in range(sheet.nrows)]
    header = [str(h).strip() if h is not None else "" for h in rows[0]]
    return header, rows[1:]


def _num(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return num(value)
    except (TypeError, ValueError):
        return None


def _fips(value: object) -> str:
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    digits = re.sub(r"\D", "", text)
    return digits[:5].zfill(5)


def parse_fmr_latest(external: Path) -> tuple[pl.DataFrame, int]:
    folder = external / "hud"
    files = sorted(folder.glob("FY*_FMRs*.xlsx"))
    if not files:
        raise ContractError(f"no fiscal year FMR file under {folder}")
    path = files[-1]
    fy = 2000 + int(re.search(r"FY(\d{2})", path.name).group(1))  # type: ignore[union-attr]
    header, rows = _sheet_rows(path)
    idx = {h.lower(): i for i, h in enumerate(header)}
    out: list[dict[str, object]] = []
    for r in rows:
        if not r or r[idx["fips"]] is None:
            continue
        code = str(r[idx["hud_area_code"]]).strip()
        out.append(
            {
                "county_fips": _fips(r[idx["fips"]]),
                "fiscal_year": fy,
                "hud_area_code": code,
                "hud_area_name": str(r[idx["hud_area_name"]]).strip(),
                "cbsa_code": cbsa_from_hud_code(code),
                "fmr_0": _num(r[idx["fmr_0"]]),
                "fmr_1": _num(r[idx["fmr_1"]]),
                "fmr_2": _num(r[idx["fmr_2"]]),
                "fmr_3": _num(r[idx["fmr_3"]]),
                "fmr_4": _num(r[idx["fmr_4"]]),
            }
        )
    return pl.DataFrame(out, schema_overrides={"cbsa_code": pl.Utf8}), fy


def parse_fmr_history(external: Path) -> pl.DataFrame | None:
    """The county level history, when the fetch found it; columns fmr<yy>_<bedrooms> by fiscal year."""
    folder = external / "hud"
    files = sorted(folder.glob("FMR_All_1983_*.csv")) + sorted(folder.glob("FMR_All_1983_*.xlsx"))
    if not files:
        return None
    path = files[-1]
    if path.suffix == ".csv":
        raw = pl.read_csv(path, infer_schema_length=0, encoding="latin-1")
    else:
        header, rows = _sheet_rows(path)
        raw = pl.DataFrame(
            [
                dict(zip(header, [str(c) if c is not None else None for c in r], strict=False))
                for r in rows
                if r
            ]
        )
    cols = {c.lower(): c for c in raw.columns}
    fips_col = next((cols[c] for c in cols if c.startswith("fips")), None)
    if fips_col is None:
        raise ContractError("the FMR history has no fips column")
    out: list[pl.DataFrame] = []
    years = sorted({int(m.group(1)) for c in cols for m in [re.match(r"fmr(\d{2,4})_?2$", c)] if m})
    for y in years:
        fy = y if y > 1900 else (1900 + y if y >= 83 else 2000 + y)

        def col(bed: int, y: int = y) -> str | None:
            for cand in (f"fmr{y}_{bed}", f"fmr{y:02d}_{bed}", f"fmr{y}{bed}"):
                if cand in cols:
                    return cols[cand]
            return None

        c2 = col(2)
        if c2 is None:
            continue
        sel = {
            "county_fips": pl.col(fips_col)
            .cast(pl.Utf8)
            .str.replace_all(r"\D", "")
            .str.slice(0, 5)
            .str.zfill(5),
            "fiscal_year": pl.lit(fy),
        }
        for bed in range(5):
            c = col(bed)
            sel[f"fmr_{bed}"] = (
                pl.col(c).cast(pl.Float64, strict=False) if c else pl.lit(None, dtype=pl.Float64)
            )
        out.append(raw.select(**sel))
    if not out:
        return None
    return pl.concat(out).sort(["county_fips", "fiscal_year"])


def parse_income_limits(external: Path) -> tuple[pl.DataFrame, list[int]]:
    """Every Section 8 income limits workbook present: median family income and the four person limits."""
    folder = external / "hud"
    files = sorted(folder.glob("Section8-FY*.xls*"))
    frames: list[pl.DataFrame] = []
    years: list[int] = []
    for path in files:
        yy = int(re.search(r"FY(\d{2})", path.name).group(1))  # type: ignore[union-attr]
        fy = 2000 + yy
        header, rows = _sheet_rows(path)
        idx = {h.lower(): i for i, h in enumerate(header)}
        median_col = next(
            (idx[c] for c in idx if re.fullmatch(r"median\d{4}", c) and c.endswith(str(fy))), None
        )
        if median_col is None:
            median_col = next((idx[c] for c in idx if re.fullmatch(r"median\d{4}", c)), None)
        if median_col is None:
            continue
        fips_col = next((idx[c] for c in ("fips", "fips2010", "fips2000") if c in idx), None)
        state_col = idx.get("state")
        county_col = idx.get("county")
        area_col = next((idx[c] for c in ("hud_area_code", "cbsasub", "msa") if c in idx), None)
        name_col = next((idx[c] for c in ("hud_area_name", "metro_area_name", "msaname") if c in idx), None)
        out: list[dict[str, object]] = []
        for r in rows:
            if not r:
                continue
            if fips_col is not None and r[fips_col] not in (None, ""):
                fips = _fips(r[fips_col])
            elif state_col is not None and county_col is not None and r[state_col] not in (None, ""):
                fips = _fips(r[state_col]).lstrip("0").zfill(2)[-2:] + str(int(num(r[county_col]))).zfill(3)
            else:
                continue
            code = str(r[area_col]).strip() if area_col is not None and r[area_col] is not None else ""
            out.append(
                {
                    "county_fips": fips,
                    "fiscal_year": fy,
                    "hud_area_code": code,
                    "hud_area_name": str(r[name_col]).strip()
                    if name_col is not None and r[name_col] is not None
                    else "",
                    "cbsa_code": cbsa_from_hud_code(code),
                    "median_family_income": _num(r[median_col]),
                    "l30_4": _num(r[idx["l30_4"]]) if "l30_4" in idx else None,
                    "l50_4": _num(r[idx["l50_4"]]) if "l50_4" in idx else None,
                    "l80_4": _num(r[idx["l80_4"]]) if "l80_4" in idx else None,
                }
            )
        if out:
            frames.append(
                pl.DataFrame(
                    out,
                    schema_overrides={
                        "cbsa_code": pl.Utf8,
                        "l30_4": pl.Float64,
                        "l50_4": pl.Float64,
                        "l80_4": pl.Float64,
                    },
                )
            )
            years.append(fy)
    if not frames:
        raise ContractError(f"no income limits workbooks under {folder}")
    return pl.concat(frames).sort(["county_fips", "fiscal_year"]), years


def quarantine_fmr(frame: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    flagged, report = apply_rules(frame, FMR_RULES, "hud_fmr", "fiscal_year")
    return flagged, report.frame()


def quarantine_il(frame: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    flagged, report = apply_rules(frame, IL_RULES, "hud_il", "fiscal_year")
    return flagged, report.frame()
