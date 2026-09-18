"""Employment allowance (beskæftigelsesfradrag) and job allowance
(jobfradrag) — both computed on the AM-bidragsgrundlag (income subject to
AM-bidrag, i.e. before the 8% is subtracted), per skat.dk's own wording.
See docs/research_2026.md items 3-4.
"""
from __future__ import annotations

from decimal import Decimal


def compute_employment_allowance(
    am_bidrag_base: Decimal, rate: Decimal, max_amount: Decimal
) -> Decimal:
    """12.75% of AM-bidragsgrundlag, capped at max_amount."""
    return min(am_bidrag_base * rate, max_amount)


def compute_job_allowance(
    am_bidrag_base: Decimal, rate: Decimal, floor_amount: Decimal, max_amount: Decimal
) -> Decimal:
    """4.5% of the AM-bidragsgrundlag ABOVE floor_amount, capped at max_amount.
    Zero if am_bidrag_base does not exceed the floor."""
    excess = am_bidrag_base - floor_amount
    if excess <= 0:
        return Decimal(0)
    return min(excess * rate, max_amount)
