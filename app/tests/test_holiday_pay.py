from decimal import Decimal

from app.calculations.engine import calculate_monthly_withholding
from app.models.salary_input import (
    IncomeType,
    SalaryInput,
    TaxCardMode,
    TaxCardType,
)


def test_hourly_wage_uses_feriegodtgorelse_125_percent():
    inp = SalaryInput(
        income_type=IncomeType.HOURLY_WAGE,
        hourly_wage=Decimal("150"),
        hours=160,
        municipality_name="København",
    )
    result = calculate_monthly_withholding(inp)
    assert result.holiday_pay.rate_used == Decimal("0.125")
    assert result.holiday_pay.gross == Decimal(round(24000 * Decimal("0.125")))


def test_fixed_salary_uses_ferietillaeg_1_percent():
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="København",
    )
    result = calculate_monthly_withholding(inp)
    assert result.holiday_pay.rate_used == Decimal("0.01")
    assert result.holiday_pay.gross == Decimal(round(30000 * Decimal("0.01")))


def test_holiday_pay_includes_tips_in_its_base():
    without_tips = calculate_monthly_withholding(
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("30000"),
            municipality_name="København",
        )
    )
    with_tips = calculate_monthly_withholding(
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("30000"),
            municipality_name="København",
            tips=Decimal("1000"),
        )
    )
    assert with_tips.holiday_pay.gross > without_tips.holiday_pay.gross


def test_holiday_pay_is_never_added_to_ordinary_net_automatically():
    """Ordinary net_income must not already include holiday pay."""
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="København",
    )
    result = calculate_monthly_withholding(inp)
    assert result.net_income != result.total_with_holiday.net
    assert result.net_income + result.holiday_pay.net == result.total_with_holiday.net


def test_holiday_pay_has_no_atp():
    inp = SalaryInput(
        income_type=IncomeType.HOURLY_WAGE,
        hourly_wage=Decimal("150"),
        hours=160,
        municipality_name="København",
    )
    result = calculate_monthly_withholding(inp)
    # Holiday pay gross - am_bidrag - income_tax should equal net (no ATP line subtracted)
    hp = result.holiday_pay
    assert hp.gross - hp.am_bidrag - hp.income_tax == hp.net


def test_total_with_holiday_sums_without_double_counting():
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="Odense",
        is_church_member=True,
    )
    result = calculate_monthly_withholding(inp)
    twh = result.total_with_holiday
    assert twh.gross == result.gross_income + result.holiday_pay.gross
    assert twh.net == result.net_income + result.holiday_pay.net
    expected_tax = result.total_tax + result.holiday_pay.am_bidrag + result.holiday_pay.income_tax
    assert twh.tax == expected_tax


def test_holiday_pay_marginal_rate_includes_municipal_and_church():
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="København",
        is_church_member=True,
    )
    result = calculate_monthly_withholding(inp)
    # marginal rate should be at least bund + municipal + church (no mellem/top at this income)
    assert result.holiday_pay.marginal_rate_applied >= Decimal("0.35")
    assert result.holiday_pay.marginal_rate_applied < Decimal("0.40")


def test_holiday_pay_in_tax_card_mode_uses_card_percentage_directly():
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
    assert result.holiday_pay.marginal_rate_applied == Decimal("0.37")


def test_higher_ordinary_income_raises_holiday_pay_marginal_rate():
    low = calculate_monthly_withholding(
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("30000"),
            municipality_name="København",
        )
    )
    high = calculate_monthly_withholding(
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("100000"),  # into topskat territory
            municipality_name="København",
        )
    )
    assert high.holiday_pay.marginal_rate_applied > low.holiday_pay.marginal_rate_applied
