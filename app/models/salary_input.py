"""Input models for the calculation engine.

Two fundamentally different ways to enter income (Monthly Wage vs Monthly
Salary) are modelled as an explicit enum + optional fields, rather than
collapsing them into "gross income" before they reach the engine — the
engine's own first step (salary.py) is what turns either shape into a
single monthly gross figure, so this distinction is never lost or
guessed at silently.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class IncomeType(str, Enum):
    HOURLY_WAGE = "hourly_wage"      # Option 1: Monthly Wage
    FIXED_SALARY = "fixed_salary"    # Option 2: Monthly Salary


class TaxCardType(str, Enum):
    HOVEDKORT = "hovedkort"
    BIKORT = "bikort"
    FRIKORT = "frikort"


class TaxCardMode(str, Enum):
    STANDARD_ESTIMATE = "standard_estimate"
    MY_TAX_CARD = "my_tax_card"


@dataclass(frozen=True)
class SalaryInput:
    income_type: IncomeType

    # Option 1 — Monthly Wage
    hourly_wage: Decimal | None = None
    hours: int | None = None
    minutes: int | None = None

    # Option 2 — Monthly Salary
    fixed_monthly_salary: Decimal | None = None

    # Common inputs
    municipality_name: str = "København"
    is_church_member: bool = False

    # V1.2 — age. Used only to determine AM-bidrag age exemption (see
    # docs/research_2026.md item 14 for the exact rule and its documented
    # limitation: this app only collects current age, not date of birth,
    # so it cannot capture the real "turns 18 during the tax year" rule
    # exactly). None means "not provided" and is treated as an adult (no
    # exemption) — the app never silently assumes exemption.
    age: int | None = None

    # V1.1 restorations from the old Streamlit prototype (see
    # docs/old_streamlit_feature_audit.md) — both optional, default to 0
    # so existing callers are unaffected.
    tips: Decimal = Decimal(0)
    extra_deduction: Decimal = Decimal(0)  # see docs/research_2026.md item 13c

    # Tax-card mode
    tax_card_mode: TaxCardMode = TaxCardMode.STANDARD_ESTIMATE
    tax_card_type: TaxCardType = TaxCardType.HOVEDKORT
    tax_card_percentage: Decimal | None = None       # required if MY_TAX_CARD, not FRIKORT
    tax_card_monthly_deduction: Decimal | None = None  # hovedkort only; 0 for bikort

    # V1.2 — Frikort. The user's remaining tax-free balance for the year,
    # as shown on their forskudsopgørelse. See docs/research_2026.md item
    # 15: this is a documented assumption about the balance's base, and
    # income that exceeds the remaining balance is NOT silently taxed
    # under another mode — it is rejected with a clear, actionable error.
    remaining_frikort_amount: Decimal | None = None

    # Monthly-first simplified default flow (product decision: users
    # should not need to understand Hovedkort/Bikort/Frikort or annual
    # tax logic to use the app). Both optional; mutually exclusive with
    # tax_card_mode=MY_TAX_CARD (that is the separate, advanced flow).
    # See app/calculations/payslip.py for the calculation this feeds.
    monthly_deduction: Decimal | None = None  # fradrag, e.g. 5207
    tax_percentage: Decimal | None = None      # trækprocent, e.g. 0.37

    def __post_init__(self) -> None:
        if self.income_type is IncomeType.HOURLY_WAGE:
            if self.hourly_wage is None or self.hours is None:
                raise ValueError(
                    "Please enter your hourly wage and hours worked."
                )
            if self.hourly_wage < 0:
                raise ValueError("Please enter a valid hourly wage in DKK (0 or more).")
            if self.hours < 0:
                raise ValueError("Please enter a valid number of hours worked (0 or more).")
        elif self.income_type is IncomeType.FIXED_SALARY:
            if self.fixed_monthly_salary is None:
                raise ValueError(
                    "Please enter your fixed monthly salary in DKK."
                )
            if self.fixed_monthly_salary < 0:
                raise ValueError("Please enter a valid monthly salary in DKK (0 or more).")

        if self.minutes is not None and not (0 <= self.minutes <= 59):
            raise ValueError("Minutes must be between 0 and 59.")

        if self.age is not None:
            if not (0 <= self.age <= 120):
                raise ValueError("Please enter a realistic age (0-120).")

        if self.tips is not None and self.tips < 0:
            raise ValueError("Tips can't be negative — enter 0 if you didn't receive any tips.")
        if self.extra_deduction is not None and self.extra_deduction < 0:
            raise ValueError("Additional deduction can't be negative — enter 0 if it doesn't apply.")

        if self.tax_card_mode is TaxCardMode.MY_TAX_CARD:
            if self.tax_card_type is TaxCardType.FRIKORT:
                if self.remaining_frikort_amount is None:
                    raise ValueError(
                        "Please enter your remaining Frikort amount (from your forskudsopgørelse)."
                    )
                if self.remaining_frikort_amount < 0:
                    raise ValueError("Remaining Frikort amount can't be negative.")
                # Frikort has no withholding percentage/deduction — those
                # fields belong to hovedkort/bikort and must not be mixed in.
                if self.tax_card_percentage is not None or self.tax_card_monthly_deduction is not None:
                    raise ValueError(
                        "Frikort doesn't use a withholding percentage or monthly deduction — "
                        "only the remaining Frikort amount."
                    )
                return

            if self.tax_card_percentage is None:
                raise ValueError(
                    "Please enter your tax card withholding percentage."
                )
            if not (Decimal(0) <= self.tax_card_percentage <= Decimal(1)):
                raise ValueError("Withholding percentage must be between 0% and 100%.")
            if (
                self.tax_card_type is TaxCardType.HOVEDKORT
                and self.tax_card_monthly_deduction is None
            ):
                raise ValueError(
                    "Please enter your monthly deduction (fradrag) for your hovedkort."
                )
            if self.tax_card_monthly_deduction is not None and self.tax_card_monthly_deduction < 0:
                raise ValueError("Monthly deduction can't be negative.")

        if self.tax_percentage is not None and not (Decimal(0) <= self.tax_percentage <= Decimal(1)):
            raise ValueError("Tax percentage must be between 0% and 100%.")
        if self.monthly_deduction is not None and self.monthly_deduction < 0:
            raise ValueError("Monthly deduction can't be negative.")
        if self.tax_card_mode is TaxCardMode.MY_TAX_CARD and (
            self.monthly_deduction is not None or self.tax_percentage is not None
        ):
            raise ValueError(
                "Monthly deduction and tax percentage are part of the simple monthly flow, "
                "they can't be combined with 'Use my tax card' (Hovedkort/Bikort/Frikort)."
            )
