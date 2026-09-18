from decimal import Decimal

from app.calculations.engine import calculate_annual_tax, calculate_monthly_withholding
from app.models.salary_input import (
    IncomeType,
    SalaryInput,
    TaxCardMode,
    TaxCardType,
)
from app.models.tax_result import CalculationBasis


def test_spec_example_hourly_wage_end_to_end():
    """150 DKK/hr x 160h in Copenhagen, church member."""
    inp = SalaryInput(
        income_type=IncomeType.HOURLY_WAGE,
        hourly_wage=Decimal("150"),
        hours=160,
        minutes=0,
        municipality_name="København",
        is_church_member=True,
    )
    result = calculate_monthly_withholding(inp)
    assert result.gross_income == Decimal("24000")
    assert result.calculation_basis is CalculationBasis.STANDARD_ESTIMATE
    # Net must be positive and less than gross.
    assert Decimal("0") < result.net_income < result.gross_income
    # Church tax must be charged (member = True).
    assert result.church_tax > 0


def test_spec_example_fixed_salary_end_to_end():
    """30,000 DKK/month fixed salary, not a church member."""
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="Aarhus",
        is_church_member=False,
    )
    result = calculate_monthly_withholding(inp)
    assert result.gross_income == Decimal("30000")
    assert result.church_tax == Decimal(0)  # never auto-applied


def test_church_tax_zero_when_not_a_member_even_in_high_church_tax_municipality():
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="Læsø",  # highest church tax rate in the dataset
        is_church_member=False,
    )
    result = calculate_monthly_withholding(inp)
    assert result.church_tax == Decimal(0)


def test_church_tax_nonzero_when_member():
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="Læsø",
        is_church_member=True,
    )
    result = calculate_monthly_withholding(inp)
    assert result.church_tax > 0


def test_higher_municipal_tax_rate_means_lower_net_income():
    low_tax_municipality = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("35000"),
        municipality_name="København",  # 23.39%, lowest
    )
    high_tax_municipality = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("35000"),
        municipality_name="Læsø",  # 26.30%, one of the highest
    )
    low = calculate_monthly_withholding(low_tax_municipality)
    high = calculate_monthly_withholding(high_tax_municipality)
    assert low.net_income > high.net_income


def test_annual_and_monthly_are_related_but_not_identical():
    """Spec: annual and monthly are related but must not be treated as
    identical — rounding on 12 monthly calculations vs one annual
    calculation can differ by a small amount."""
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="Odense",
    )
    monthly = calculate_monthly_withholding(inp)
    annual = calculate_annual_tax(inp)

    assert annual.period == "annual"
    assert monthly.period == "monthly"
    assert annual.gross_income == monthly.gross_income * 12
    # Should be close (within rounding) but not necessarily bit-identical x12.
    assert abs(annual.net_income - monthly.net_income * 12) < Decimal("50")


def test_tax_card_mode_bypasses_bracket_calculation():
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="København",
        tax_card_mode=TaxCardMode.MY_TAX_CARD,
        tax_card_type=TaxCardType.HOVEDKORT,
        tax_card_percentage=Decimal("0.37"),
        tax_card_monthly_deduction=Decimal("4508"),
    )
    result = calculate_monthly_withholding(inp)
    assert result.calculation_basis is CalculationBasis.TAX_CARD
    assert result.bundskat == Decimal(0)
    assert result.municipal_tax == Decimal(0)
    assert result.state_tax_total > 0  # the withheld amount is still recorded


def test_standard_estimate_vs_tax_card_are_independent_paths():
    base_kwargs = dict(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="København",
    )
    standard = calculate_monthly_withholding(SalaryInput(**base_kwargs))
    tax_card = calculate_monthly_withholding(
        SalaryInput(
            **base_kwargs,
            tax_card_mode=TaxCardMode.MY_TAX_CARD,
            tax_card_type=TaxCardType.HOVEDKORT,
            tax_card_percentage=Decimal("0.37"),
            tax_card_monthly_deduction=Decimal("4508"),
        )
    )
    # Different calculation strategies can legitimately produce different
    # net figures; the important thing is they don't silently collapse to
    # the same code path.
    assert standard.calculation_basis != tax_card.calculation_basis


def test_unknown_municipality_raises():
    import pytest

    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="Not A Real Place",
    )
    with pytest.raises(ValueError):
        calculate_monthly_withholding(inp)
