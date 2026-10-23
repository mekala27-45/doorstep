"""The arithmetic of affordability: payments, shares, the affordable price, brackets, the breakeven."""

from doorstep_finance.brackets import decile_incomes, median_from_brackets, share_above
from doorstep_finance.breakeven import Breakeven, CostModel, breakeven, breakeven_year
from doorstep_finance.mortgage import (
    FinanceError,
    affordable_price,
    balance_after,
    down_payment_years,
    income_needed,
    payment,
    payment_on_price,
    payment_share,
    principal_for_payment,
    schedule,
)

__all__ = [
    "Breakeven",
    "CostModel",
    "FinanceError",
    "affordable_price",
    "balance_after",
    "breakeven",
    "breakeven_year",
    "decile_incomes",
    "down_payment_years",
    "income_needed",
    "median_from_brackets",
    "payment",
    "payment_on_price",
    "payment_share",
    "principal_for_payment",
    "schedule",
    "share_above",
]
