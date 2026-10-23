"""Pre-registration: every chapter plan hashed before the real data is analysed.

The pipeline calls ``register`` before any estimate runs on the real metros and writes
results/chapters/plans.json with every plan and its hash. The method notes print the hash; a test
recomputes the hash of the committed plan and fails if it differs; a plan edited after registration
changes its hash and stops the stage. ``MODULES`` is the chapter order the story uses.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType
from typing import Any

from doorstep_core.config import POLICY, Policy

from doorstep_chapters import (
    c1_definition,
    c2_rate_shock,
    c3_burden,
    c4_supply,
    c5_ranking,
    c6_buyers,
    c7_migration,
    c8_decision,
)
from doorstep_chapters.common import plan_hash

MODULES: tuple[ModuleType, ...] = (
    c1_definition,
    c2_rate_shock,
    c3_burden,
    c4_supply,
    c5_ranking,
    c6_buyers,
    c7_migration,
    c8_decision,
)


class RegistrationError(RuntimeError):
    pass


def all_plans(policy: Policy = POLICY) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for module in MODULES:
        plan = module.plan(policy)
        out.append(
            {
                "number": module.NUMBER,
                "slug": module.SLUG,
                "title": module.TITLE,
                "plan": plan,
                "hash": plan_hash(plan),
            }
        )
    return out


def register(path: Path, policy: Policy = POLICY) -> dict[str, str]:
    """Write every plan and its hash; returns slug to hash. An existing registration with a different hash for the
    same slug is a plan that changed after registration, which stops the stage."""
    plans = all_plans(policy)
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        seen = {p["slug"]: p["hash"] for p in existing.get("plans", [])}
        for p in plans:
            if p["slug"] in seen and seen[p["slug"]] != p["hash"]:
                raise RegistrationError(
                    f"chapter {p['number']} ({p['slug']}) changed after registration: {seen[p['slug']]} is registered, "
                    f"the committed plan hashes to {p['hash']}; delete the registration on purpose to re-register"
                )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"plans": plans}, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return {p["slug"]: p["hash"] for p in plans}


def registered_hashes(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {p["slug"]: p["hash"] for p in payload["plans"]}
