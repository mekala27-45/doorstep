"""The arithmetic every chapter and the calculator share: the payment on a loan, the share of income
it takes, the price a payment can carry, and the schedule behind it. Every function here is tested
against a closed form or a hand computed case to the cent, because a figure that goes to a reader as
a dollar amount has to survive someone checking it on a bank's own calculator.

Rates are annual percentages (6.5 means six and a half percent), as Freddie Mac publishes them.
Prices, payments and incomes are dollars. Shares are fractions of one.
"""

from __future__ import annotations

from dataclasses import dataclass


class FinanceError(ValueError):
    pass


def monthly_rate(annual_rate_pct: float) -> float:
    if annual_rate_pct < 0 or annual_rate_pct > 30:
        raise FinanceError(
            f"a mortgage rate of {annual_rate_pct} percent is outside the range this build accepts"
        )
    return annual_rate_pct / 100.0 / 12.0


def payment(principal: float, annual_rate_pct: float, term_years: int) -> float:
    """The level monthly payment of principal and interest on a fully amortising fixed rate loan."""
    if principal < 0:
        raise FinanceError("principal cannot be negative")
    if term_years <= 0:
        raise FinanceError("the term must be at least one year")
    n = term_years * 12
    r = monthly_rate(annual_rate_pct)
    if r == 0.0:
        return principal / n
    factor = (1.0 + r) ** n
    return principal * r * factor / (factor - 1.0)


def principal_for_payment(monthly_payment: float, annual_rate_pct: float, term_years: int) -> float:
    """The inverse of ``payment``: the loan a monthly payment carries."""
    if monthly_payment < 0:
        raise FinanceError("a payment cannot be negative")
    n = term_years * 12
    r = monthly_rate(annual_rate_pct)
    if r == 0.0:
        return monthly_payment * n
    factor = (1.0 + r) ** n
    return monthly_payment * (factor - 1.0) / (r * factor)


def payment_on_price(price: float, annual_rate_pct: float, down_share: float, term_years: int) -> float:
    """Principal and interest on a home at a price with a down payment share. Taxes and insurance are
    workbook inputs, not part of the headline, and the definitions document says so."""
    if not 0.0 <= down_share < 1.0:
        raise FinanceError("the down payment share must be in [0, 1)")
    return payment(price * (1.0 - down_share), annual_rate_pct, term_years)


def payment_share(
    price: float, income: float, annual_rate_pct: float, down_share: float, term_years: int
) -> float:
    """Twelve payments over annual household income."""
    if income <= 0:
        raise FinanceError("income must be positive")
    return 12.0 * payment_on_price(price, annual_rate_pct, down_share, term_years) / income


def affordable_price(
    income: float, annual_rate_pct: float, down_share: float, term_years: int, line: float
) -> float:
    """The price whose payment takes exactly ``line`` of income: the inverse of ``payment_share``."""
    if income <= 0:
        raise FinanceError("income must be positive")
    if not 0.0 < line < 1.0:
        raise FinanceError("the affordable line is a share of income in (0, 1)")
    monthly = line * income / 12.0
    loan = principal_for_payment(monthly, annual_rate_pct, term_years)
    return loan / (1.0 - down_share)


def income_needed(
    price: float, annual_rate_pct: float, down_share: float, term_years: int, line: float
) -> float:
    """The annual income at which the payment on a price sits exactly on the line."""
    if not 0.0 < line < 1.0:
        raise FinanceError("the affordable line is a share of income in (0, 1)")
    return 12.0 * payment_on_price(price, annual_rate_pct, down_share, term_years) / line


@dataclass(frozen=True)
class ScheduleRow:
    month: int
    payment: float
    interest: float
    principal: float
    balance: float


def schedule(principal: float, annual_rate_pct: float, term_years: int) -> list[ScheduleRow]:
    """The amortisation schedule, month by month; the last balance is zero to the cent."""
    n = term_years * 12
    r = monthly_rate(annual_rate_pct)
    pay = payment(principal, annual_rate_pct, term_years)
    rows: list[ScheduleRow] = []
    balance = principal
    for month in range(1, n + 1):
        interest = balance * r
        paid_down = pay - interest
        if month == n:
            paid_down = balance
            pay_this = interest + paid_down
        else:
            pay_this = pay
        balance = balance - paid_down
        rows.append(ScheduleRow(month, pay_this, interest, paid_down, max(balance, 0.0)))
    return rows


def balance_after(principal: float, annual_rate_pct: float, term_years: int, months: int) -> float:
    """The balance after a number of payments, in closed form."""
    n = term_years * 12
    if months < 0 or months > n:
        raise FinanceError("months must lie within the term")
    r = monthly_rate(annual_rate_pct)
    if r == 0.0:
        return principal * (1.0 - months / n)
    pay = payment(principal, annual_rate_pct, term_years)
    growth = (1.0 + r) ** months
    return principal * growth - pay * (growth - 1.0) / r


def down_payment_years(price: float, down_share: float, income: float, saving_rate: float) -> float:
    """Years to save the down payment at a stated share of income saved each year, no return assumed.
    The reader's question is simple, so the arithmetic stays simple and the pushback names what it leaves out."""
    if income <= 0 or saving_rate <= 0:
        raise FinanceError("income and the saving rate must be positive")
    return price * down_share / (income * saving_rate)
