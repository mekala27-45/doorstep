"""What every source contract shares: the typed frame it promises, the quarantine rules it applies,
the counts it publishes, and a digest over all three so that changing a rule forces a re-ingest.

A quarantine rule never deletes a row. It flags the row, the count is published by source and year,
and the mart that reads the row decides what to do with the flag. Day 3 of the series set the rule
and every build since has kept it: a number that was dropped silently cannot be explained to a reader.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl


class ContractError(ValueError):
    pass


@dataclass(frozen=True)
class Rule:
    name: str
    description: str
    expression: Callable[[pl.DataFrame], pl.Expr]


@dataclass
class QuarantineReport:
    source: str
    counts: list[dict[str, object]] = field(default_factory=list)

    def add(self, rule: str, year: int | None, count: int, rows: int) -> None:
        self.counts.append({"source": self.source, "rule": rule, "year": year, "flagged": count, "rows": rows})

    def frame(self) -> pl.DataFrame:
        if not self.counts:
            return pl.DataFrame(
                schema={"source": pl.Utf8, "rule": pl.Utf8, "year": pl.Int64, "flagged": pl.Int64, "rows": pl.Int64}
            )
        return pl.DataFrame(self.counts)


def apply_rules(frame: pl.DataFrame, rules: Sequence[Rule], source: str, year_column: str | None) -> tuple[pl.DataFrame, QuarantineReport]:
    """Add one boolean column per rule and a ``quarantined`` column that is true when any rule fires.
    Refuses an empty frame: a rule that reports a pass over nothing is the Day 3 bug."""
    if frame.height == 0:
        raise ContractError(f"{source}: the quarantine rules were handed no rows")
    report = QuarantineReport(source)
    out = frame
    flags: list[str] = []
    for rule in rules:
        column = f"q_{rule.name}"
        out = out.with_columns(rule.expression(out).fill_null(False).alias(column))
        flags.append(column)
        if year_column and year_column in out.columns:
            grouped = out.group_by(year_column).agg(pl.col(column).sum().alias("flagged"), pl.len().alias("rows")).sort(year_column)
            for row in grouped.iter_rows(named=True):
                report.add(rule.name, int(row[year_column]), int(row["flagged"]), int(row["rows"]))
        else:
            report.add(rule.name, None, int(out[column].sum()), out.height)
    any_flag = pl.any_horizontal([pl.col(c) for c in flags]) if flags else pl.lit(False)
    out = out.with_columns(any_flag.alias("quarantined"))
    return out, report


def contract_digest(name: str, fields: Sequence[str], rules: Sequence[Rule], extra: dict[str, object] | None = None) -> str:
    """Sixteen hex characters over the field list, the rule names and descriptions, and any stated
    filter, so a change to the contract changes the digest and the derived files are rebuilt."""
    payload = {
        "name": name,
        "fields": list(fields),
        "rules": [{"name": r.name, "description": r.description} for r in rules],
        "extra": extra or {},
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def require(path: Path, what: str) -> Path:
    if not path.exists():
        raise ContractError(f"{what} is missing: expected {path}. Run deploy/fetch-data.ps1 on a machine that reaches the host.")
    return path


def write_parquet(frame: pl.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(path, compression="zstd", statistics=True)
    return path
