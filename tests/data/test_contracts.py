"""Every quarantine rule three ways: a clean frame passes with nothing flagged, the planted defect is flagged
and counted, and an empty frame is refused rather than reported as a pass. Plus the loan rounding rules, the
refinance subset, the ACS gap and the geography tests the spec names."""

from __future__ import annotations

import datetime as dt

import polars as pl
import pytest
from doorstep_contracts import acs, fhfa, geography, hmda, hud, permits, pmms, population
from doorstep_contracts.common import ContractError, QuarantineReport, apply_rules, contract_digest


def _flags(frame: pl.DataFrame, rule: str) -> int:
    return int(frame[f"q_{rule}"].sum())


# FHFA


def _fhfa(rows: list[dict[str, object]]) -> pl.DataFrame:
    base = {"place_name": "X", "flavor": "all_transactions", "index_sa": None, "is_division": False}
    return pl.DataFrame([{**base, **r} for r in rows])


def test_fhfa_rules_pass_a_clean_series() -> None:
    frame = _fhfa(
        [
            {"place_id": "1", "year": 2020, "quarter": 1, "period": "2020Q1", "index_nsa": 100.0, "prev_index": None, "gap_before": False},
            {"place_id": "1", "year": 2020, "quarter": 2, "period": "2020Q2", "index_nsa": 103.0, "prev_index": 100.0, "gap_before": False},
        ]
    )
    flagged, report = fhfa.quarantine(frame)
    assert not flagged["quarantined"].any()
    assert report.filter(pl.col("flagged") > 0).height == 0


def test_fhfa_rules_flag_a_gap_a_jump_and_a_bad_level() -> None:
    frame = _fhfa(
        [
            {"place_id": "1", "year": 2020, "quarter": 1, "period": "2020Q1", "index_nsa": 100.0, "prev_index": None, "gap_before": False},
            {"place_id": "1", "year": 2020, "quarter": 3, "period": "2020Q3", "index_nsa": 150.0, "prev_index": 100.0, "gap_before": True},
            {"place_id": "1", "year": 2020, "quarter": 4, "period": "2020Q4", "index_nsa": 0.0, "prev_index": 150.0, "gap_before": False},
        ]
    )
    flagged, report = fhfa.quarantine(frame)
    assert _flags(flagged, "missing_quarter") == 1
    assert _flags(flagged, "implausible_jump") == 2
    assert _flags(flagged, "non_positive_index") == 1
    assert int(report.filter(pl.col("rule") == "missing_quarter")["flagged"].sum()) == 1


def test_fhfa_rules_refuse_an_empty_frame() -> None:
    with pytest.raises(ContractError, match="no rows"):
        fhfa.quarantine(_fhfa([]).clear())


# PMMS


def _pmms(rows: list[dict[str, object]]) -> pl.DataFrame:
    return pl.DataFrame(rows)


def test_pmms_rules_three_ways() -> None:
    clean = _pmms(
        [
            {"week": dt.date(2024, 1, 4), "year": 2024, "quarter": 1, "period": "2024Q1", "rate_30": 6.6, "points_30": 0.6, "rate_15": 5.9, "days_since_prev": None},
            {"week": dt.date(2024, 1, 11), "year": 2024, "quarter": 1, "period": "2024Q1", "rate_30": 6.7, "points_30": 0.6, "rate_15": 5.9, "days_since_prev": 7},
        ]
    )
    flagged, _ = pmms.quarantine(clean)
    assert not flagged["quarantined"].any()
    bad = clean.with_columns(pl.Series("days_since_prev", [None, 21]), pl.Series("rate_30", [6.6, 25.0]))
    flagged, _ = pmms.quarantine(bad)
    assert _flags(flagged, "missing_week") == 1 and _flags(flagged, "implausible_rate") == 1
    with pytest.raises(ContractError):
        pmms.quarantine(clean.clear())


# ACS


