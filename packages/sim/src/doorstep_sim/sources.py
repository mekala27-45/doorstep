"""A simulated world written in the shape of the real sources.

The warehouse reads parquet under data/derived and data/hmda in the contracts' schemas. Writing a
simulated world into those same files lets the whole warehouse, the metric layer and every chapter run
on data with known truth, which is how the SQL is tested without a live source and how the HMDA scale
test generates the full row count of the real extract before the real files are joined. Each simulated
metro is one county in one state; the delineation file, the gazetteer and the population file follow.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
from doorstep_contracts import geography
from doorstep_core.config import INCOME_BRACKETS
from doorstep_core.scalars import num
from doorstep_core.seeds import rng
from doorstep_finance.brackets import lognormal_bracket_counts

from doorstep_sim.metros import World


def _county(i: int) -> str:
    return f"{90 + (i % 9):02d}{(i // 9) + 1:03d}"


def _acs_rows(w: World) -> pl.DataFrame:
    rows: list[dict[str, object]] = []

    def put(
        year: int,
        code: str,
        name: str,
        table: str,
        var: str,
        est: float | None,
        moe: float | None,
        national: bool = False,
    ) -> None:
        rows.append(
            {
                "year": year,
                "cbsa_code": code,
                "name": name,
                "table": table,
                "variable": var,
                "estimate": est,
                "moe": moe,
                "source": "census",
                "is_national": national,
                "q_jam_value": False,
                "q_moe_exceeds_estimate": False,
                "q_negative_moe": False,
                "quarantined": False,
            }
        )

    my = w.metro_year
    brackets = w.brackets
    for r in my.iter_rows(named=True):
        if r["year"] == 2020:
            continue
        y, code, name = int(r["year"]), str(r["metro_id"]), str(r["metro_name"])
        hh = float(r["households"])
        owners = float(r["owner_households"])
        renters = float(r["renter_households"])
        put(y, code, name, "B11001", "B11001_001", hh, hh * 0.01)
        put(y, code, name, "B25003", "B25003_001", hh, hh * 0.01)
        put(y, code, name, "B25003", "B25003_002", owners, owners * 0.015)
        put(y, code, name, "B25003", "B25003_003", renters, renters * 0.02)
        put(y, code, name, "B19013", "B19013_001", r["median_income"], r["median_income_moe"])
        put(y, code, name, "B25077", "B25077_001", r["median_value_reported"], r["median_value_moe"])
        put(y, code, name, "B25064", "B25064_001", r["median_rent"], float(r["median_rent"]) * 0.02)
        put(
            y,
            code,
            name,
            "B25071",
            "B25071_001",
            100.0 * 12.0 * float(r["median_rent"]) / float(r["renter_median_income"]),
            0.5,
        )
        put(y, code, name, "B25119", "B25119_001", r["median_income"], r["median_income_moe"])
        put(y, code, name, "B25119", "B25119_002", float(r["median_income"]) * 1.3, r["median_income_moe"])
        put(y, code, name, "B25119", "B25119_003", r["renter_median_income"], r["median_income_moe"])
        put(y, code, name, "B25001", "B25001_001", hh * 1.08, hh * 0.01)
        put(y, code, name, "B25002", "B25002_003", hh * 0.08, hh * 0.005)
        put(y, code, name, "B25004", "B25004_002", hh * 0.02, hh * 0.002)
        put(y, code, name, "B25004", "B25004_004", hh * 0.01, hh * 0.001)
        put(y, code, name, "B25004", "B25004_006", hh * 0.03, hh * 0.002)
        # renter burden bands: total, 30 to 34.9, 35 to 39.9, 40 to 49.9, 50 plus, not computed
        burdened = float(r["rent_burdened_share"]) * renters
        severe = float(r["rent_severe_share"]) * renters
        mid = max(burdened - severe, 0.0)
        put(y, code, name, "B25070", "B25070_001", renters, renters * 0.02)
        put(y, code, name, "B25070", "B25070_007", mid * 0.4, mid * 0.05)
        put(y, code, name, "B25070", "B25070_008", mid * 0.3, mid * 0.05)
        put(y, code, name, "B25070", "B25070_009", mid * 0.3, mid * 0.05)
        put(y, code, name, "B25070", "B25070_010", severe, severe * 0.05)
        put(y, code, name, "B25070", "B25070_011", 0.0, 0.0)
        with_m = owners * 0.6
        put(y, code, name, "B25091", "B25091_002", with_m, with_m * 0.02)
        put(y, code, name, "B25091", "B25091_008", with_m * 0.08, with_m * 0.01)
        put(y, code, name, "B25091", "B25091_009", with_m * 0.05, with_m * 0.01)
        put(y, code, name, "B25091", "B25091_010", with_m * 0.06, with_m * 0.01)
        put(y, code, name, "B25091", "B25091_011", with_m * 0.09, with_m * 0.01)
        put(y, code, name, "B25091", "B25091_012", 0.0, 0.0)
        put(y, code, name, "B25091", "B25091_013", owners - with_m, owners * 0.02)
        put(y, code, name, "B25007", "B25007_003", owners * 0.01, owners * 0.002)
        put(y, code, name, "B25007", "B25007_004", owners * 0.08, owners * 0.005)
        put(y, code, name, "B25007", "B25007_012", renters, renters * 0.02)
        put(y, code, name, "B25007", "B25007_013", renters * 0.07, renters * 0.005)
        put(y, code, name, "B25007", "B25007_014", renters * 0.25, renters * 0.01)
        put(y, code, name, "B25024", "B25024_002", hh * 0.6, hh * 0.01)
        for k in (6, 7, 8, 9):
            put(y, code, name, "B25024", f"B25024_{k:03d}", hh * 0.05, hh * 0.005)
        put(y, code, name, "B25103", "B25103_002", float(r["median_value_true"]) * 0.011, 50.0)
        # income brackets, with the suppressed cells as nulls
        b = brackets.filter((pl.col("metro_id") == code) & (pl.col("year") == y)).sort("bracket")
        put(y, code, name, "B19001", "B19001_001", hh, hh * 0.01)
        for br in b.iter_rows(named=True):
            put(
                y,
                code,
                name,
                "B19001",
                f"B19001_{int(br['bracket']) + 2:03d}",
                br["households"],
                None if br["households"] is None else float(br["households"]) * 0.1,
            )
        # burden by income group: seven groups, spread by the renter income distribution, in the layout the
        # census used that year (seven cells per group with five rent bands through 2014, nine from 2015)
        shares = (0.08, 0.17, 0.22, 0.17, 0.18, 0.09, 0.09)
        burden_by_group = (0.95, 0.85, 0.6, 0.35, 0.15, 0.05, 0.02)
        severe_by_group = (0.75, 0.5, 0.25, 0.08, 0.02, 0.0, 0.0)
        per_group = 7 if y <= 2014 else 9
        for g, (share, bg, sg) in enumerate(zip(shares, burden_by_group, severe_by_group, strict=True)):
            start = 2 + g * per_group
            total = renters * share
            put(y, code, name, "B25074", f"B25074_{start:03d}", total, total * 0.05)
            if per_group == 9:
                put(y, code, name, "B25074", f"B25074_{start + 4:03d}", total * (bg - sg) * 0.4, None)
                put(y, code, name, "B25074", f"B25074_{start + 5:03d}", total * (bg - sg) * 0.3, None)
                put(y, code, name, "B25074", f"B25074_{start + 6:03d}", total * (bg - sg) * 0.3, None)
                put(y, code, name, "B25074", f"B25074_{start + 7:03d}", total * sg, None)
                put(y, code, name, "B25074", f"B25074_{start + 8:03d}", 0.0, None)
            else:
                put(y, code, name, "B25074", f"B25074_{start + 4:03d}", total * bg * 0.4, None)
                put(y, code, name, "B25074", f"B25074_{start + 5:03d}", total * bg * 0.6, None)
                put(y, code, name, "B25074", f"B25074_{start + 6:03d}", 0.0, None)
    # national rows: the household weighted sums and medians
    for y in sorted(set(my["year"].to_list())):
        if y == 2020:
            continue
        sub = my.filter(pl.col("year") == y)
        hh = float(sub["households"].sum())
        put(y, "US", "United States", "B11001", "B11001_001", hh, hh * 0.002, True)
        put(
            y,
            "US",
            "United States",
            "B25003",
            "B25003_002",
            float(sub["owner_households"].sum()),
            hh * 0.002,
            True,
        )
        put(
            y,
            "US",
            "United States",
            "B25003",
            "B25003_003",
            float(sub["renter_households"].sum()),
            hh * 0.002,
            True,
        )
        put(
            y,
            "US",
            "United States",
            "B19013",
            "B19013_001",
            num(sub["median_income"].median()),
            300.0,
            True,
        )
        put(
            y,
            "US",
            "United States",
            "B25077",
            "B25077_001",
            num(sub["median_value_reported"].median()),
            800.0,
            True,
        )
        put(y, "US", "United States", "B25064", "B25064_001", num(sub["median_rent"].median()), 5.0, True)
        put(
            y,
            "US",
            "United States",
            "B25119",
            "B25119_003",
            num(sub["renter_median_income"].median()),
            300.0,
            True,
        )
        put(
            y,
            "US",
            "United States",
            "B25119",
            "B25119_002",
            num(sub["median_income"].median()) * 1.3,
            300.0,
            True,
        )
        renters = float(sub["renter_households"].sum())
        burdened = float((sub["rent_burdened_share"] * sub["renter_households"]).sum())
        severe = float((sub["rent_severe_share"] * sub["renter_households"]).sum())
        put(y, "US", "United States", "B25070", "B25070_001", renters, renters * 0.002, True)
        put(y, "US", "United States", "B25070", "B25070_007", (burdened - severe) * 0.4, None, True)
        put(y, "US", "United States", "B25070", "B25070_008", (burdened - severe) * 0.3, None, True)
        put(y, "US", "United States", "B25070", "B25070_009", (burdened - severe) * 0.3, None, True)
        put(y, "US", "United States", "B25070", "B25070_010", severe, None, True)
        put(y, "US", "United States", "B25070", "B25070_011", 0.0, None, True)
    return pl.DataFrame(rows, schema_overrides={"estimate": pl.Float64, "moe": pl.Float64})


def _loan_rows(w: World, *, scale: float = 1.0) -> pl.DataFrame:
    """Loan level rows per year with the counts the simulated world implies, at a stated scale."""
    g = rng(w.seed, "loans", w.condition.name)
    frames: list[pl.DataFrame] = []
    income_by = {
        (r["metro_id"], r["year"]): (float(r["median_income"]), float(r["median_value_true"]))
        for r in w.metro_year.iter_rows(named=True)
    }
    for r in w.loans_year.iter_rows(named=True):
        year = int(r["year"])
        if year < 2018:
            continue
        code = str(r["metro_id"])
        idx = int(code[1:]) - 1
        county = _county(idx)
        n_p = int(round(float(r["purchase_loans"]) * scale))
        n_r = int(round(float(r["refinance_loans"]) * scale))
        n = n_p + n_r
        if n == 0:
            continue
        med_income, med_value = income_by[(code, year)]
        rate = float(r["rate_at_origination"])
        ratio = float(r["borrower_income_ratio"])
        income = np.round(med_income * ratio * np.exp(g.normal(0.0, 0.45, n)) / 1000.0) * 1000.0
        value = np.round(med_value * np.exp(g.normal(0.05, 0.35, n)) / 5000.0) * 5000.0 + 5000.0
        amount = np.round(value * np.clip(g.normal(0.85, 0.1, n), 0.3, 0.98) / 5000.0) * 5000.0 + 5000.0
        purpose = np.array([1] * n_p + [31] * int(n_r * 0.6) + [32] * (n_r - int(n_r * 0.6)))
        rates = np.round(rate + g.normal(0.0, 0.3, n), 3)
        ages = g.choice(
            ["<25", "25-34", "35-44", "45-54", "55-64", "65-74", ">74"],
            size=n,
            p=[0.04, 0.3, 0.26, 0.18, 0.12, 0.07, 0.03],
        )
        frames.append(
            pl.DataFrame(
                {
                    "year": np.full(n, year, dtype=np.int64),
                    "lei": [f"SIMLEI{(i % 40):03d}" for i in range(n)],
                    "msa_md": [code] * n,
                    "state_code": [county[:2]] * n,
                    "county_fips": [county] * n,
                    "loan_purpose": purpose.astype(np.int64),
                    "lien_status": np.ones(n, dtype=np.int64),
                    "loan_amount": amount,
                    "property_value": value,
                    "income": income,
                    "interest_rate": rates,
                    "rate_spread": np.round(g.normal(0.3, 0.4, n), 3),
                    "loan_term": np.where(g.random(n) < 0.9, 360, 180).astype(np.int64),
                    "ltv": np.round(100.0 * amount / value, 2),
                    "dti_band": ["36%-<40%"] * n,
                    "applicant_age": ages,
                    "total_units": np.ones(n, dtype=np.int64),
                    "occupancy_type": np.where(g.random(n) < 0.95, 1, 2).astype(np.int64),
                    "reverse_mortgage": np.full(n, 2, dtype=np.int64),
                    "open_end": np.full(n, 2, dtype=np.int64),
                    "business_purpose": np.full(n, 2, dtype=np.int64),
                    "msa_md_median_family_income": np.full(n, med_income * 1.2),
                }
            )
        )
    frame = pl.concat(frames)
    frame = frame.with_columns(
        pl.col("income").is_null().alias("q_income_exempt_or_missing"),
        pl.col("interest_rate").is_null().alias("q_rate_missing"),
        (pl.col("loan_term") != 360).alias("q_term_not_30_years"),
        pl.lit(False).alias("q_metro_unresolved"),
        (pl.col("occupancy_type") != 1).alias("q_not_principal_residence"),
        pl.lit(False).alias("q_reverse_open_or_business"),
        (pl.col("property_value") < pl.col("loan_amount")).alias("q_value_below_loan"),
    ).with_columns(
        pl.any_horizontal(
            [
                pl.col(c)
                for c in [
                    "q_income_exempt_or_missing",
                    "q_rate_missing",
                    "q_term_not_30_years",
                    "q_not_principal_residence",
                    "q_value_below_loan",
                ]
            ]
        ).alias("quarantined")
    )
    return frame


def export(w: World, external: Path, derived: Path, hmda: Path, *, loan_scale: float = 1.0) -> dict[str, int]:
    """Write the world as the derived sources the warehouse reads. Returns row counts per file."""
    derived.mkdir(parents=True, exist_ok=True)
    hmda.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    n = w.metro_year["metro_id"].n_unique()
    codes = sorted(w.metro_year["metro_id"].unique().to_list())
    names = {
        r["metro_id"]: r["metro_name"]
        for r in w.metro_year.select(["metro_id", "metro_name"]).unique().iter_rows(named=True)
    }

    # FHFA: the all-transactions index per metro and quarter, plus a purchase-only copy for the first thirty
    q = w.metro_quarter
    fhfa_rows = []
    for flavor in ("all-transactions", "purchase-only"):
        sub = q if flavor == "all-transactions" else q.filter(pl.col("metro_id").is_in(codes[:30]))
        for r in sub.iter_rows(named=True):
            fhfa_rows.append(
                {
                    "place_id": r["metro_id"],
                    "place_name": names[r["metro_id"]],
                    "flavor": flavor,
                    "year": int(r["year"]),
                    "quarter": int(r["quarter"]),
                    "period": r["period"],
                    "index_nsa": float(r["index"]),
                    "index_sa": float(r["index"]) if flavor == "purchase-only" else None,
                    "is_division": False,
                    "q_missing_quarter": False,
                    "q_non_positive_index": False,
                    "q_implausible_jump": False,
                    "quarantined": False,
                }
            )
    fhfa = pl.DataFrame(fhfa_rows, schema_overrides={"index_sa": pl.Float64})
    fhfa.write_parquet(derived / "fhfa_quarterly.parquet")
    counts["fhfa_quarterly"] = fhfa.height

    rates = w.rates.with_columns(pl.lit(13).alias("weeks")).select(
        ["year", "quarter", "period", "rate", "weeks"]
    )
    rates.write_parquet(derived / "pmms_quarterly.parquet")
    counts["pmms_quarterly"] = rates.height

    acs = _acs_rows(w)
    acs.write_parquet(derived / "acs_long.parquet")
    counts["acs_long"] = acs.height

    # one county per metro, every vintage the same
    del_rows = []
    for v in (2009, 2013, 2015, 2017, 2018, 2020, 2023):
        for i, code in enumerate(codes):
            del_rows.append(
                {
                    "vintage": v,
                    "cbsa_code": code,
                    "cbsa_title": names[code],
                    "kind": "metropolitan",
                    "division_code": None,
                    "division_title": None,
                    "county_fips": _county(i),
                    "county_name": f"County {i + 1}",
                    "state_name": f"State {i % 9}",
                    "central": True,
                    "q_county_in_two_areas": False,
                    "q_malformed_fips": False,
                    "quarantined": False,
                }
            )
    delin = pl.DataFrame(del_rows, schema_overrides={"division_code": pl.Utf8, "division_title": pl.Utf8})
    delin.write_parquet(derived / "delineations.parquet")
    counts["delineations"] = delin.height
    # The same areas in every vintage, so the alias table is empty with its schema.
    geography.aliases(delin).write_parquet(derived / "area_aliases.parquet")
    gaz = pl.DataFrame(
        {
            "cbsa_code": codes,
            "name": [names[c] for c in codes],
            "kind": ["metropolitan"] * n,
            "land_sqmi": [1000.0] * n,
            "latitude": [30.0 + i * 0.3 for i in range(n)],
            "longitude": [-120.0 + i * 0.7 for i in range(n)],
            "gazetteer_year": [2026] * n,
        }
    )
    gaz.write_parquet(derived / "gazetteer.parquet")

    my = w.metro_year
    pop_rows = []
    permit_rows = []
    fmr_rows = []
    il_rows = []
    for r in my.iter_rows(named=True):
        i = codes.index(r["metro_id"])
        county = _county(i)
        y = int(r["year"])
        pop_rows.append(
            {
                "county_fips": county,
                "year": y,
                "vintage": 2025 if y >= 2020 else 2019 if y >= 2010 else 2009,
                "population": float(r["population"]),
                "births": float(r["population"]) * 0.012,
                "deaths": float(r["population"]) * 0.009,
                "international_migration": float(r["population"]) * 0.002,
                "domestic_migration": float(r["domestic_migration_per_100"]) * float(r["population"]) / 100.0,
                "intercensal_population": None,
            }
        )
        permit_rows.append(
            {
                "year": y,
                "partial_through_month": None,
                "county_fips": county,
                "units_1": float(r["permits"]) * 0.7,
                "units_2": 0.0,
                "units_3_4": 0.0,
                "units_5_plus": float(r["permits"]) * 0.3,
                "units_total": float(r["permits"]),
                "buildings_total": float(r["permits"]) * 0.75,
                "value_total": float(r["permits"]) * 250_000.0,
                "units_total_reported": float(r["permits"]) * 0.95,
                "q_negative_units": False,
                "q_imputed_share_high": False,
                "q_malformed_fips": False,
                "quarantined": False,
            }
        )
        fmr_rows.append(
            {
                "county_fips": county,
                "fiscal_year": y,
                "fmr_0": float(r["median_rent"]) * 0.8,
                "fmr_1": float(r["median_rent"]) * 0.9,
                "fmr_2": float(r["median_rent"]) * 1.05,
                "fmr_3": float(r["median_rent"]) * 1.4,
                "fmr_4": float(r["median_rent"]) * 1.7,
            }
        )
        il_rows.append(
            {
                "county_fips": county,
                "fiscal_year": y,
                "hud_area_code": f"METRO{r['metro_id']}",
                "hud_area_name": names[r["metro_id"]],
                "cbsa_code": r["metro_id"],
                "median_family_income": float(r["median_income"]) * 1.2,
                "l30_4": float(r["median_income"]) * 0.36,
                "l50_4": float(r["median_income"]) * 0.6,
                "l80_4": float(r["median_income"]) * 0.96,
                "q_non_positive_income": False,
                "q_limit_order": False,
                "quarantined": False,
            }
        )
    pl.DataFrame(pop_rows, schema_overrides={"intercensal_population": pl.Float64}).write_parquet(
        derived / "popest_county.parquet"
    )
    pl.DataFrame(permit_rows, schema_overrides={"partial_through_month": pl.Int64}).write_parquet(
        derived / "bps_county.parquet"
    )
    pl.DataFrame(fmr_rows).write_parquet(derived / "hud_fmr_history.parquet")
    il = pl.DataFrame(il_rows)
    il.write_parquet(derived / "hud_income_limits.parquet")
    il.select(["county_fips", "fiscal_year", "hud_area_code", "hud_area_name", "cbsa_code"]).with_columns(
        pl.lit(1500.0).alias("fmr_0"),
        pl.lit(1600.0).alias("fmr_1"),
        pl.lit(1800.0).alias("fmr_2"),
        pl.lit(2200.0).alias("fmr_3"),
        pl.lit(2500.0).alias("fmr_4"),
        pl.lit(False).alias("q_non_positive_rent"),
        pl.lit(False).alias("q_bedroom_order"),
        pl.lit(False).alias("quarantined"),
    ).filter(pl.col("fiscal_year") == pl.col("fiscal_year").max()).write_parquet(
        derived / "hud_fmr_latest.parquet"
    )
    counts["popest_county"] = len(pop_rows)
    counts["bps_county"] = len(permit_rows)

    loans = _loan_rows(w, scale=loan_scale)
    for year in sorted(loans["year"].unique().to_list()):
        sub = loans.filter(pl.col("year") == year)
        sub.write_parquet(hmda / f"lar_{int(year)}.parquet")
        counts[f"lar_{int(year)}"] = sub.height
    return counts


def bracket_bounds() -> list[int]:
    return list(INCOME_BRACKETS)


__all__ = ["export", "lognormal_bracket_counts"]
