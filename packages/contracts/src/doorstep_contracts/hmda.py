"""The HMDA loan level extract: the public snapshot LAR files, filtered on the PC that fetched them.

The fetch script keeps originated loans (action taken 1) for home purchase, refinance and cash out
refinance (purposes 1, 31, 32) and the columns this build reads, and writes them as gzipped CSV parts
per year with the source header beside them. This module reads the parts with DuckDB, applies the
occupancy filter (principal residence, occupancy type 1) and the rounding contract, and writes one
parquet file per year under data/hmda. The derived race, ethnicity and sex fields were never loaded;
fair lending is the Day 9 build, not this one, and the statement says so.

The rounding rules are part of the public record and of this contract: income is reported in
thousands of dollars, loan amount and property value at the midpoint of their reporting bins, and age in
bands. Nothing here identifies a person: a row is a lender, a geography, a purpose and amounts.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import polars as pl

from doorstep_contracts.common import ContractError, Rule, apply_rules, contract_digest

FIELDS = (
    "year",
    "lei",
    "msa_md",
    "state_code",
    "county_fips",
    "loan_purpose",
    "lien_status",
    "loan_amount",
    "property_value",
    "income",
    "interest_rate",
    "rate_spread",
    "loan_term",
    "ltv",
    "dti_band",
    "applicant_age",
    "total_units",
    "occupancy_type",
    "reverse_mortgage",
    "open_end",
    "business_purpose",
    "msa_md_median_family_income",
)

FILTER = {
    "fetch": "action_taken = 1 and loan_purpose in (1, 31, 32)",
    "ingest": "occupancy_type = 1 (principal residence); reverse mortgages, open end lines and business purpose loans flagged",
}

RULES = (
    Rule("income_exempt_or_missing", "income reported as exempt or missing", lambda f: pl.col("income").is_null()),
    Rule("rate_missing", "no interest rate reported", lambda f: pl.col("interest_rate").is_null()),
    Rule("term_not_30_years", "a loan term other than 360 months, excluded from the rate sensitive measures", lambda f: pl.col("loan_term") != 360),
    Rule("metro_unresolved", "a metro code that is not five digits or is the 99999 code for no metro", lambda f: pl.col("msa_md").is_null() | (pl.col("msa_md") == "99999")),
    Rule("not_principal_residence", "occupancy other than a principal residence", lambda f: pl.col("occupancy_type") != 1),
    Rule("reverse_open_or_business", "a reverse mortgage, an open end line of credit or a business purpose loan", lambda f: (pl.col("reverse_mortgage") == 1) | (pl.col("open_end") == 1) | (pl.col("business_purpose") == 1)),
    Rule("value_below_loan", "a property value below the loan amount", lambda f: pl.col("property_value") < pl.col("loan_amount")),
)

DIGEST = contract_digest("hmda", FIELDS, RULES, FILTER)


def years_available(external: Path) -> list[int]:
    folder = external / "hmda"
    years: list[int] = []
    for d in sorted(folder.glob("20[0-9][0-9]")):
        if (d / "summary.json").exists() and list(d.glob("lar_part*.csv.gz")):
            years.append(int(d.name))
    return years


def fetch_summary(external: Path, year: int) -> dict[str, object]:
    path = external / "hmda" / str(year) / "summary.json"
    loaded: dict[str, object] = json.loads(path.read_text(encoding="utf-8-sig"))
    return loaded


def read_year(con: duckdb.DuckDBPyConnection, external: Path, year: int) -> pl.DataFrame:
    folder = external / "hmda" / str(year)
    parts = sorted(folder.glob("lar_part*.csv.gz"))
    if not parts:
        raise ContractError(f"no HMDA parts for {year} under {folder}")
    glob = (folder / "lar_part*.csv.gz").as_posix()
    sql = f"""
    select
        {year}::bigint as year,
        lei,
        nullif("derived_msa-md", '') as msa_md,
        nullif(state_code, '') as state_code,
        case when county_code is null or county_code = '' or county_code = 'NA' then null else lpad(cast(county_code as varchar), 5, '0') end as county_fips,
        try_cast(loan_purpose as integer) as loan_purpose,
        try_cast(lien_status as integer) as lien_status,
        try_cast(loan_amount as double) as loan_amount,
        try_cast(property_value as double) as property_value,
        try_cast(income as double) * 1000.0 as income,
        try_cast(interest_rate as double) as interest_rate,
        try_cast(rate_spread as double) as rate_spread,
        try_cast(loan_term as integer) as loan_term,
        try_cast(loan_to_value_ratio as double) as ltv,
        nullif(debt_to_income_ratio, '') as dti_band,
        nullif(applicant_age, '') as applicant_age,
        try_cast(total_units as integer) as total_units,
        try_cast(occupancy_type as integer) as occupancy_type,
        try_cast(reverse_mortgage as integer) as reverse_mortgage,
        try_cast("open-end_line_of_credit" as integer) as open_end,
        try_cast(business_or_commercial_purpose as integer) as business_purpose,
        try_cast(ffiec_msa_md_median_family_income as double) as msa_md_median_family_income
    from read_csv('{glob}', header = true, all_varchar = true, union_by_name = true, compression = 'gzip')
    """
    frame: pl.DataFrame = con.execute(sql).pl()
    if frame.height == 0:
        raise ContractError(f"HMDA {year} read to zero rows")
    return frame


def quarantine(frame: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    flagged, report = apply_rules(frame, RULES, "hmda", "year")
    return flagged, report.frame()


def purchase_filter() -> pl.Expr:
    return pl.col("loan_purpose") == 1


def refinance_filter() -> pl.Expr:
    return pl.col("loan_purpose").is_in([31, 32])


def analysis_rows() -> pl.Expr:
    """Rows the chapters use: principal residence, not reverse, open end or business, metro resolved."""
    return ~pl.col("q_not_principal_residence") & ~pl.col("q_reverse_open_or_business") & ~pl.col("q_metro_unresolved")