def _acs(rows: list[dict[str, object]]) -> pl.DataFrame:
    base = {"cbsa_code": "35620", "name": "New York", "table": "B19013", "variable": "B19013_001", "source": "census", "is_national": False}
    return pl.DataFrame([{**base, **r} for r in rows], schema_overrides={"estimate": pl.Float64, "moe": pl.Float64})


def test_acs_rules_three_ways() -> None:
    clean = _acs([{"year": 2019, "estimate": 80_000.0, "moe": 1_200.0}, {"year": 2021, "estimate": 85_000.0, "moe": 1_300.0}])
    flagged, _ = acs.quarantine(clean)
    assert not flagged["quarantined"].any()
    planted = _acs(
        [
            {"year": 2019, "estimate": -666_666_666.0, "moe": -222_222_222.0},
            {"year": 2019, "estimate": 500.0, "moe": 900.0},
            {"year": 2019, "estimate": 500.0, "moe": -5.0},
        ]
    )
    flagged, report = acs.quarantine(planted)
    assert _flags(flagged, "jam_value") == 1
    assert _flags(flagged, "moe_exceeds_estimate") == 1
    assert _flags(flagged, "negative_moe") == 1
    assert set(report["rule"]) == {"jam_value", "moe_exceeds_estimate", "negative_moe"}
    with pytest.raises(ContractError):
        acs.quarantine(clean.clear())


def test_the_acs_gap_is_carried_as_a_gap_and_a_planted_2020_row_is_rejected() -> None:
    frame = _acs([{"year": y, "estimate": 1.0, "moe": 0.1} for y in (2018, 2019, 2021, 2022)])
    years = acs.years_present(frame)
    assert 2020 not in years and years == [2018, 2019, 2021, 2022]
    planted = _acs([{"year": 2020, "estimate": 1.0, "moe": 0.1}])
    with pytest.raises(ContractError, match="2020"):
        acs.refuse_gap_year(planted)


# HUD


def test_hud_rules_three_ways() -> None:
    base = {"county_fips": "36061", "fiscal_year": 2024, "hud_area_code": "METRO35620M35620", "hud_area_name": "New York", "cbsa_code": "35620"}
    clean = pl.DataFrame([{**base, "fmr_0": 1500.0, "fmr_1": 1700.0, "fmr_2": 2000.0, "fmr_3": 2500.0, "fmr_4": 2700.0}])
    flagged, _ = hud.quarantine_fmr(clean)
    assert not flagged["quarantined"].any()
    bad = pl.DataFrame([{**base, "fmr_0": 1500.0, "fmr_1": 2100.0, "fmr_2": 0.0, "fmr_3": 2500.0, "fmr_4": 2700.0}])
    flagged, _ = hud.quarantine_fmr(bad)
    assert _flags(flagged, "non_positive_rent") == 1 and _flags(flagged, "bedroom_order") == 1
    with pytest.raises(ContractError):
        hud.quarantine_fmr(clean.clear())
    il_clean = pl.DataFrame([{**base, "median_family_income": 100_000.0, "l30_4": 30_000.0, "l50_4": 50_000.0, "l80_4": 80_000.0}])
    flagged, _ = hud.quarantine_il(il_clean)
    assert not flagged["quarantined"].any()
    il_bad = pl.DataFrame([{**base, "median_family_income": 0.0, "l30_4": 30_000.0, "l50_4": 90_000.0, "l80_4": 80_000.0}])
    flagged, _ = hud.quarantine_il(il_bad)
    assert _flags(flagged, "non_positive_income") == 1 and _flags(flagged, "limit_order") == 1


# Permits


def _permits(units_total: float, reported: float, fips: str = "36061") -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "year": 2023, "partial_through_month": None, "county_fips": fips, "county_name": "New York",
                "units_1": units_total, "units_2": 0.0, "units_3_4": 0.0, "units_5_plus": 0.0,
                "units_total": units_total, "buildings_total": units_total, "value_total": 1.0, "units_total_reported": reported,
            }
        ]
    )


