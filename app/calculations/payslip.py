"""Monthly payslip-style withholding — the simplified, monthly-first
default calculation (product decision: the main flow should not require
understanding Hovedkort/Bikort/Frikort, annual tax, or progressive
bracket logic).

Order of operations, verified against a real DataLøn payslip (gross
1,050 / ATP 99 / AM-bidrag 76 on a base of 951 / A-Indkomst 875 / A-skat
0 because fradrag covered it / net 875):

    gross income
    minus ATP                          -> gross - ATP
    AM-bidrag = 8% of (gross - ATP)
    minus AM-bidrag                    -> A-Indkomst (income after AM)
    minus monthly fradrag, floored at 0 -> taxable A-skat base
    apply trækprocent                   -> A-skat / withheld tax
    net = gross - ATP - AM-bidrag - A-skat

An earlier version of this module used gross (not gross-ATP) as the
AM-bidrag base and never subtracted ATP before applying fradrag; both
were bugs, caught by comparing against the real payslip above, not
intentional simplifications. This still stays a separate function from
app.calculations.withholding (the "Use my tax card" advanced flow)
rather than being merged into it, so each one's tests still catch a
regression in the other, but the two now agree on this ordering.
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
    """gross - ATP - AM-bidrag - fradrag = taxable (A-skat base);
    taxable * trækprocent = withheld tax (A-skat);
    gross - ATP - AM-bidrag - withheld tax = net.

    taxable_after_fradrag is floored at 0 — a fradrag larger than what's
    left after ATP and AM-bidrag never produces a negative taxable base
    (and therefore never a negative withheld_tax). This matches a real
    payslip's own A-Indkomst (income after ATP and AM-bidrag) being the
    base fradrag is subtracted from, not gross income directly."""
    income_after_am = gross_income - atp_employee_contribution - am_bidrag_amount
    taxable_after_fradrag = income_after_am - monthly_deduction
    taxable_after_fradrag = max(taxable_after_fradrag, Decimal(0))
    withheld_tax = taxable_after_fradrag * tax_percentage
    net_income = income_after_am - withheld_tax

    return PayslipWithholdingResult(
        taxable_after_fradrag=taxable_after_fradrag,
        withheld_tax=withheld_tax,
        net_income=net_income,
    )
