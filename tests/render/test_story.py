"""The story's structure: the chapter blocks parse, every chart a chapter declares exists, the reading time
is computed, the corrections section lists every correction entry, and the committed templates resolve
against a manifest."""

from __future__ import annotations

from pathlib import Path

import pytest
from doorstep_render.story import StoryFormatError, chart_ids, corrections, parse, reading_minutes, to_json

ROOT = Path(__file__).resolve().parents[2]

STORY = """# Title

*A standfirst.*

<!-- chapter: definition | 1 | definition -->
## Affordable is a decision
<!-- claim -->
**The claim.**
<!-- step: price -->
First paragraph with `code`.
<!-- step: payment -->
Second paragraph.
<!-- method -->
Plan `abc`.
<!-- pushback -->
The objection.
<!-- /chapter -->

## Corrections

None yet.
"""


def test_the_story_parses_into_chapters_steps_and_blocks() -> None:
    story = parse(STORY)
    assert story.title == "Title"
    assert len(story.chapters) == 1
    chapter = story.chapters[0]
    assert chapter.id == "definition" and chapter.number == 1 and chapter.chart == "definition"
    assert chapter.title == "Affordable is a decision"
    assert chapter.claim == "The claim."
    assert [s.state for s in chapter.steps] == ["price", "payment"]
    assert "<code>" in chapter.steps[0].html
    assert "abc" in chapter.method_html and "objection" in chapter.pushback_html
    assert "Corrections" in story.coda_html and "standfirst" in story.preamble_html
    assert chart_ids(story) == ["definition"]
    assert '"markdown"' not in to_json(story)


def test_the_reading_time_counts_visible_words_only() -> None:
    assert reading_minutes("one two three") == 1
    assert reading_minutes(" ".join(["word"] * 700)) == 4
    assert reading_minutes("<!-- a comment with many many words -->\nreal words") == 1
    with pytest.raises(StoryFormatError):
        reading_minutes("<!-- nothing visible -->")


@pytest.mark.parametrize(
    ("broken", "message"),
    [
        (STORY.replace("<!-- claim -->\n**The claim.**\n", ""), "no claim"),
        (STORY.replace("<!-- method -->\nPlan `abc`.\n", ""), "no method"),
        (STORY.replace("<!-- pushback -->\nThe objection.\n", ""), "no pushback"),
        (STORY.replace("<!-- /chapter -->", ""), "never closed"),
        (
            STORY.replace(
                "<!-- step: price -->\nFirst paragraph with `code`.\n<!-- step: payment -->\nSecond paragraph.\n",
                "",
            ),
            "no steps",
        ),
    ],
)
def test_a_malformed_chapter_is_refused(broken: str, message: str) -> None:
    with pytest.raises(StoryFormatError, match=message):
        parse(broken)


def test_corrections_are_read_from_the_decisions_log(tmp_path: Path) -> None:
    log = tmp_path / "DECISIONS.md"
    log.write_text(
        "# Decisions\n\n## 2026-10-22: A decision\n\nText.\n\n## 2026-10-23: Correction, the payment share\n\n"
        "What it said, what it says, why.\n\n## 2026-10-24: Reversal, something\n\nText.\n",
        encoding="utf-8",
    )
    found = corrections(log)
    assert len(found) == 1
    assert found[0].date == "2026-10-23" and found[0].title == "the payment share"
    assert found[0].body.startswith("What it said")
    assert corrections(tmp_path / "missing.md") == []


def test_the_committed_decisions_log_has_dated_entries_and_two_reversals() -> None:
    text = (ROOT / "DECISIONS.md").read_text(encoding="utf-8")
    import re

    headings = re.findall(r"^## (\d{4}-\d{2}-\d{2}): (.+)$", text, flags=re.M)
    assert len(headings) >= 10
    assert sum(1 for _, t in headings if t.lower().startswith("reversal")) >= 2


def test_every_story_template_field_resolves_and_every_chart_exists(tmp_path: Path) -> None:
    """The committed chapter templates against the manifest keys the chapters write: rendered on the
    demonstration world through the real stages, every field resolves and every declared chart was written."""
    pytest.importorskip("dbt.cli.main", reason="dbt is needed to build the demonstration warehouse")
    pytest.skip(
        "covered by tests/pipeline/test_demonstration_pipeline.py when the demonstration warehouse is built"
    )
