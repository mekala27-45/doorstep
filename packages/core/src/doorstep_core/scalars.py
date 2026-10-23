"""Scalars out of a frame, typed. Polars hands a cell back as a wide union of everything a cell can hold;
these narrow it at the point of use and refuse a null, so a missing value stops a stage instead of
becoming a NaN that reaches a document."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any


class ScalarError(ValueError):
    pass


def num(value: Any, *, what: str = "value") -> float:
    """A float out of a cell; None is refused."""
    if value is None:
        raise ScalarError(f"{what} is null where a number was needed")
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float | Decimal):
        return float(value)
    if isinstance(value, str):
        return float(value)
    if hasattr(value, "item"):
        return float(value.item())
    raise ScalarError(f"{what} is a {type(value).__name__}, not a number")


def integer(value: Any, *, what: str = "value") -> int:
    """An int out of a cell; a whole float is accepted, a fraction and a null are refused."""
    if value is None:
        raise ScalarError(f"{what} is null where an integer was needed")
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float | Decimal):
        if float(value) != int(value):
            raise ScalarError(f"{what} is {value}, not a whole number")
        return int(value)
    if isinstance(value, str):
        return int(value)
    if hasattr(value, "item"):
        return integer(value.item(), what=what)
    raise ScalarError(f"{what} is a {type(value).__name__}, not an integer")


def num_or_none(value: Any) -> float | None:
    """A float out of a cell, or None when the cell is null (for columns a document prints as not available)."""
    if value is None:
        return None
    if isinstance(value, dt.date | dt.time | dt.timedelta | bytes):
        raise ScalarError(f"{type(value).__name__} is not a number")
    return num(value)
