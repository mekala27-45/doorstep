"""Three tests per text gate: a clean pass, the defect it exists for, and a refusal to pass nothing."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts import check_no_em_dash, check_statement, check_vocabulary, scan_for_planted_identifiers  # noqa: E402
from doorstep_core.statements import STATEMENT  # noqa: E402


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


# Dashes


def test_dash_gate_passes_clean_text(tmp_path: Path) -> None:
    files = [_write(tmp_path, "a.md", "A plain sentence, with a comma and a hyphen-ated word.\n")]
    assert check_no_em_dash.check(tmp_path, files) == 1


def test_dash_gate_rejects_an_em_dash(tmp_path: Path) -> None:
    files = [_write(tmp_path, "a.md", "A sentence " + chr(0x2014) + " with the banned character.\n")]
    with pytest.raises(ValueError, match="dash gate failed"):
        check_no_em_dash.check(tmp_path, files)


def test_dash_gate_refuses_nothing(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no files"):
        check_no_em_dash.check(tmp_path, [])


# Vocabulary


def test_vocabulary_gate_passes_plain_prose(tmp_path: Path) -> None:
    files = [_write(tmp_path, "a.md", "The payment share rose. The ranking changed for nine metros.\n")]
    assert check_vocabulary.check(tmp_path, files) == 1


def test_vocabulary_gate_rejects_filler(tmp_path: Path) -> None:
    word = "lever" + "age"
    files = [_write(tmp_path, "a.md", f"We {word} the warehouse to find the answer.\n")]
    with pytest.raises(ValueError):
        check_vocabulary.check(tmp_path, files)


def test_vocabulary_gate_refuses_nothing(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        check_vocabulary.check(tmp_path, [])


# The statement


def test_statement_gate_passes_a_surface_that_carries_it(tmp_path: Path) -> None:
    files = [_write(tmp_path, "README.md", f"# Title\n\n> {STATEMENT}\n")]
    assert check_statement.check(tmp_path, files) == 1


def test_statement_gate_rejects_a_surface_without_it(tmp_path: Path) -> None:
    files = [_write(tmp_path, "README.md", "# Title\n\nNo statement here.\n")]
    with pytest.raises(ValueError, match="missing the statement"):
        check_statement.check(tmp_path, files)


def test_statement_gate_refuses_nothing(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no surfaces"):
        check_statement.check(tmp_path, [])


# The identifier scan


def test_identifier_scan_passes_clean_published_files(tmp_path: Path) -> None:
    files = [_write(tmp_path, "manifest.json", '{"values": {"ch1.diff": {"value": 0.026}}}')]
    assert scan_for_planted_identifiers.check(tmp_path, files, planted={"plantedperson_quiddle"}) == 1


def test_identifier_scan_finds_a_planted_household_and_an_email(tmp_path: Path) -> None:
    files = [
        _write(
            tmp_path,
            "checks.json",
            '{"check": {"metro": "35620", "note": "saved by plantedperson_quiddle", "email": "a@private-mail.net"}}',
        )
    ]
    with pytest.raises(ValueError) as caught:
        scan_for_planted_identifiers.check(tmp_path, files, planted={"plantedperson_quiddle"})
    assert "planted identifier" in str(caught.value)
    assert "email address" in str(caught.value)


def test_identifier_scan_finds_a_raw_loan_row_and_a_tract_column(tmp_path: Path) -> None:
    import polars as pl

    raw = _write(tmp_path, "rows.csv", "activity_year,lei,derived_msa-md,state_code,county_code,census_tract\n2024,X,,PA,42057,42057960300\n")
    with pytest.raises(ValueError, match="hmda raw header"):
        scan_for_planted_identifiers.check(tmp_path, [raw], planted=set())
    table = tmp_path / "loans.parquet"
    pl.DataFrame({"cbsa_code": ["35620"], "census_tract": ["36061000100"]}).write_parquet(table)
    with pytest.raises(ValueError, match="registrant column 'census_tract'"):
        scan_for_planted_identifiers.check(tmp_path, [table], planted=set())


def test_identifier_scan_refuses_nothing(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no files"):
        scan_for_planted_identifiers.check(tmp_path, [], planted=set())


def test_card_numbers_need_luhn_and_a_clean_boundary() -> None:
    assert scan_for_planted_identifiers.find_card_numbers("card 4111 1111 1111 1111 here") == ["4111111111111111"]
    assert scan_for_planted_identifiers.find_card_numbers("id 4111111111111111a") == []
    assert scan_for_planted_identifiers.find_card_numbers("not valid 4111 1111 1111 1112") == []
