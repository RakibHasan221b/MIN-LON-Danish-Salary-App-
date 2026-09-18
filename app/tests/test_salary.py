from decimal import Decimal

from app.calculations.salary import (
    compute_monthly_gross_income,
    decimal_hours_worked,
    gross_from_fixed_salary,
    gross_from_hourly_wage,
    hours_and_minutes_to_decimal_hours,
)
from app.models.salary_input import IncomeType, SalaryInput


def test_spec_example_hourly_wage():
    """150 DKK/hour x 160 hours = 24,000 DKK gross monthly income."""
    assert gross_from_hourly_wage(Decimal("150"), 160) == Decimal("24000")


def test_spec_example_fixed_salary():
    """30,000 DKK/month = 30,000 DKK gross monthly income."""
    assert gross_from_fixed_salary(Decimal("30000")) == Decimal("30000")


def test_hourly_wage_with_minutes():
    # 100 kr/h x 37h30m = 3750
    assert gross_from_hourly_wage(Decimal("100"), 37, 30) == Decimal("3750")


def test_hours_and_minutes_conversion():
    assert hours_and_minutes_to_decimal_hours(39, 30) == Decimal("39.5")
    assert hours_and_minutes_to_decimal_hours(0, 0) == Decimal("0")
    assert hours_and_minutes_to_decimal_hours(1, 15) == Decimal("1.25")


def test_dispatch_hourly_wage_mode():
    inp = SalaryInput(
        income_type=IncomeType.HOURLY_WAGE,
        hourly_wage=Decimal("150"),
        hours=160,
        minutes=0,
    )
    assert compute_monthly_gross_income(inp) == Decimal("24000")


def test_dispatch_fixed_salary_mode():
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
    )
    assert compute_monthly_gross_income(inp) == Decimal("30000")


def test_modes_are_never_confused():
    """The two modes must not leak into each other's fields."""
    wage_input = SalaryInput(
        income_type=IncomeType.HOURLY_WAGE, hourly_wage=Decimal("200"), hours=100
    )
    assert wage_input.fixed_monthly_salary is None

    salary_input = SalaryInput(
        income_type=IncomeType.FIXED_SALARY, fixed_monthly_salary=Decimal("40000")
    )
    assert salary_input.hourly_wage is None
    assert salary_input.hours is None


def test_fixed_salary_mode_assumes_fulltime_hours_for_atp():
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY, fixed_monthly_salary=Decimal("30000")
    )
    assert decimal_hours_worked(inp) >= Decimal("117")


def test_hourly_mode_uses_actual_hours_for_atp():
    inp = SalaryInput(
        income_type=IncomeType.HOURLY_WAGE, hourly_wage=Decimal("150"), hours=50
    )
    assert decimal_hours_worked(inp) == Decimal("50")


def test_missing_required_fields_raise():
    import pytest

    with pytest.raises(ValueError):
        SalaryInput(income_type=IncomeType.HOURLY_WAGE)  # missing hourly_wage/hours

    with pytest.raises(ValueError):
        SalaryInput(income_type=IncomeType.FIXED_SALARY)  # missing fixed_monthly_salary
