"""The OMB metropolitan delineation files, one per vintage, and the CBSA gazetteer.

Every source in this build is published against the delineation in force when it came out: the
census tables carry the vintage of their year, the permits and population files their release's, the
loans the vintage HMDA used for that year, and the price index the current one. The crosswalk here
maps every county to exactly one area per vintage, and the warehouse carries each metro under its
latest code with the earlier codes as aliases. The 2023 delineation renamed and recomposed areas
(Connecticut's planning regions among them), which is why the crosswalk is tested rather than assumed.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from doorstep_contracts.common import ContractError, Rule, apply_rules, contract_digest

VINTAGES = (2009, 2013, 2015, 2017, 2018, 2020, 2023)

FIELDS = (
    "vintage",
    "cbsa_code",
    "cbsa_title",
    "kind",
    "division_code",
    "division_title",
    "county_fips",
    "county_name",
    "state_name",
    "central",
)

RULES = (
    Rule(
        "county_in_two_areas",
        "a county mapped to more than one area in one vintage",
        lambda f: pl.col("areas_for_county") > 1,
    ),
    Rule(
        "malformed_fips",
        "a county code that is not five digits",
        lambda f: pl.col("county_fips").str.len_chars() != 5,
    ),
)

DIGEST = contract_digest("geography", FIELDS, RULES, {"vintages": list(VINTAGES)})


def _rows_xlsx(path: Path) -> list[list[object]]:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    return [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]


def _rows_xls(path: Path) -> list[list[object]]:
    import xlrd

    book = xlrd.open_workbook(path)
    sheet = book.sheet_by_index(0)
    return [sheet.row_values(r) for r in range(sheet.nrows)]


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def parse_vintage(external: Path, vintage: int) -> pl.DataFrame:
    folder = external / "delineations"
    candidates = [folder / f"list1_{vintage}.xlsx", folder / f"list1_{vintage}.xls"]
    path = next((c for c in candidates if c.exists()), None)
    if path is None:
        raise ContractError(f"the {vintage} delineation file is missing under {folder}")
    rows = _rows_xlsx(path) if path.suffix == ".xlsx" else _rows_xls(path)
    header_index = next(i for i, r in enumerate(rows) if _text(r[0]) == "CBSA Code")
    header = [_text(h) for h in rows[header_index]]
    out: list[dict[str, object]] = []
    for r in rows[header_index + 1 :]:
        cells = [_text(c) for c in r] + [""] * (len(header) - len(r))
        code = cells[0]
        if not code.isdigit():
            continue
        if vintage == 2009:
            # The 2009 layout: Level of CBSA, Status, Division Title, CSA Title, Component Name, State, FIPS (5), County Status
            kind = "metropolitan" if cells[5].strip() == "1" else "micropolitan"
            fips = cells[10].zfill(5)
            out.append(
                {
                    "vintage": vintage,
                    "cbsa_code": code,
                    "cbsa_title": cells[3],
                    "kind": kind,
                    "division_code": cells[1] or None,
                    "division_title": cells[6] or None,
                    "county_fips": fips,
                    "county_name": cells[8],
                    "state_name": cells[9],
                    "central": cells[11].lower().startswith("central"),
                }
            )
        else:
            kind = "metropolitan" if cells[4].lower().startswith("metropolitan") else "micropolitan"
            fips = cells[9].zfill(2) + cells[10].zfill(3)
            out.append(
                {
                    "vintage": vintage,
                    "cbsa_code": code,
                    "cbsa_title": cells[3],
                    "kind": kind,
                    "division_code": cells[1] or None,
                    "division_title": cells[5] or None,
                    "county_fips": fips,
                    "county_name": cells[7],
                    "state_name": cells[8],
                    "central": cells[11].lower().startswith("central"),
                }
            )
    if not out:
        raise ContractError(f"no county rows read from {path.name}")
    return pl.DataFrame(out, schema_overrides={"division_code": pl.Utf8, "division_title": pl.Utf8})


def parse(external: Path) -> pl.DataFrame:
    frames = [
        parse_vintage(external, v)
        for v in VINTAGES
        if (external / "delineations" / f"list1_{v}.xlsx").exists()
        or (external / "delineations" / f"list1_{v}.xls").exists()
    ]
    if not frames:
        raise ContractError("no delineation files were found")
    frame = pl.concat(frames).sort(["vintage", "cbsa_code", "county_fips"])
    frame = frame.with_columns(pl.len().over(["vintage", "county_fips"]).alias("areas_for_county"))
    return frame


def quarantine(frame: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    flagged, report = apply_rules(frame, RULES, "omb", "vintage")
    return flagged.select(
        [*FIELDS, *[c for c in flagged.columns if c.startswith("q_")], "quarantined"]
    ), report.frame()


def latest_vintage(frame: pl.DataFrame) -> int:
    return int(frame["vintage"].max())  # type: ignore[arg-type]


def areas(frame: pl.DataFrame, vintage: int) -> pl.DataFrame:
    """One row per area in a vintage: code, title, kind, county count."""
    return (
        frame.filter(pl.col("vintage") == vintage)
        .group_by(["cbsa_code", "cbsa_title", "kind"])
        .agg(pl.len().alias("counties"))
        .sort("cbsa_code")
    )


def divisions(frame: pl.DataFrame, vintage: int) -> pl.DataFrame:
    """Division code to parent area, with the division's counties, for the FHFA roll up."""
    return (
        frame.filter((pl.col("vintage") == vintage) & pl.col("division_code").is_not_null())
        .select(["division_code", "division_title", "cbsa_code", "cbsa_title", "county_fips"])
        .sort(["division_code", "county_fips"])
    )


def parse_gazetteer(external: Path) -> pl.DataFrame:
    """Area centroids and land area from the Census gazetteer, for the map."""
    import io
    import zipfile

    folder = external / "gazetteer"
    zips = sorted(folder.glob("*_Gaz_cbsa_national.zip"))
    if not zips:
        raise ContractError(f"no gazetteer zip under {folder}")
    with zipfile.ZipFile(zips[-1]) as z:
        name = next(n for n in z.namelist() if n.endswith(".txt"))
        text = z.read(name).decode("latin-1")
    frame = pl.read_csv(
        io.StringIO(text),
        separator="|",
        infer_schema_length=10_000,
        schema_overrides={"GEOID": pl.Utf8, "CSAFP": pl.Utf8},
    )
    frame = frame.rename({c: c.strip() for c in frame.columns})
    return frame.select(
        pl.col("GEOID").alias("cbsa_code"),
        pl.col("NAME").alias("name"),
        pl.when(pl.col("CBSA_TYPE") == 1)
        .then(pl.lit("metropolitan"))
        .otherwise(pl.lit("micropolitan"))
        .alias("kind"),
        pl.col("ALAND_SQMI").cast(pl.Float64).alias("land_sqmi"),
        pl.col("INTPTLAT").cast(pl.Float64).alias("latitude"),
        pl.col("INTPTLONG").cast(pl.Float64).alias("longitude"),
    ).with_columns(pl.lit(int(zips[-1].name[:4])).alias("gazetteer_year"))
