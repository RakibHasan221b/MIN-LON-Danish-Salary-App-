from decimal import Decimal

import pytest

from app.calculations.engine import calculate_monthly_withholding, round_dkk
from app.models.salary_input import IncomeType, SalaryInput


def test_zero_hours_zero_gross():
    inp = SalaryInput(
        income_type=IncomeType.HOURLY_WAGE,
        hourly_wage=Decimal("150"),
        hours=0,
        minutes=0,
        municipality_name="København",
    )
    result = calculate_monthly_withholding(inp)
    assert result.gross_income == Decimal(0)
    assert result.net_income == Decimal(0)
    assert result.effective_tax_rate == Decimal(0)  # guarded against div-by-zero


def test_very_low_income_below_personal_allowance_pays_no_state_tax():
    inp = SalaryInput(
        income_type=IncomeType.HOURLY_WAGE,
        hourly_wage=Decimal("150"),
        hours=10,
        municipality_name="København",
    )
    result = calculate_monthly_withholding(inp)
    assert result.bundskat == Decimal(0)
    assert result.mellemskat == Decimal(0)
    assert result.topskat == Decimal(0)


def test_very_high_income_triggers_all_brackets():
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("300000"),  # 3.6M/year, above ekstra-topskat
        municipality_name="København",
    )
    result = calculate_monthly_withholding(inp)
    assert result.bundskat > 0
    assert result.mellemskat > 0
    assert result.topskat > 0
    assert result.ekstra_topskat > 0
    assert result.net_income > 0


def test_net_income_never_exceeds_gross_income():
    for salary in (Decimal("0"), Decimal("5000"), Decimal("30000"), Decimal("500000")):
        inp = SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=salary,
            municipality_name="København",
        )
        result = calculate_monthly_withholding(inp)
        assert result.net_income <= result.gross_income


def test_net_income_never_negative_even_for_extreme_input():
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("10000000"),
        municipality_name="København",
    )
    result = calculate_monthly_withholding(inp)
    assert result.net_income >= Decimal(0)


def test_hourly_wage_with_odd_minutes():
    inp = SalaryInput(
        income_type=IncomeType.HOURLY_WAGE,
        hourly_wage=Decimal("175.50"),
        hours=37,
        minutes=45,
        municipality_name="Odense",
    )
    result = calculate_monthly_withholding(inp)
    # 37h45m = 37.75h x 175.50 = 6625.125
    assert result.gross_income == round_dkk(Decimal("175.50") * Decimal("37.75"))


def test_round_dkk_half_up():
    assert round_dkk(Decimal("100.50")) == Decimal("101")
    assert round_dkk(Decimal("100.49")) == Decimal("100")
    assert round_dkk(Decimal("100.4999")) == Decimal("100")


def test_municipality_lookup_is_case_insensitive():
    inp_lower = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="københavn",
    )
    result = calculate_monthly_withholding(inp_lower)
    assert result.municipality_name == "København"


def test_negative_salary_input_is_rejected_with_plain_language_error():
    """V1.2: SalaryInput itself now validates business-rule sanity (e.g. a
    negative salary) with a plain-language message, rather than deferring
    entirely to the API/UI layer — see docs/v1_2_implementation_audit.md
    section 10. A negative gross is rejected at construction time."""
    with pytest.raises(ValueError, match="valid monthly salary"):
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("-1000"),
            municipality_name="København",
        )