def test_permit_rules_three_ways() -> None:
    flagged, _ = permits.quarantine(_permits(100.0, 100.0))
    assert not flagged["quarantined"].any()
    flagged, _ = permits.quarantine(pl.concat([_permits(-1.0, -1.0), _permits(100.0, 40.0), _permits(5.0, 5.0, "3606")]))
    assert _flags(flagged, "negative_units") == 1
    assert _flags(flagged, "imputed_share_high") >= 1
    assert _flags(flagged, "malformed_fips") == 1
    with pytest.raises(ContractError):
        permits.quarantine(_permits(1.0, 1.0).clear())


def test_permit_years_must_be_continuous() -> None:
    full = pl.concat([_permits(1.0, 1.0).with_columns(pl.lit(y).alias("year")) for y in (2021, 2022, 2023)])
    permits.refuse_missing_years(full)
    with_hole = pl.concat([_permits(1.0, 1.0).with_columns(pl.lit(y).alias("year")) for y in (2021, 2023)])
    with pytest.raises(ContractError, match="2022"):
        permits.refuse_missing_years(with_hole)


# Population


def _pop(rows: list[dict[str, object]]) -> pl.DataFrame:
    base = {"county_fips": "36061", "births": 10.0, "deaths": 5.0, "international_migration": 1.0, "domestic_migration": -2.0}
    return pl.DataFrame([{**base, **r} for r in rows])


def test_population_rules_three_ways_and_the_latest_vintage_wins() -> None:
    clean = _pop([{"year": 2019, "vintage": 2019, "population": 1000.0, "vintages_for_year": 1}])
    flagged, _ = population.quarantine(clean)
    assert not flagged["quarantined"].any()
    overlap = _pop(
        [
            {"year": 2019, "vintage": 2019, "population": 1000.0, "vintages_for_year": 2},
            {"year": 2019, "vintage": 2020, "population": 0.0, "vintages_for_year": 2},
        ]
    )
    flagged, _ = population.quarantine(overlap)
    assert _flags(flagged, "vintage_overlap") == 2 and _flags(flagged, "non_positive_population") == 1
    latest = population.latest_per_year(overlap)
    assert latest.height == 1 and int(latest["vintage"][0]) == 2020
    with pytest.raises(ContractError):
        population.quarantine(clean.clear())


# Geography


def _geo(rows: list[dict[str, object]]) -> pl.DataFrame:
    base = {"cbsa_title": "Area", "kind": "metropolitan", "division_code": None, "division_title": None, "county_name": "C", "state_name": "S", "central": True}
    return pl.DataFrame([{**base, **r} for r in rows], schema_overrides={"division_code": pl.Utf8, "division_title": pl.Utf8})


def test_every_county_maps_to_one_area_per_vintage_and_a_planted_double_is_rejected() -> None:
    clean = _geo(
        [
            {"vintage": 2023, "cbsa_code": "35620", "county_fips": "36061", "areas_for_county": 1},
            {"vintage": 2023, "cbsa_code": "35620", "county_fips": "36047", "areas_for_county": 1},
            {"vintage": 2020, "cbsa_code": "35620", "county_fips": "36061", "areas_for_county": 1},
        ]
    )
    flagged, _ = geography.quarantine(clean)
    assert not flagged["quarantined"].any()
    doubled = _geo(
        [
            {"vintage": 2023, "cbsa_code": "35620", "county_fips": "36061", "areas_for_county": 2},
            {"vintage": 2023, "cbsa_code": "35614", "county_fips": "36061", "areas_for_county": 2},
            {"vintage": 2023, "cbsa_code": "35620", "county_fips": "3606", "areas_for_county": 1},
        ]
    )
    flagged, report = geography.quarantine(doubled)
    assert _flags(flagged, "county_in_two_areas") == 2
    assert _flags(flagged, "malformed_fips") == 1
    assert int(report.filter(pl.col("rule") == "county_in_two_areas")["flagged"].sum()) == 2
    with pytest.raises(ContractError):
        geography.quarantine(clean.clear())


