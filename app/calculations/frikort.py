"""Frikort (tax-free card) withholding.

A frikort lets a person earn income completely free of state/municipal/
church income tax up to a running annual balance shown on their
forskudsopgørelse ("Resterende frikortbeløb" / remaining Frikort amount).
This module handles ONLY the well-verified case: the income being
calculated is within the user's stated remaining balance, so income tax
is 0 for this amount.

AM-bidrag and ATP are NOT exempted by frikort status — those still apply
per the normal rules (an age exemption for AM-bidrag is handled
separately in app.calculations.am_bidrag and is independent of frikort).

What this module deliberately does NOT do: if the entered income exceeds
the user's remaining Frikort balance, SKAT would normally switch the
person to bikort withholding for the excess — reconstructing that split
correctly requires knowing exactly how much of THIS period's income falls
before/after the balance is exhausted, which this app cannot verify from
a single period's inputs alone. Rather than inventing a blended
calculation or silently falling back to another tax-card type, this
module raises a clear, actionable ValueError directing the user to
Bikort or a lower income figure. See docs/research_2026.md item 15.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class FrikortBalanceExceededError(ValueError):
    """Raised when the entered income exceeds the user's remaining
    Frikort balance — this app does not attempt to calculate the
    bikort-rate tax on the excess portion. See module docstring."""


@dataclass(frozen=True)
class FrikortResult:
    withholding_base: Decimal
    withheld_tax: Decimal  # always 0 for the supported case


def compute_frikort_withholding(
    gross_income: Decimal,
    atp_employee_contribution: Decimal,
    am_bidrag: Decimal,
    remaining_frikort_amount: Decimal,
) -> FrikortResult:
    """Supported case only: gross_income <= remaining_frikort_amount.
    Compares against gross income (a documented assumption — see
    docs/research_2026.md item 15; not independently verified whether
    SKAT compares the balance against gross A-indkomst or an
    AM-bidrag-adjusted figure)."""
    if gross_income > remaining_frikort_amount:
        raise FrikortBalanceExceededError(
            "This income is more than your remaining Frikort amount "
            f"(DKK {remaining_frikort_amount:,.0f}). We can't correctly estimate the tax on "
            "the part above your balance. Switch to Bikort / Second job above, or lower the "
            "income so it fits inside your remaining Frikort balance."
        )
    withholding_base = gross_income - atp_employee_contribution - am_bidrag
    withholding_base = max(withholding_base, Decimal(0))
    return FrikortResult(withholding_base=withholding_base, withheld_tax=Decimal(0))
