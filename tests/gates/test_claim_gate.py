"""The claim gate as a renderer: a clean pass, a document edited by hand, a digit typed into a template,
and a refusal to run over nothing. Also the pre registration gate for the chapter plans."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from doorstep_chapters import c1_definition, c4_supply, plans
from doorstep_chapters.common import SplitViolation, check_reporting_years, plan_hash
from doorstep_core.config import POLICY
from doorstep_core.manifest import Manifest, Scribe
from doorstep_render.render import (
    ClaimGateError,
    Renderer,
    Target,
    hand_typed_numbers,
    load_allowed_literals,
)


def _manifest() -> Manifest:
    m = Manifest(as_of="2026-10-22", seed=1)
    w = Scribe(m, source="simulated", population="a test", origin="tests")
    w.put("ch1.diff", 0.026, "pts1")
    w.put("story.chapters", 8, "int")
    return m


def _root(tmp_path: Path, template: str) -> Path:
    (tmp_path / "docs" / "templates").mkdir(parents=True)
    (tmp_path / "docs" / "templates" / "NOTE.md.j2").write_text(template, encoding="utf-8")
    (tmp_path / "DECISIONS.md").write_text("# Decisions\n", encoding="utf-8")
    return tmp_path


def _renderer(root: Path, manifest: Manifest) -> Renderer:
    return Renderer(root, manifest, [Target("NOTE.md.j2", "NOTE.md")], [root / "docs" / "templates"])


def test_claim_gate_passes_a_document_it_rendered(tmp_path: Path) -> None:
    root = _root(tmp_path, "The share moved {{ v('ch1.diff') }} over {{ v('story.chapters') }} chapters.\n")
    r = _renderer(root, _manifest())
    written = r.write_all()
    assert (root / "NOTE.md").read_text(encoding="utf-8") == "The share moved +2.6 pts over 8 chapters.\n"
    assert written == [root / "NOTE.md"]
    assert r.check_all() == []


def test_claim_gate_catches_a_number_edited_into_a_document(tmp_path: Path) -> None:
    root = _root(tmp_path, "The share moved {{ v('ch1.diff') }}.\n")
    r = _renderer(root, _manifest())
    r.write_all()
    (root / "NOTE.md").write_text("The share moved +3.1 pts.\n", encoding="utf-8")
    drifts = r.check_all()
    assert len(drifts) == 1
    assert "+2.6 pts" in drifts[0].diff and "+3.1 pts" in drifts[0].diff


def test_claim_gate_catches_a_digit_typed_into_a_template() -> None:
    assert hand_typed_numbers("The share moved {{ v('ch1.diff') }} since 2006\n", []) == ["2006"]
    assert hand_typed_numbers("Apache 2.0 and {{ v('x') }}", ["Apache 2.0"]) == []


def test_allowed_literals_skip_comments_and_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "allowed.txt"
    path.write_text("# a comment\nApache 2.0\n\n/v1/\n", encoding="utf-8")
    assert load_allowed_literals(path) == ["Apache 2.0", "/v1/"]


def test_claim_gate_refuses_nothing(tmp_path: Path) -> None:
    root = _root(tmp_path, "x\n")
    with pytest.raises(ClaimGateError, match="no documents"):
        Renderer(root, _manifest(), [], [root / "docs" / "templates"])
    with pytest.raises(ClaimGateError, match="empty manifest"):
        _renderer(root, Manifest(as_of="2026-10-22", seed=1))


def test_claim_gate_refuses_an_unknown_field(tmp_path: Path) -> None:
    root = _root(tmp_path, "{{ v('does.not.exist') }}\n")
    with pytest.raises(KeyError):
        _renderer(root, _manifest()).write_all()


# Pre registration


def test_every_plan_hash_is_stable_and_registered(tmp_path: Path) -> None:
    path = tmp_path / "plans.json"
    first = plans.register(path)
    again = plans.register(path)
    assert first == again
    assert set(first) == {m.SLUG for m in plans.MODULES}
    for module in plans.MODULES:
        assert first[module.SLUG] == plan_hash(module.plan(POLICY))
    assert plans.registered_hashes(path) == first


def test_a_plan_changed_after_registration_fails_the_gate(tmp_path: Path) -> None:
    path = tmp_path / "plans.json"
    plans.register(path)
    stored = json.loads(path.read_text(encoding="utf-8"))
    for entry in stored["plans"]:
        if entry["slug"] == c4_supply.SLUG:
            entry["hash"] = "0" * 16
    path.write_text(json.dumps(stored), encoding="utf-8")
    with pytest.raises(plans.RegistrationError, match="changed after registration"):
        plans.register(path)


def test_a_chapter_that_reports_on_its_fitting_years_is_rejected() -> None:
    plan = c1_definition.plan(POLICY)
    check_reporting_years(plan, [POLICY.test_first_year, POLICY.test_first_year + 1], POLICY)
    with pytest.raises(SplitViolation):
        check_reporting_years(plan, [POLICY.fit_first_year + 1], POLICY)
    # A plan with no fitted split (the supply windows) is not checked, and says so by returning.
    check_reporting_years(c4_supply.plan(POLICY), [2010, 2015], POLICY)
