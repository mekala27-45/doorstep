"""Rent or buy: the horizon at which owning overtakes renting, under a stated cost model.

Two households start with the same cash: the down payment plus the buyer's closing costs. One buys
the home; the other rents the same home and invests that cash and, every year, the difference
between what the owner pays out (payment, taxes, insurance, maintenance, mortgage insurance) and the
rent. At each horizon the owner's position is the home's value less the balance and the selling
costs; the renter's is the invested cash. The breakeven is the first year the owner is ahead. The
appreciation and rent growth paths are inputs, so the chapter can draw them from a metro's own
history by block bootstrap and publish an interval, and the simulator can hand in a known path and
ask the engine to recover a known breakeven.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from doorstep_finance.mortgage import FinanceError, balance_after, payment


@dataclass(frozen=True)
class CostModel:
    buy_closing_share: float = 0.03
    sell_closing_share: float = 0.06
    property_tax_share: float = 0.011
    insurance_share: float = 0.004
    maintenance_share: float = 0.01
    pmi_rate_under_20: float = 0.006
    investment_return: float = 0.045

    @classmethod
    def from_mapping(cls, values: dict[str, float]) -> CostModel:
        known = {k: v for k, v in values.items() if k in cls.__dataclass_fields__}
        return cls(**known)


@dataclass(frozen=True)
class YearPosition:
    year: int
    home_value: float
    balance: float
    owner_equity: float
    owner_outlay_cumulative: float
    rent_cumulative: float
    renter_wealth: float
    difference: float
    """renter_wealth minus owner_equity: positive means renting is ahead at this horizon."""


@dataclass(frozen=True)
class Breakeven:
    years: list[YearPosition]
    breakeven_year: int | None

    @property
    def horizon(self) -> int:
        return len(self.years)


def _path(value: float | Sequence[float], horizon: int, name: str) -> list[float]:
    if isinstance(value, int | float):
        return [float(value)] * horizon
    values = [float(v) for v in value]
    if len(values) < horizon:
        raise FinanceError(f"the {name} path has {len(values)} years but the horizon is {horizon}")
    return values[:horizon]


def breakeven(
    price: float,
    annual_rent: float,
    annual_rate_pct: float,
    down_share: float,
    term_years: int,
    horizon_years: int,
    appreciation: float | Sequence[float],
    rent_growth: float | Sequence[float],
    cost: CostModel,
) -> Breakeven:
    if price <= 0 or annual_rent <= 0:
        raise FinanceError("price and rent must be positive")
    if horizon_years <= 0:
        raise FinanceError("the horizon must be at least one year")
    if not 0.0 <= down_share < 1.0:
        raise FinanceError("the down payment share must be in [0, 1)")
    app = _path(appreciation, horizon_years, "appreciation")
    rg = _path(rent_growth, horizon_years, "rent growth")
    loan = price * (1.0 - down_share)
    monthly = payment(loan, annual_rate_pct, term_years)
    cash_at_start = price * down_share + price * cost.buy_closing_share
    renter_wealth = cash_at_start
    value = price
    rent = annual_rent
    owner_outlay = cash_at_start
    rent_total = 0.0
    rows: list[YearPosition] = []
    hit: int | None = None
    for year in range(1, horizon_years + 1):
        value *= 1.0 + app[year - 1]
        if year > 1:
            rent *= 1.0 + rg[year - 2]
        months = min(year * 12, term_years * 12)
        balance = balance_after(loan, annual_rate_pct, term_years, months)
        paid_this_year = monthly * 12.0 if year * 12 <= term_years * 12 else 0.0
        ltv = balance / value if value > 0 else 0.0
        pmi = cost.pmi_rate_under_20 * balance if down_share < 0.20 and ltv > 0.80 else 0.0
        carrying = value * (cost.property_tax_share + cost.insurance_share + cost.maintenance_share)
        outlay = paid_this_year + carrying + pmi
        owner_outlay += outlay
        rent_total += rent
        # The renter invests what the owner paid out beyond the rent, or draws it down when the rent is higher.
        renter_wealth = renter_wealth * (1.0 + cost.investment_return) + (outlay - rent)
        equity = value - balance - value * cost.sell_closing_share
        difference = renter_wealth - equity
        rows.append(
            YearPosition(year, value, balance, equity, owner_outlay, rent_total, renter_wealth, difference)
        )
        if hit is None and difference <= 0.0:
            hit = year
    return Breakeven(rows, hit)


def breakeven_year(result: Breakeven, horizon_years: int) -> float:
    """The breakeven as a number for intervals: the year, or one past the horizon when owning never catches up."""
    return float(result.breakeven_year) if result.breakeven_year is not None else float(horizon_years + 1)
