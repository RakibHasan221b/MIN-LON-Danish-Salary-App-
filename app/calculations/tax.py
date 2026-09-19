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


def _band_income(
    personlig_indkomst: Decimal, lower: Decimal, upper: Decimal | None
) -> Decimal:
    """How much personal income falls inside [lower, upper)."""
    if personlig_indkomst <= lower:
        return Decimal(0)
    top = personlig_indkomst if upper is None else min(personlig_indkomst, upper)
    return max(top - lower, Decimal(0))


def compute_state_tax(
    personlig_indkomst: Decimal,
    personal_allowance: Decimal,
    brackets: dict,
    municipal_rate: Decimal | None = None,
    skatteloft: dict | None = None,
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

    # Skatteloft (PSL 19). The combined rate of state personal-income tax
    # plus MUNICIPAL tax is capped, and the cap is tiered by band. Where the
    # combined rate would exceed the band's ceiling, the state tax on the
    # income in that band is reduced by the excess (the "nedslag"). Church
    # tax and AM-bidrag sit outside the ceiling and are not counted here.
    #
    # Without this, anyone above the mellemskat threshold in a municipality
    # above roughly 25.06% (75 of the 98) is overcharged.
    if municipal_rate is not None and skatteloft is not None:
        bund_rate = Decimal(str(brackets["bundskat"]["rate"]))
        mellem_rate = Decimal(str(brackets["mellemskat"]["rate"]))
        top_rate = Decimal(str(brackets["topskat"]["rate"]))
        ekstra_rate = Decimal(str(brackets["ekstra_topskat"]["rate"]))

        mellem_threshold = Decimal(str(brackets["mellemskat"]["threshold"]))
        top_threshold = Decimal(str(brackets["topskat"]["threshold"]))
        ekstra_threshold = Decimal(str(brackets["ekstra_topskat"]["threshold"]))

        def nedslag(
            cumulative_state_rate: Decimal, ceiling: Decimal, income_in_band: Decimal
        ) -> Decimal:
            excess = cumulative_state_rate + municipal_rate - ceiling
            if excess <= 0 or income_in_band <= 0:
                return Decimal(0)
            return excess * income_in_band

        mellemskat -= nedslag(
            bund_rate + mellem_rate,
            Decimal(str(skatteloft["mellemskat_band_rate"])),
            _band_income(personlig_indkomst, mellem_threshold, top_threshold),
        )
        topskat -= nedslag(
            bund_rate + mellem_rate + top_rate,
            Decimal(str(skatteloft["topskat_band_rate"])),
            _band_income(personlig_indkomst, top_threshold, ekstra_threshold),
        )
        ekstra_topskat -= nedslag(
            bund_rate + mellem_rate + top_rate + ekstra_rate,
            Decimal(str(skatteloft["ekstra_topskat_band_rate"])),
            _band_income(personlig_indkomst, ekstra_threshold, None),
        )

        mellemskat = max(mellemskat, Decimal(0))
        topskat = max(topskat, Decimal(0))
        ekstra_topskat = max(ekstra_topskat, Decimal(0))

    return StateTaxResult(
        bundskat=bundskat,
        mellemskat=mellemskat,
        topskat=topskat,
        ekstra_topskat=ekstra_topskat,
    )
