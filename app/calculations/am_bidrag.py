"""AM-bidrag (labour market contribution) — 8%, applied on the
AM-bidragsgrundlag, which is gross income minus the employee's ATP
contribution. See docs/research_2026.md item 5 for the full ordering
rationale.

V1.2: an age-based exemption. See docs/research_2026.md item 14 for the
verified 2026 rule and its documented limitation — this app only collects
current age (an integer), not date of birth, so `is_exempt_by_age` uses
"age <= 17" as a deliberate, documented simplification of the real
whole-tax-year rule (which depends on whether the person turns 18 at any
point during the year, not their age today). It can over-exempt someone
who is 17 now but turns 18 later in the same tax year — this is flagged
in the UI and the research doc, never silently assumed away.
"""
from __future__ import annotations

from decimal import Decimal

AM_BIDRAG_AGE_EXEMPTION_MAX_AGE = 17


def is_exempt_by_age(age: int | None) -> bool:
    """True if `age` (current age in years, or None if not provided)
    qualifies for the simplified under-18 AM-bidrag exemption used by
    this app. None (age not provided) is never treated as exempt — the
    app defaults to the adult/no-exemption behaviour unless the user
    explicitly states an age of 17 or under."""
    return age is not None and age <= AM_BIDRAG_AGE_EXEMPTION_MAX_AGE


def compute_am_bidrag_base(gross_income: Decimal, atp_employee_contribution: Decimal) -> Decimal:
    """Gross income minus the employee's own ATP contribution."""
    return gross_income - atp_employee_contribution


def compute_am_bidrag(am_bidrag_base: Decimal, rate: Decimal, exempt: bool = False) -> Decimal:
    """8% of the AM-bidragsgrundlag, or 0 if `exempt` (see
    `is_exempt_by_age`) — never a silent hardcoded-adult assumption."""
    if exempt:
        return Decimal(0)
    return am_bidrag_base * rate
