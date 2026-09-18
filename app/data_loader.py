"""Loads the 2026 tax/ATP/municipality datasets from app/data/*.json.

Kept deliberately separate from the calculation modules: the engine never
hard-codes a rate or threshold, it always reads these through here, so a
future tax year is added by dropping in new JSON files rather than editing
calculation code.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"


@lru_cache(maxsize=None)
def _load_json(filename: str) -> Any:
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_tax_rules(year: int = 2026) -> dict:
    return _load_json(f"tax_rules_{year}.json")


def load_atp_rules(year: int = 2026) -> dict:
    return _load_json(f"atp_{year}.json")


def load_municipalities(year: int = 2026) -> list[dict]:
    return _load_json(f"municipalities_{year}.json")


def get_municipality(name: str, year: int = 2026) -> dict | None:
    for m in load_municipalities(year):
        if m["name"].casefold() == name.casefold():
            return m
    return None
