"""Structured result models — the transparent breakdown the spec requires.

Never a single number: every stage of the pipeline gets its own labelled
line, in DKK, so the UI can render a breakdown instead of a lone total.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class CalculationBasis(str, Enum):
    STANDARD_ESTIMATE = "standard_estimate"
    TAX_CARD = "tax_card"
    FRIKORT = "frikort"
    MONTHLY_PAYSLIP = "monthly_payslip"


@dataclass(frozen=True)
class BreakdownLine:
    label: str
    amount: Decimal  # negative = deduction, positive = income/allowance


@dataclass(frozen=True)
class HolidayPayResult:
    """Feriegodtgørelse (hourly wage, 12.5%) or ferietillæg (fixed salary,
    1%) — a separate income stream from ordinary salary, never folded into
    it automatically. See docs/research_2026.md item 13a."""

    rate_used: Decimal  # 0.125 or 0.01
    rate_label: str  # "feriegodtgørelse (12.5%)" or "ferietillæg (1%)"
    gross: Decimal
    am_bidrag: Decimal
    income_tax: Decimal
    net: Decimal
    marginal_rate_applied: Decimal  # the combined rate used for income_tax


@dataclass(frozen=True)
class TotalWithHolidayResult:
    """Ordinary salary + holiday pay, summed from the two independently
    computed streams — never double-counting AM-bidrag or allowances."""

    gross: Decimal
    tax: Decimal
    net: Decimal


@dataclass(frozen=True)
class TaxResult:
    period: str  # "monthly" or "annual"
    calculation_basis: CalculationBasis

    gross_income: Decimal
    atp_employee_contribution: Decimal
    am_bidrag_base: Decimal
    am_bidrag: Decimal

    employment_allowance: Decimal
    job_allowance: Decimal

    taxable_income: Decimal  # personal income used for state tax brackets

    bundskat: Decimal
    mellemskat: Decimal
    topskat: Decimal
    ekstra_topskat: Decimal
    state_tax_total: Decimal

    municipal_tax: Decimal
    church_tax: Decimal
    is_church_member: bool

    net_income: Decimal
    effective_tax_rate: Decimal  # 0..1

    municipality_name: str
    tax_year: int = 2026
    assumptions: list[str] = field(default_factory=list)

    # V1.1 restorations — see docs/old_streamlit_feature_audit.md
    base_gross_income: Decimal = Decimal(0)  # gross income excluding tips
    tips: Decimal = Decimal(0)
    extra_deduction_applied: Decimal = Decimal(0)
    other_adjustments: Decimal = Decimal(0)  # reserved for a future misc. adjustment; 0 in V1.1
    holiday_pay: "HolidayPayResult | None" = None
    total_with_holiday: "TotalWithHolidayResult | None" = None

    # V1.2 — transparency fields
    age_am_bidrag_exempt: bool = False  # see docs/research_2026.md item 14
    remaining_frikort_amount: Decimal | None = None  # echoed back for FRIKORT results

    # Monthly-first simplified default flow (MONTHLY_PAYSLIP basis only).
    # See app/calculations/payslip.py.
    monthly_deduction_applied: Decimal = Decimal(0)
    tax_percentage_used: Decimal | None = None  # the trækprocent actually applied (0..1)
    tax_percentage_estimated: bool = False  # True when the user left % blank and we estimated it

    @property
    def total_tax(self) -> Decimal:
        return (
            self.atp_employee_contribution
            + self.am_bidrag
            + self.state_tax_total
            + self.municipal_tax
            + self.church_tax
            + self.other_adjustments
        )

    def breakdown(self) -> list[BreakdownLine]:
        """Ordered, display-ready line items. Zero-value rows are omitted
        by the caller (per spec) — this returns every computed line and
        lets the presentation layer decide what to hide."""
        if self.calculation_basis is CalculationBasis.MONTHLY_PAYSLIP:
            return self._monthly_payslip_breakdown()

        lines: list[BreakdownLine] = []
        if self.tips:
            lines.append(BreakdownLine("Base gross", self.base_gross_income))
            lines.append(BreakdownLine("Tips / extra income", self.tips))
            lines.append(BreakdownLine("Total gross", self.gross_income))
        else:
            lines.append(BreakdownLine("Gross income", self.gross_income))

        lines.append(BreakdownLine("ATP", -self.atp_employee_contribution))
        lines.append(BreakdownLine("AM-bidrag", -self.am_bidrag))
        lines.append(BreakdownLine("Employment allowance", self.employment_allowance))
        lines.append(BreakdownLine("Job allowance", self.job_allowance))
        if self.extra_deduction_applied:
            lines.append(BreakdownLine("Additional deduction", self.extra_deduction_applied))

        if self.calculation_basis is CalculationBasis.STANDARD_ESTIMATE:
            lines += [
                BreakdownLine("Bottom tax (bundskat)", -self.bundskat),
                BreakdownLine("Middle tax (mellemskat)", -self.mellemskat),
                BreakdownLine("Top tax (topskat)", -self.topskat),
                BreakdownLine("Additional top tax", -self.ekstra_topskat),
            ]
        elif self.calculation_basis is CalculationBasis.FRIKORT:
            lines.append(BreakdownLine("Income tax (Frikort — tax-free)", -self.state_tax_total))
        else:
            lines.append(BreakdownLine("State Tax / A-skat (tax card)", -self.state_tax_total))
        lines.append(BreakdownLine("Municipal tax", -self.municipal_tax))
        if self.is_church_member:
            lines.append(BreakdownLine("Church tax", -self.church_tax))
        if self.other_adjustments:
            lines.append(BreakdownLine("Other applicable adjustment", -self.other_adjustments))
        lines.append(BreakdownLine("Estimated net salary", self.net_income))
        return lines

    def _monthly_payslip_breakdown(self) -> list[BreakdownLine]:
        """Simplified monthly-first flow: gross -> AM-bidrag -> fradrag ->
        trækprocent -> ATP -> net, in that literal order — matches the
        product decision that this default flow needs no bracket-by-
        bracket detail, just the payslip-style line items."""
        lines: list[BreakdownLine] = []
        if self.tips:
            lines.append(BreakdownLine("Base gross", self.base_gross_income))
            lines.append(BreakdownLine("Tips / extra income", self.tips))
            lines.append(BreakdownLine("Gross salary", self.gross_income))
        else:
            lines.append(BreakdownLine("Gross salary", self.gross_income))
        lines.append(BreakdownLine("AM-bidrag", -self.am_bidrag))
        lines.append(BreakdownLine("Monthly fradrag", -self.monthly_deduction_applied))
        lines.append(BreakdownLine("Taxable after fradrag", self.taxable_income))
        lines.append(BreakdownLine("A-tax / withheld tax", -self.state_tax_total))
        lines.append(BreakdownLine("ATP", -self.atp_employee_contribution))
        lines.append(BreakdownLine("Estimated net salary", self.net_income))
        return lines
