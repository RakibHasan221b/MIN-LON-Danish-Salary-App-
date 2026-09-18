"""Step 1 of the pipeline: turn either income-entry mode into one monthly
gross income figure. This is the ONLY place the two input modes are
reconciled — everything downstream of this module treats "gross monthly
income" as one thing, regardless of which mode produced it.
"""
from __future__ import annotations

from decimal import Decimal

from app.models.salary_input import IncomeType, SalaryInput


def hours_and_minutes_to_decimal_hours(hours: int, minutes: int) -> Decimal:
    """39h 30m -> Decimal('39.5')."""
    return Decimal(hours) + (Decimal(minutes) / Decimal(60))


def gross_from_hourly_wage(
    hourly_wage: Decimal, hours: int, minutes: int = 0
) -> Decimal:
    """Option 1 — Monthly Wage: hourly rate x hours worked.

    Example from the spec: 150 DKK/hour x 160 hours = 24,000 DKK.
    """
    total_hours = hours_and_minutes_to_decimal_hours(hours, minutes)
    return hourly_wage * total_hours


def gross_from_fixed_salary(fixed_monthly_salary: Decimal) -> Decimal:
    """Option 2 — Monthly Salary: the fixed amount IS the gross income."""
    return fixed_monthly_salary


def compute_monthly_gross_income(salary_input: SalaryInput) -> Decimal:
    """Dispatch on income_type. This is the single entry point the rest
    of the engine (and the API layer) should call — never branch on
    income_type anywhere else."""
    if salary_input.income_type is IncomeType.HOURLY_WAGE:
        return gross_from_hourly_wage(
            salary_input.hourly_wage,
            salary_input.hours,
            salary_input.minutes or 0,
        )
    elif salary_input.income_type is IncomeType.FIXED_SALARY:
        return gross_from_fixed_salary(salary_input.fixed_monthly_salary)
    raise ValueError(f"Unknown income_type: {salary_input.income_type}")


def decimal_hours_worked(salary_input: SalaryInput) -> Decimal:
    """Hours worked in the month, used by atp.py. Monthly Salary mode has
    no hours field in V1, so full-time (>=117h) is assumed — this is a
    documented assumption (see docs/research_2026.md item 13), not a
    silent default."""
    if salary_input.income_type is IncomeType.HOURLY_WAGE:
        return hours_and_minutes_to_decimal_hours(
            salary_input.hours, salary_input.minutes or 0
        )
    return Decimal(160)  # ~ full-time monthly hours, safely >= 117 ATP threshold
