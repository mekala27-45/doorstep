"""The affordability arithmetic the API serves, over the committed calculator marts.

A check takes a metro, an annual income, a down payment share, a rate and a horizon and answers with the
payment on the median home and its share of the income, the price the income can carry at the thirty
percent line, the share of households in that metro whose income clears the payment on the median home,
and the rent or buy breakeven horizon with the interval the metro's own history gives it. The carry
forward expectation is the payment share next quarter if prices and rates do not move; when the next
quarter publishes, the scorer compares it with the payment share the published price and rate produce
for the same inputs.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
from doorstep_core.config import POLICY, Policy
from doorstep_finance.brackets import share_above
from doorstep_finance.breakeven import CostModel, breakeven, breakeven_years_vectorised
from doorstep_finance.mortgage import affordable_price, income_needed, payment_on_price

FILES = ("calc_metros.parquet", "calc_quarters.parquet")
BLOCK_YEARS = 3
PATHS = 200


class UnknownMetro(KeyError):
    pass


class UnknownQuarter(KeyError):
    pass


@dataclass(frozen=True)
class Answer:
    cbsa_code: str
    cbsa_title: str
    quarter: str
    income: int
    down_share: float
    rate: float
    horizon_years: int
    median_home: float
    payment: float
    payment_share: float
    affordable_price: float
    affordable_share: float | None
    households_can_afford: float | None
    breakeven_years: float | None
    breakeven_low: float | None
    breakeven_high: float | None
    never_share: float | None
    median_income: float
    income_year: int
    expected_next_payment_share: float

    def payload(self) -> dict[str, Any]:
        return {
            "cbsa_code": self.cbsa_code,
            "cbsa_title": self.cbsa_title,
            "quarter": self.quarter,
            "income": self.income,
            "down_share": self.down_share,
            "rate": self.rate,
            "horizon_years": self.horizon_years,
            "median_home": round(self.median_home, 2),
            "payment": round(self.payment, 2),
            "payment_share": self.payment_share,
            "affordable_price": round(self.affordable_price, 2),
            "affordable_share": self.affordable_share,
            "households_can_afford": self.households_can_afford,
            "breakeven_years": self.breakeven_years,
            "breakeven_low": self.breakeven_low,
            "breakeven_high": self.breakeven_high,
            "never_share": self.never_share,
            "median_income": self.median_income,
            "income_year": self.income_year,
            "expected_next_payment_share": self.expected_next_payment_share,
        }


def _rng(seed: int, label: str) -> np.random.Generator:
    stream = int.from_bytes(hashlib.sha256(label.encode()).digest()[:4], "little")
    return np.random.default_rng(np.random.SeedSequence([seed, stream]))


def _paths(history: np.ndarray, horizon: int, draws: int, seed: int, label: str) -> np.ndarray:
    g = _rng(seed, label)
    n = history.shape[0]
    blocks_needed = int(np.ceil(horizon / BLOCK_YEARS))
    starts = g.integers(0, max(n - BLOCK_YEARS + 1, 1), size=(draws, blocks_needed))
    idx = (starts[:, :, None] + np.arange(BLOCK_YEARS)[None, None, :]).reshape(draws, -1)[:, :horizon]
    return np.asarray(history[np.minimum(idx, n - 1)], dtype=np.float64)


class Calculator:
    """The committed marts, loaded once, with a version that is the digest of their bytes."""

    def __init__(self, marts: Path, policy: Policy = POLICY) -> None:
        self.policy = policy
        self.version = "none"
        self.metros: pl.DataFrame | None = None
        self.quarters: pl.DataFrame | None = None
        self.meta: dict[str, Any] = {}
        paths = [marts / f for f in FILES]
        if not all(p.exists() for p in paths):
            return
        digest = hashlib.sha256()
        for p in paths:
            digest.update(p.read_bytes())
        self.version = f"marts-{digest.hexdigest()[:10]}"
        self.metros = pl.read_parquet(paths[0])
        self.quarters = pl.read_parquet(paths[1])
        meta_path = marts / "calc_meta.json"
        self.meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        self._by_code = {str(r["cbsa_code"]): r for r in self.metros.iter_rows(named=True)}
        self._quarter_index: dict[str, dict[str, tuple[float, float]]] = {}
        for r in self.quarters.iter_rows(named=True):
            self._quarter_index.setdefault(str(r["cbsa_code"]), {})[str(r["period"])] = (
                float(r["value_anchored"]),
                float(r["rate"]),
            )

    @property
    def ready(self) -> bool:
        return self.metros is not None

    @property
    def rate_default(self) -> float:
        return float(self.meta.get("rate_default", 6.5))

    @property
    def latest_period(self) -> str:
        return str(self.meta.get("latest_period", ""))

    def metro(self, code: str) -> dict[str, Any]:
        try:
            return self._by_code[code]
        except (AttributeError, KeyError) as exc:
            raise UnknownMetro(f"no metro with code {code}") from exc

    def quarters_of(self, code: str) -> list[str]:
        return sorted(self._quarter_index.get(code, {}))

    def next_quarter(self, code: str, quarter: str) -> str | None:
        qs = self.quarters_of(code)
        if quarter not in qs:
            return None
        i = qs.index(quarter)
        return qs[i + 1] if i + 1 < len(qs) else None

    def value_and_rate(self, code: str, quarter: str) -> tuple[float, float]:
        try:
            return self._quarter_index[code][quarter]
        except KeyError as exc:
            raise UnknownQuarter(f"no prices for {code} in {quarter}") from exc

    def largest(self, n: int) -> list[str]:
        assert self.metros is not None
        return [
            str(c) for c in self.metros.sort("households", descending=True).head(n)["cbsa_code"].to_list()
        ]

    def check(
        self,
        code: str,
        income: float,
        down_share: float,
        rate: float | None,
        horizon_years: int,
        *,
        quarter: str | None = None,
        paths: int = PATHS,
    ) -> Answer:
        m = self.metro(code)
        q = quarter or str(m["latest_period"])
        median_home, q_rate = self.value_and_rate(code, q)
        the_rate = float(rate) if rate is not None else (self.rate_default if quarter is None else q_rate)
        income_rounded = int(round(float(income) / 1000.0) * 1000)
        if income_rounded <= 0:
            raise ValueError("income must be at least five hundred dollars")
        policy = self.policy
        pay = payment_on_price(median_home, the_rate, down_share, policy.loan_term_years)
        share = 12.0 * pay / income_rounded
        aff_price = affordable_price(
            income_rounded, the_rate, down_share, policy.loan_term_years, policy.affordable_line
        )
        brackets = m["brackets"]
        aff_share: float | None = None
        can_afford: float | None = None
        if brackets is not None and sum(brackets) > 0:
            needed = income_needed(
                median_home, the_rate, down_share, policy.loan_term_years, policy.affordable_line
            )
            aff_share = share_above(needed, list(brackets))
            can_afford = aff_share * float(m["households"]) if m["households"] else None
        be_years = be_low = be_high = never = None
        app, rg = m["appreciation"], m["rent_growth"]
        if app is not None and rg is not None and len(app) >= 3 and len(rg) >= 3:
            a = _paths(np.asarray(app, dtype=np.float64), horizon_years, paths, policy.seed, f"{code}-app")
            r = _paths(np.asarray(rg, dtype=np.float64), horizon_years, paths, policy.seed, f"{code}-rent")
            years: np.ndarray = np.array(
                breakeven_years_vectorised(
                    median_home,
                    float(m["median_rent"]) * 12.0,
                    the_rate,
                    down_share,
                    policy.loan_term_years,
                    a,
                    r,
                    CostModel.from_mapping(policy.breakeven_cost_model),
                )
            )
            alpha = (1.0 - policy.interval_level) / 2.0
            be_years, be_low, be_high = (
                float(np.median(years)),
                float(np.quantile(years, alpha)),
                float(np.quantile(years, 1.0 - alpha)),
            )
            never = float(np.mean(years > horizon_years))
        return Answer(
            cbsa_code=code,
            cbsa_title=str(m["cbsa_title"]),
            quarter=q,
            income=income_rounded,
            down_share=down_share,
            rate=the_rate,
            horizon_years=horizon_years,
            median_home=median_home,
            payment=pay,
            payment_share=share,
            affordable_price=aff_price,
            affordable_share=aff_share,
            households_can_afford=can_afford,
            breakeven_years=be_years,
            breakeven_low=be_low,
            breakeven_high=be_high,
            never_share=never,
            median_income=float(m["median_income"]),
            income_year=int(m["income_year"]),
            expected_next_payment_share=share,
        )

    def realized(
        self, code: str, quarter: str, income: int, down_share: float, rate_was: float, median_home_was: float
    ) -> dict[str, float] | None:
        """The payment share the next quarter's published price and rate give the same inputs, or None when
        the next quarter has not published."""
        nxt = self.next_quarter(code, quarter)
        if nxt is None:
            return None
        value, rate = self.value_and_rate(code, nxt)
        pay = payment_on_price(value, rate, down_share, self.policy.loan_term_years)
        return {
            "quarter": nxt,  # type: ignore[dict-item]
            "payment_share": 12.0 * pay / income,
            "price_moved": value / median_home_was - 1.0,
            "rate_moved": rate - rate_was,
        }

    def curve(
        self, code: str, income: float, down_share: float, rate: float | None, horizon_years: int
    ) -> list[dict[str, float]]:
        """The rent or buy curve under the metro's median appreciation and rent growth, year by year."""
        m = self.metro(code)
        median_home, _ = self.value_and_rate(code, str(m["latest_period"]))
        the_rate = float(rate) if rate is not None else self.rate_default
        app = float(np.median(m["appreciation"])) if m["appreciation"] else 0.03
        rg = float(np.median(m["rent_growth"])) if m["rent_growth"] else 0.03
        result = breakeven(
            median_home,
            float(m["median_rent"]) * 12.0,
            the_rate,
            down_share,
            self.policy.loan_term_years,
            horizon_years,
            app,
            rg,
            CostModel.from_mapping(self.policy.breakeven_cost_model),
        )
        return [
            {
                "year": float(y.year),
                "difference": y.difference,
                "owner_equity": y.owner_equity,
                "renter_wealth": y.renter_wealth,
                "home_value": y.home_value,
            }
            for y in result.years
        ]
