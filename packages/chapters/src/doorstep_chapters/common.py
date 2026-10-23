"""What every chapter shares: the plan and its hash, the result container, the split check and the
message rule shape.

A chapter is a module with ``NUMBER``, ``SLUG``, ``TITLE``, ``plan()``, ``simulate_estimate(world)`` and
``estimate(panel, policy)``. ``plan()`` returns the claim, the estimator, the split, the family of
comparisons, the interval method and the operating points as a mapping; its design hash is registered in
results/chapters/plans.json before any estimate runs on real data, printed in the method note, and
checked by a test against the committed plan. ``estimate`` returns a ``ChapterResult`` whose values,
tables and figure the pipeline writes into the manifest; the message is chosen by a rule from the
interval of a difference, never from two point estimates, and every rule has a branch for every outcome
including the null.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import polars as pl
from doorstep_core.config import POLICY, Policy
from doorstep_core.formats import format_value
from doorstep_core.hashing import design_hash
from doorstep_core.manifest import Scalar

Row = Sequence[Scalar]


class ChapterError(ValueError):
    pass


class SplitViolation(ChapterError):
    """A chapter reported on the years it chose its parameters on."""


@dataclass(frozen=True)
class Value:
    value: Scalar
    fmt: str
    model: str = "none"

    def text(self) -> str:
        return format_value(self.value, self.fmt)


@dataclass(frozen=True)
class Table:
    columns: list[str]
    formats: list[str]
    rows: list[list[Scalar]]
    model: str = "none"


@dataclass(frozen=True)
class Figure:
    """The chart the chapter publishes: a message as its title, the conventional title as the subtitle,
    the SQL behind it and the frames the site draws."""

    title: str
    subtitle: str
    sql: str
    frames: dict[str, pl.DataFrame]
    model: str = "none"
    callout: str = ""


@dataclass(frozen=True)
class Grade:
    """One recovery study row: an estimator's estimate against the truth on one simulated world."""

    estimator: str
    estimate: float
    truth: float
    low: float | None = None
    high: float | None = None
    flag: float | None = None
    """A per world indicator the study averages: the placebo flagged the condition, the message branch, a hit."""
    detail: str = ""

    @property
    def error(self) -> float:
        return self.estimate - self.truth

    @property
    def covered(self) -> bool | None:
        if self.low is None or self.high is None:
            return None
        return self.low <= self.truth <= self.high


@dataclass
class ChapterResult:
    number: int
    slug: str
    source: str
    population: str
    branch: str
    message: str
    values: dict[str, Value] = field(default_factory=dict)
    tables: dict[str, Table] = field(default_factory=dict)
    figure: Figure | None = None
    extra_figures: dict[str, Figure] = field(default_factory=dict)
    method: dict[str, str] = field(default_factory=dict)
    pushback: str = ""
    marts: dict[str, pl.DataFrame] = field(default_factory=dict)
    reported_years: list[int] = field(default_factory=list)

    def put(self, key: str, value: Scalar, fmt: str, *, model: str = "none") -> None:
        if key in self.values:
            raise ChapterError(f"{self.slug}: value {key} written twice")
        self.values[key] = Value(value, fmt, model)

    def text(self, key: str) -> str:
        return self.values[key].text()

    def put_table(
        self,
        key: str,
        columns: Sequence[str],
        formats: Sequence[str],
        rows: Sequence[Row],
        *,
        model: str = "none",
    ) -> None:
        if key in self.tables:
            raise ChapterError(f"{self.slug}: table {key} written twice")
        if len(columns) != len(formats):
            raise ChapterError(
                f"{self.slug}: table {key} has {len(columns)} columns and {len(formats)} formats"
            )
        if not rows:
            raise ChapterError(f"{self.slug}: table {key} has no rows")
        self.tables[key] = Table(list(columns), list(formats), [list(r) for r in rows], model)


def plan_hash(plan: Mapping[str, Any]) -> str:
    return design_hash(dict(plan))


def split_for(policy: Policy = POLICY) -> dict[str, Any]:
    return {
        "choose_on": [policy.fit_first_year, policy.fit_last_year],
        "report_on": [policy.test_first_year, "latest"],
    }


def check_reporting_years(
    plan: Mapping[str, Any], reported_years: Sequence[int], policy: Policy = POLICY
) -> None:
    """A chapter whose plan declares the split may not report its headline on the years it chose on."""
    split = plan.get("split")
    if not isinstance(split, Mapping) or "choose_on" not in split:
        return
    lo, hi = split["choose_on"]
    inside = sorted(y for y in reported_years if int(lo) <= int(y) <= int(hi))
    if inside:
        raise SplitViolation(
            f"headline reported on fitting years {inside}; the plan reports from {split['report_on'][0]}"
        )


@dataclass(frozen=True)
class Branch:
    name: str
    text: str


MessageRule = Callable[..., Branch]


def interval_text(low: float, high: float, fmt: str) -> str:
    return f"{format_value(low, fmt)} to {format_value(high, fmt)}"


def weighted_mean(frame: pl.DataFrame, value: str, weight: str) -> float | None:
    sub = frame.filter(pl.col(value).is_not_null() & pl.col(weight).is_not_null() & (pl.col(weight) > 0))
    if sub.height == 0:
        return None
    w = sub[weight].sum()
    return float((sub[value] * sub[weight]).sum() / w) if w else None


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise ChapterError(message)
