"""Monthly payslip-style withholding — the simplified, monthly-first
default calculation (product decision: the main flow should not require
understanding Hovedkort/Bikort/Frikort, annual tax, or progressive
bracket logic).

This is deliberately a DIFFERENT order of operations from
app.calculations.withholding (the "Use my tax card" advanced flow):
that module subtracts ATP before computing the AM-bidrag base and before
applying withholding. This module follows the literal top-to-bottom order
given in the product spec:

    gross income
    minus AM-bidrag          (computed directly on gross, not gross-ATP)
    minus monthly fradrag    -> taxable after fradrag
    apply trækprocent        -> A-tax / withheld tax
    minus ATP                -> net salary

Both are legitimate, documented simplifications of a real payslip; they
are kept as separate functions rather than merged, so neither one's
behavior (and tests) can silently drift when the other changes.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PayslipWithholdingResult:
    taxable_after_fradrag: Decimal
    withheld_tax: Decimal
    net_income: Decimal


def compute_payslip_withholding(
    gross_income: Decimal,
    am_bidrag_amount: Decimal,
    monthly_deduction: Decimal,
    tax_percentage: Decimal,
    atp_employee_contribution: Decimal,
) -> PayslipWithholdingResult:
    """gross - AM-bidrag - fradrag = taxable; taxable * trækprocent =
    withheld tax; gross - AM-bidrag - withheld tax - ATP = net.

    taxable_after_fradrag is floored at 0 — a fradrag larger than what's
    left after AM-bidrag never produces a negative taxable base (and
    therefore never a negative withheld_tax)."""
    taxable_after_fradrag = gross_income - am_bidrag_amount - monthly_deduction
    taxable_after_fradrag = max(taxable_after_fradrag, Decimal(0))
    withheld_tax = taxable_after_fradrag * tax_percentage
    net_income = gross_income - am_bidrag_amount - withheld_tax - atp_employee_contribution

    return PayslipWithholdingResult(
        taxable_after_fradrag=taxable_after_fradrag,
        withheld_tax=withheld_tax,
        net_income=net_income,
    )
