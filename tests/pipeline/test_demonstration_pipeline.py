"""The pipeline end to end on the demonstration world: the simulator's export through the real warehouse, the
metric layer, the eight chapters, the manifest, the claim gate and the story parser. Slow (a few minutes) and
it needs dbt and some memory, so it is one test module with one session fixture, run in CI's pipeline job.

Every document template is rendered here against a manifest with every chapter present, so a template field
that no stage writes fails before the real run does; and every chart a chapter declares in the story must have
been written by the chapters stage.
"""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from doorstep_core.manifest import Manifest
from doorstep_core.paths import Paths

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    os.environ.get("DOORSTEP_SKIP_PIPELINE_TEST") == "1", reason="the pipeline test was skipped by request"
)


@dataclass(frozen=True)
class DemoPaths(Paths):
    """The repository's warehouse, templates and scripts; data, results and the warehouse file under a temp root."""

    home: Path = Path(".")

    @property
    def data(self) -> Path:
        return self.home / "data"

    @property
    def results(self) -> Path:
        return self.home / "results"

    @property
    def warehouse_db(self) -> Path:
        return self.home / "warehouse.duckdb"

    @property
    def scratch(self) -> Path:
        return self.home / "scratch"

    @property
    def exports(self) -> Path:
        # The demonstration run writes its workbook and bundle under the temp root too; the first version
        # wrote them into the repository's exports/ and a test run overwrote the real bundle in the tree.
        return self.home / "exports"


@pytest.fixture(scope="module")
def demo(tmp_path_factory: pytest.TempPathFactory) -> Iterator[DemoPaths]:
    pytest.importorskip("dbt.cli.main", reason="dbt is needed to build the demonstration warehouse")
    home = tmp_path_factory.mktemp("demo")
    p = DemoPaths(root=ROOT, home=home)
    env = {
        "DOORSTEP_DATA_DIR": str(p.data),
        "DOORSTEP_RESULTS_DIR": str(p.results),
        "DOORSTEP_WAREHOUSE_PATH": str(p.warehouse_db),
        "DOORSTEP_DUCKDB_TMP": str(p.scratch / "duckdb_tmp"),
    }
    saved = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        from doorstep_pipeline.stages import chapters, exports, metrics, warehouse
        from doorstep_sim.metros import DEMONSTRATION, generate
        from doorstep_sim.sources import export

        world = generate(DEMONSTRATION, 20261022, n_metros=24)
        export(world, p.external, p.derived, p.hmda, loan_scale=0.2)
        # the data stage never runs here, so the quarantine report the warehouse ships as a mart is the one the
        # geography rules write over the exported delineations (every rule, nothing flagged)
        import polars as pl
        from doorstep_contracts import geography

        delineations = pl.read_parquet(p.derived / "delineations.parquet").drop(
            "q_county_in_two_areas", "q_malformed_fips", "quarantined"
        )
        _, report = geography.quarantine(delineations.with_columns(pl.lit(1).alias("areas_for_county")))
        (p.results / "data").mkdir(parents=True, exist_ok=True)
        report.write_parquet(p.results / "data" / "quarantine.parquet")
        warehouse.run(p)
        metrics.run(p)
        chapters.run(p, replicates=40, draws=200)
        exports.run(p)
        yield p
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(home, ignore_errors=True)


def test_the_warehouse_and_the_metric_layer_built(demo: DemoPaths) -> None:
    wh = Manifest.load(demo.results / "warehouse" / "manifest.json")
    assert wh.raw("warehouse.tests_failed") == 0
    assert int(wh.raw("warehouse.tests")) >= 100  # type: ignore[arg-type]
    m = Manifest.load(demo.results / "metrics" / "manifest.json")
    assert m.raw("metrics.disagreements") == 0 and int(m.raw("metrics.count")) >= 14  # type: ignore[arg-type]


def test_every_chapter_wrote_its_plan_its_values_and_its_chart(demo: DemoPaths) -> None:
    ch = Manifest.load(demo.results / "chapters" / "manifest.json")
    plans = json.loads((demo.results / "chapters" / "plans.json").read_text(encoding="utf-8"))
    hashes = {p["slug"]: p["hash"] for p in plans["plans"]}
    for n in range(1, 9):
        slug = str(ch.raw(f"ch{n}.slug"))
        assert ch.raw(f"ch{n}.plan_hash") == hashes[slug]
        assert ch.raw(f"ch{n}.message") and ch.raw(f"ch{n}.pushback")
    charts = {c.stem for c in (demo.results / "charts").glob("*.json")}
    assert {
        "definition",
        "rate_shock",
        "lock_in",
        "burden",
        "supply",
        "ranking",
        "buyers",
        "migration",
        "decision",
    } <= charts
    for name in ("calc_metros.parquet", "calc_quarters.parquet", "calc_meta.json"):
        assert (demo.marts / name).exists()


def test_every_template_resolves_and_every_story_chart_exists(demo: DemoPaths, tmp_path: Path) -> None:
    """Assemble with the real data, simulate and recovery manifests beside the demonstration's own (the data stage
    reads the raw files, which the demonstration does not have), then render every template and parse the story."""
    from doorstep_pipeline.stages import assemble
    from doorstep_render.render import Renderer
    from doorstep_render.story import chart_ids, parse
    from doorstep_render.targets import discover, template_roots

    for stage in ("data", "simulate", "recovery"):
        src = ROOT / "results" / stage / "manifest.json"
        if not src.exists():
            pytest.skip(f"results/{stage}/manifest.json is not built in this checkout")
        (demo.results / stage).mkdir(exist_ok=True)
        shutil.copy(src, demo.results / stage / "manifest.json")
    merged = assemble.run(demo)
    assert merged.raw("story.chapters") == 8
    out_root = tmp_path / "render"
    out_root.mkdir()
    r = Renderer(out_root, merged, discover(ROOT), template_roots(ROOT))
    r.env.globals["inline"] = lambda rel: (ROOT / rel).read_text(encoding="utf-8").rstrip("\n")
    written = r.write_all()
    assert len(written) >= 13
    assert r.check_all() == []
    story = parse((out_root / "story" / "story.md").read_text(encoding="utf-8"))
    assert len(story.chapters) == 8 and story.reading_minutes >= 10
    charts = {c.stem for c in (demo.results / "charts").glob("*.json")}
    assert set(chart_ids(story)) <= charts
    for chapter in story.chapters:
        assert chapter.steps and chapter.method_html and chapter.pushback_html
    briefing = (out_root / "report" / "briefing.md").read_text(encoding="utf-8")
    assert briefing.count("### What the housing economist would push back on") == 9
