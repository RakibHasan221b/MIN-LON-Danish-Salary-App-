"""Progressive Danish state tax: bundskat, mellemskat, topskat, ekstra
topskat. Applied to personlig indkomst (personal income), NEVER as a flat
percentage of gross. See docs/research_2026.md item 9 for the exact base
definitions this module relies on.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class StateTaxResult:
    bundskat: Decimal
    mellemskat: Decimal
    topskat: Decimal
    ekstra_topskat: Decimal

    @property
    def total(self) -> Decimal:
        return self.bundskat + self.mellemskat + self.topskat + self.ekstra_topskat


def compute_personlig_indkomst(am_bidrag_base: Decimal, am_bidrag: Decimal) -> Decimal:
    """Personal income = AM-bidragsgrundlag minus the AM-bidrag itself."""
    return am_bidrag_base - am_bidrag


def _bracket_tax(personlig_indkomst: Decimal, rate: Decimal, threshold: Decimal) -> Decimal:
    excess = personlig_indkomst - threshold
    if excess <= 0:
        return Decimal(0)
    return excess * rate


def compute_state_tax(
    personlig_indkomst: Decimal,
    personal_allowance: Decimal,
    brackets: dict,
) -> StateTaxResult:
    """Implements the four 2026 brackets, each on its correct base:

    - bundskat: rate x max(0, personlig_indkomst - personal_allowance)
    - mellemskat / topskat / ekstra_topskat: rate x max(0, personlig_indkomst - threshold)
      (their thresholds already account for the personal allowance's effect
      per skat.dk — the allowance is NOT subtracted again here).

    `brackets` is the "state_tax_brackets" dict straight from
    tax_rules_2026.json, so every rate/threshold is data-driven.
    """
    bund_base = personlig_indkomst - personal_allowance
    bundskat = max(bund_base, Decimal(0)) * Decimal(str(brackets["bundskat"]["rate"]))

    mellemskat = _bracket_tax(
        personlig_indkomst,
        Decimal(str(brackets["mellemskat"]["rate"])),
        Decimal(str(brackets["mellemskat"]["threshold"])),
    )
    topskat = _bracket_tax(
        personlig_indkomst,
        Decimal(str(brackets["topskat"]["rate"])),
        Decimal(str(brackets["topskat"]["threshold"])),
    )
    ekstra_topskat = _bracket_tax(
        personlig_indkomst,
        Decimal(str(brackets["ekstra_topskat"]["rate"])),
        Decimal(str(brackets["ekstra_topskat"]["threshold"])),
    )

    return StateTaxResult(
        bundskat=bundskat,
        mellemskat=mellemskat,
        topskat=topskat,
        ekstra_topskat=ekstra_topskat,
    )
