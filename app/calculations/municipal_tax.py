"""Municipal tax (kommuneskat) and church tax (kirkeskat). Both are flat
percentages of skattepligtig indkomst (taxable income, after the
employment/job allowances AND the personal allowance) — never a flat
percentage of gross. See docs/research_2026.md item 9.
"""
from __future__ import annotations

from decimal import Decimal


def compute_skattepligtig_indkomst(
    personlig_indkomst: Decimal, employment_allowance: Decimal, job_allowance: Decimal
) -> Decimal:
    """Taxable income = personal income minus the ligningsmæssige fradrag
    (employment allowance + job allowance)."""
    return personlig_indkomst - employment_allowance - job_allowance


def compute_municipal_tax(
    skattepligtig_indkomst: Decimal, personal_allowance: Decimal, municipal_rate: Decimal
) -> Decimal:
    base = skattepligtig_indkomst - personal_allowance
    return max(base, Decimal(0)) * municipal_rate


def compute_church_tax(
    skattepligtig_indkomst: Decimal,
    personal_allowance: Decimal,
    church_rate: Decimal,
    is_church_member: bool,
) -> Decimal:
    """Zero unless the user is a Folkekirken member — church tax is never
    applied automatically."""
    if not is_church_member:
        return Decimal(0)
    base = skattepligtig_indkomst - personal_allowance
    return max(base, Decimal(0)) * church_rate
