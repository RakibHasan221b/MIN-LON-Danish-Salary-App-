"""Tax-card-based withholding: an ALTERNATIVE to the standard bracket
estimate, used only when the user supplies their actual SKAT-issued
withholding percentage (and, for hovedkort, their monthly fradrag).

This module makes no attempt to reconstruct that percentage/fradrag from
salary and municipality alone — the spec is explicit that this cannot be
done honestly without the person's full forskudsopgørelse. It only
applies numbers the user already has in hand.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.models.salary_input import TaxCardType


@dataclass(frozen=True)
class TaxCardWithholdingResult:
    withholding_base: Decimal
    withheld_tax: Decimal


def compute_tax_card_withholding(
    gross_income: Decimal,
    atp_employee_contribution: Decimal,
    am_bidrag: Decimal,
    tax_card_percentage: Decimal,
    tax_card_type: TaxCardType,
    tax_card_monthly_deduction: Decimal | None,
) -> TaxCardWithholdingResult:
    """withholding_base = gross - ATP - AM-bidrag - fradrag (hovedkort only).
    withheld_tax = tax_card_percentage x withholding_base.

    Bikort applies no monthly fradrag, per SKAT rules — withholding
    starts from the first krone of that employment's income.

    Frikort is NOT handled here — it has no withholding percentage at
    all and is routed to app.calculations.frikort.compute_frikort_withholding
    instead. Calling this with tax_card_type=FRIKORT is a programming
    error, not a user input to silently coerce.
    """
    if tax_card_type is TaxCardType.FRIKORT:
        raise ValueError(
            "Frikort withholding must be computed via app.calculations.frikort, not "
            "compute_tax_card_withholding."
        )

    deduction = Decimal(0)
    if tax_card_type is TaxCardType.HOVEDKORT:
        deduction = tax_card_monthly_deduction or Decimal(0)

    withholding_base = gross_income - atp_employee_contribution - am_bidrag - deduction
    withholding_base = max(withholding_base, Decimal(0))
    withheld_tax = withholding_base * tax_card_percentage

    return TaxCardWithholdingResult(
        withholding_base=withholding_base, withheld_tax=withheld_tax
    )
