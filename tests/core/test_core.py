"""The core: the formats every surface prints, the manifest's provenance and merge, the pipeline order, the
seeded generators and the hashes caches are keyed by."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pytest
from doorstep_core.formats import FORMATS, format_value
from doorstep_core.hashing import design_hash, file_sha256
from doorstep_core.manifest import Manifest, Scribe
from doorstep_core.seeds import rng
from doorstep_pipeline import order

ROOT = Path(__file__).resolve().parents[2]


def test_every_format_prints_and_a_year_has_no_separator() -> None:
    for fmt in FORMATS:
        assert isinstance(format_value(1234.5678, fmt), str)
    assert format_value(2024, "year") == "2024"
    assert format_value(1234567, "int") == "1,234,567"
    assert format_value(0.2679, "pct1") == "26.8%"
    assert format_value(0.026, "pts1") == "+2.6 pts"
    assert format_value(0.0, "spct1") == "0.0%"
    assert format_value(31.0, "beyond1") == "beyond 30 years"
    assert format_value(12.0, "beyond0") == "12 years"
    assert format_value(366471.2, "usd0") == "$366,471"
    assert format_value(float("nan"), "float2") == "not available"
    with pytest.raises(KeyError):
        format_value(1.0, "no_such_format")


def test_manifest_values_carry_provenance_and_merge_without_losing_a_stage(tmp_path: Path) -> None:
    a = Manifest(as_of="2026-10-22", seed=1)
    Scribe(a, source="real:fhfa", population="every metro", origin="tests").put("x.one", 1.5, "float1")
    b = Manifest(as_of="2026-10-22", seed=1)
    Scribe(b, source="simulated", population="sixty metros", origin="tests", seeds=20).table(
        "t.one", ["A", "B"], ["text", "int"], [["a", 1]]
    )
    a.merge(b)
    assert a.text("x.one") == "1.5" and a.raw("x.one") == 1.5
    assert "a" in a.table_markdown("t.one")
    path = tmp_path / "m.json"
    a.save(path)
    loaded = Manifest.load(path)
    assert loaded.counts() == {"values": 1, "tables": 1, "figures": 0}
    assert loaded.values["x.one"].provenance.source == "real:fhfa"
    with pytest.raises(KeyError):
        a.text("missing")


def test_a_key_is_written_once() -> None:
    m = Manifest(as_of="2026-10-22", seed=1)
    w = Scribe(m, source="static", population="p", origin="tests")
    w.put("a.k", 1, "int")
    with pytest.raises(ValueError):
        w.put("a.k", 2, "int")
    with pytest.raises(ValueError, match="dotted"):
        w.put("k", 1, "int")


def test_the_pipeline_order_reads_only_what_ran_before_it() -> None:
    assert order.violations() == []
    assert order.violations(("chapters", "data")) != []
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    line = next(line for line in makefile.splitlines() if line.startswith("pipeline:"))
    assert tuple(line.split(":", 1)[1].split()) == order.RUN_ORDER


def test_seeded_generators_are_labelled_and_reproducible() -> None:
    a = rng(1, "bootstrap", "metros").normal(size=3)
    b = rng(1, "bootstrap", "metros").normal(size=3)
    c = rng(1, "bootstrap", "lenders").normal(size=3)
    assert np.allclose(a, b) and not np.allclose(a, c)


def test_design_and_file_hashes_change_with_their_input(tmp_path: Path) -> None:
    assert design_hash({"a": 1, "b": [1, 2]}) == design_hash({"b": [1, 2], "a": 1})
    assert design_hash({"a": 1}) != design_hash({"a": 2})
    assert re.fullmatch(r"[0-9a-f]{16}", design_hash({"a": 1}))
    f = tmp_path / "x.txt"
    f.write_text("one", encoding="utf-8")
    first = file_sha256(f)
    f.write_text("two", encoding="utf-8")
    assert file_sha256(f) != first