def test_aliases_name_a_recode_a_merge_a_dissolution_and_a_split() -> None:
    frame = _geo(
        [
            # the latest vintage: Cleveland under its new code, San Juan with the county Fajardo had, two areas
            # that split an earlier one between them
            {"vintage": 2023, "cbsa_code": "17410", "county_fips": "39035", "areas_for_county": 1},
            {"vintage": 2023, "cbsa_code": "17410", "county_fips": "39055", "areas_for_county": 1},
            {"vintage": 2023, "cbsa_code": "17410", "county_fips": "39085", "areas_for_county": 1},
            {"vintage": 2023, "cbsa_code": "41980", "county_fips": "72127", "areas_for_county": 1},
            {"vintage": 2023, "cbsa_code": "41980", "county_fips": "72053", "areas_for_county": 1},
            {"vintage": 2023, "cbsa_code": "25060", "county_fips": "28047", "areas_for_county": 1},
            {"vintage": 2023, "cbsa_code": "26000", "county_fips": "28059", "areas_for_county": 1},
            # the earlier vintage
            {"vintage": 2020, "cbsa_code": "17460", "county_fips": "39035", "areas_for_county": 1},
            {"vintage": 2020, "cbsa_code": "17460", "county_fips": "39055", "areas_for_county": 1},
            {"vintage": 2020, "cbsa_code": "41980", "county_fips": "72127", "areas_for_county": 1},
            {"vintage": 2020, "cbsa_code": "21940", "county_fips": "72053", "areas_for_county": 1},
            {"vintage": 2020, "cbsa_code": "99990", "county_fips": "01001", "areas_for_county": 1},
            {"vintage": 2020, "cbsa_code": "37700", "county_fips": "28047", "areas_for_county": 1},
            {"vintage": 2020, "cbsa_code": "37700", "county_fips": "28059", "areas_for_county": 1},
        ]
    )
    flagged, _ = geography.quarantine(frame)
    aliases = geography.aliases(flagged)
    by_code = {row["cbsa_code"]: row for row in aliases.iter_rows(named=True)}
    assert set(by_code) == {"17460", "21940", "99990", "37700"}
    assert by_code["17460"]["rule"] == "recode" and by_code["17460"]["latest_code"] == "17410"
    assert by_code["17460"]["counties"] == 2 and by_code["17460"]["counties_in_latest"] == 2
    assert by_code["21940"]["rule"] == "merged" and by_code["21940"]["latest_code"] == "41980"
    assert by_code["99990"]["rule"] == "dissolved" and by_code["99990"]["latest_code"] is None
    assert by_code["37700"]["rule"] == "split" and by_code["37700"]["latest_code"] is None
    # one vintage only: nothing to alias, the schema stays
    single = geography.aliases(flagged.filter(pl.col("vintage") == 2023))
    assert single.height == 0 and list(single.columns) == list(aliases.columns)


def test_areas_and_divisions_of_a_vintage() -> None:
    frame = _geo(
        [
            {"vintage": 2023, "cbsa_code": "35620", "county_fips": "36061", "areas_for_county": 1, "division_code": "35614", "division_title": "New York"},
            {"vintage": 2023, "cbsa_code": "35620", "county_fips": "34003", "areas_for_county": 1, "division_code": "35084", "division_title": "Newark"},
            {"vintage": 2023, "cbsa_code": "10180", "county_fips": "48059", "areas_for_county": 1},
        ]
    )
    areas = geography.areas(frame, 2023)
    assert areas.height == 2 and int(areas.filter(pl.col("cbsa_code") == "35620")["counties"][0]) == 2
    assert geography.latest_vintage(frame) == 2023


