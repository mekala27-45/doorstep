"""The FHFA House Price Index master file.

One CSV with every index FHFA publishes. This build keeps the quarterly metropolitan series of the
traditional index in two flavors: all-transactions (every metropolitan area and division, not
seasonally adjusted, 1975 onward) as the primary price series, and purchase-only (the hundred largest
areas, seasonally adjusted) beside it as a check. The index is a movement, not a level; the level
comes from the census in the anchor year (see the anchor module).

Where FHFA publishes metropolitan divisions instead of the whole area (eleven metros), the divisions
are carried with a flag, and the warehouse rolls them up to the area through the delineation file.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from doorstep_contracts.common import Rule, apply_rules, contract_digest, require

FIELDS = (
    "place_id",
    "place_name",
    "flavor",
    "year",
    "quarter",
    "period",
    "index_nsa",
    "index_sa",
    "is_division",
)

RULES = (
    Rule("missing_quarter", "a metro and flavor skips a quarter inside its own span", lambda f: pl.col("gap_before")),
    Rule("non_positive_index", "an index value at or below zero", lambda f: pl.col("index_nsa") <= 0),
    Rule(
        "implausible_jump",
        "a quarter on quarter change beyond thirty percent in either direction",
        lambda f: (pl.col("index_nsa") / pl.col("prev_index") - 1.0).abs() > 0.30,
    ),
)

DIGEST = contract_digest("fhfa", FIELDS, RULES, {"keep": "traditional, quarterly, MSA, all-transactions and purchase-only"})


def parse(external: Path) -> pl.DataFrame:
    path = require(external / "fhfa" / "hpi_master.csv", "the FHFA master file")
    raw = pl.read_csv(path, infer_schema_length=200_000, schema_overrides={"place_id": pl.Utf8})
    kept = (
        raw.filter(
            (pl.col("hpi_type") == "traditional")
            & (pl.col("frequency") == "quarterly")
            & (pl.col("level") == "MSA")
            & pl.col("hpi_flavor").is_in(["all-transactions", "purchase-only"])
        )
        .select(
            pl.col("place_id").cast(pl.Utf8),
            pl.col("place_name"),
            pl.col("hpi_flavor").alias("flavor"),
            pl.col("yr").cast(pl.Int64).alias("year"),
            pl.col("period").cast(pl.Int64).alias("quarter"),
            pl.col("index_nsa").cast(pl.Float64),
            pl.col("index_sa").cast(pl.Float64),
        )
        .with_columns(
            (pl.col("year").cast(pl.Utf8) + pl.lit("Q") + pl.col("quarter").cast(pl.Utf8)).alias("period"),
            pl.col("place_name").str.contains(r"\(MSAD\)").alias("is_division"),
        )
        .sort(["flavor", "place_id", "year", "quarter"])
    )
    kept = kept.with_columns(
        pl.col("index_nsa").shift(1).over(["flavor", "place_id"]).alias("prev_index"),
        ((pl.col("year") * 4 + pl.col("quarter")) - (pl.col("year") * 4 + pl.col("quarter")).shift(1).over(["flavor", "place_id"])).alias("step"),
    ).with_columns((pl.col("step").is_not_null() & (pl.col("step") != 1)).alias("gap_before"))
    return kept


def quarantine(frame: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    flagged, report = apply_rules(frame, RULES, "fhfa", "year")
    out = flagged.select([*FIELDS, *[c for c in flagged.columns if c.startswith("q_")], "quarantined"])
    return out, report.frame()


def latest_period(frame: pl.DataFrame) -> str:
    row = frame.sort(["year", "quarter"]).tail(1)
    return str(row["period"][0])
