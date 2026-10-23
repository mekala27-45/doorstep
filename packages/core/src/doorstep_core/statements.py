"""The statement that appears on every surface.

Written once here. The story, the memo, every page of the site, every API response
and every rendered document read it from this module, and a gate checks each surface.
"""

from __future__ import annotations

PROJECT = "doorstep"

STATEMENT = (
    "Public data from the Federal Housing Finance Agency, the Census Bureau (American Community Survey, "
    "Building Permits Survey, Population Estimates), the Department of Housing and Urban Development and "
    "the Consumer Financial Protection Bureau (HMDA), with mortgage rates from Freddie Mac under its terms "
    "of use. Metros are real and appear as they do in the public record; no household, borrower or address "
    "appears. The findings are a portfolio analysis, not financial advice, not a market forecast and not a "
    "fair lending finding."
)

RATE_ATTRIBUTION = "Mortgage rates: Freddie Mac Primary Mortgage Market Survey, used under its terms of use."


def statement_markdown() -> str:
    """The statement as a Markdown block quote, for documents."""
    return f"> {STATEMENT}"


def statement_payload() -> dict[str, str]:
    """The statement as a JSON-ready mapping, for API response bodies."""
    return {"statement": STATEMENT}


def contains_statement(text: str) -> bool:
    """True when the statement appears verbatim, allowing for line wrapping."""
    flat = " ".join(text.split())
    return " ".join(STATEMENT.split()) in flat