# HMDA


def _loans(rows: list[dict[str, object]]) -> pl.DataFrame:
    base = {
        "year": 2023, "lei": "LEI0", "msa_md": "35620", "state_code": "NY", "county_fips": "36061", "loan_purpose": 1, "lien_status": 1,
        "loan_amount": 405_000.0, "property_value": 505_000.0, "income": 120_000.0, "interest_rate": 6.5, "rate_spread": 0.3,
        "loan_term": 360, "ltv": 80.0, "dti_band": "36%-<41%", "applicant_age": "35-44", "total_units": 1, "occupancy_type": 1,
        "reverse_mortgage": 2, "open_end": 2, "business_purpose": 2, "msa_md_median_family_income": 100_000.0,
    }
    return pl.DataFrame([{**base, **r} for r in rows])


def test_loan_rules_pass_a_clean_loan() -> None:
    flagged, report = hmda.quarantine(_loans([{}]), {"36061"})
    assert not flagged["quarantined"].any()
    assert report.filter(pl.col("flagged") > 0).height == 0
    assert flagged.filter(hmda.analysis_rows()).height == 1


def test_loan_rules_flag_each_planted_defect() -> None:
    planted = _loans(
        [
            {"income": None},
            {"interest_rate": None},
            {"loan_term": 180},
            {"msa_md": None, "county_fips": "99999"},
            {"occupancy_type": 2},
            {"reverse_mortgage": 1},
            {"property_value": 100_000.0},
        ]
    )
    flagged, _ = hmda.quarantine(planted, {"36061"})
    for rule in ("income_exempt_or_missing", "rate_missing", "term_not_30_years", "metro_unresolved", "not_principal_residence", "reverse_open_or_business", "value_below_loan"):
        assert _flags(flagged, rule) == 1, rule
    assert flagged.filter(hmda.analysis_rows()).height == 4


def test_a_loan_in_a_metro_county_resolves_without_a_reported_code() -> None:
    frame = _loans([{"msa_md": None, "county_fips": "36061"}, {"msa_md": None, "county_fips": "30001"}])
    flagged, _ = hmda.quarantine(frame, {"36061"})
    assert flagged["q_metro_unresolved"].to_list() == [False, True]


def test_loan_rules_refuse_an_empty_frame() -> None:
    with pytest.raises(ContractError):
        hmda.quarantine(_loans([{}]).clear(), {"36061"})


def test_the_refinance_subset_never_enters_the_purchase_measures() -> None:
    frame = _loans([{"loan_purpose": 1}, {"loan_purpose": 31}, {"loan_purpose": 32}, {"loan_purpose": 2}])
    assert frame.filter(hmda.purchase_filter()).height == 1
    assert frame.filter(hmda.refinance_filter()).height == 2
    assert frame.filter(hmda.purchase_filter() & hmda.refinance_filter()).height == 0


def test_the_rounding_rules_are_part_of_the_contract() -> None:
    assert "thousands" in hmda.FILTER["rounding"]
    assert hmda.DIGEST == contract_digest("hmda", hmda.FIELDS, hmda.RULES, hmda.FILTER)


# The report shape


def test_apply_rules_reports_by_year_and_refuses_nothing() -> None:
    frame = pl.DataFrame({"year": [2020, 2020, 2021], "x": [1, -1, -2]})
    from doorstep_contracts.common import Rule

    rules = (Rule("negative", "x below zero", lambda f: pl.col("x") < 0),)
    flagged, report = apply_rules(frame, rules, "test", "year")
    assert flagged["quarantined"].to_list() == [False, True, True]
    counts = report.frame().sort("year")
    assert counts["flagged"].to_list() == [1, 1] and counts["rows"].to_list() == [2, 1]
    assert QuarantineReport("empty").frame().height == 0
    with pytest.raises(ContractError):
        apply_rules(frame.clear(), rules, "test", "year")
