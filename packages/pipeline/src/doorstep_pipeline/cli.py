"""The pipeline, one command per stage, in the order the Makefile runs them."""

from __future__ import annotations

import typer
from doorstep_core.log import configure
from doorstep_core.paths import paths

app = typer.Typer(add_completion=False, help="doorstep: can anyone still afford a home, in eight chapters")


@app.callback()
def main() -> None:
    configure()


@app.command()
def data() -> None:
    """Every source into typed, flagged parquet: the index, the census tables, rents, rates, permits, people, loans, the crosswalk."""
    from doorstep_pipeline.stages import data as stage

    manifest = stage.run(paths())
    typer.echo(f"data: {manifest.counts()}")


@app.command()
def simulate() -> None:
    """The demonstration country with its truth tables, under data/sim."""
    from doorstep_pipeline.stages import simulate as stage

    manifest = stage.run(paths())
    typer.echo(f"simulate: {manifest.counts()}")


@app.command()
def recovery(
    seeds: int = typer.Option(20, help="seeds per condition"),
    workers: int = typer.Option(2, help="worker processes"),
    no_cache: bool = typer.Option(False, help="run every seed again; the rederive passes this"),
) -> None:
    """Every estimator graded on simulated countries with known truth, every condition and seed."""
    from doorstep_pipeline.stages import recovery as stage

    manifest = stage.run(paths(), seeds=seeds, workers=workers, use_cache=not no_cache)
    typer.echo(f"recovery: {manifest.counts()}")


@app.command()
def warehouse() -> None:
    """dbt build and test over the derived parquet, then the shipped marts."""
    from doorstep_pipeline.stages import warehouse as stage

    manifest = stage.run(paths())
    typer.echo(f"warehouse: {manifest.counts()}")


@app.command()
def metrics() -> None:
    """The metric layer reconciled across four grains."""
    from doorstep_pipeline.stages import metrics as stage

    manifest = stage.run(paths())
    typer.echo(f"metrics: {manifest.counts()}")


@app.command()
def chapters(
    replicates: int = typer.Option(0, help="bootstrap replicates; 0 means the policy's"),
    draws: int = typer.Option(0, help="Monte Carlo draws over the census margins; 0 means the policy's"),
) -> None:
    """The eight chapters: plans registered first, then every estimate, its chart, its marts and the calculator marts."""
    from doorstep_pipeline.stages import chapters as stage

    manifest = stage.run(paths(), replicates=replicates or None, draws=draws or None)
    typer.echo(f"chapters: {manifest.counts()}")


@app.command()
def manifest() -> None:
    """Merge every stage's partial manifest into results/manifest.json."""
    from doorstep_pipeline.stages import assemble

    merged = assemble.run(paths())
    typer.echo(f"manifest: {merged.counts()}")


@app.command()
def marts() -> None:
    """The data the site reads, under web/public/data."""
    from doorstep_pipeline.stages import web

    typer.echo(f"marts: {web.run(paths())}")


@app.command()
def exports() -> None:
    """The workbook with live formulas, the BI extracts and specifications, the CSV bundle."""
    from doorstep_pipeline.stages import exports as stage

    manifest = stage.run(paths())
    typer.echo(f"exports: {manifest.counts()}")
