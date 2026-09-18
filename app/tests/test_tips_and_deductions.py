from decimal import Decimal

from app.calculations.engine import calculate_monthly_withholding
from app.models.salary_input import IncomeType, SalaryInput


def test_tips_are_added_to_gross_before_tax_not_after():
    without_tips = calculate_monthly_withholding(
        SalaryInput(
            income_type=IncomeType.HOURLY_WAGE,
            hourly_wage=Decimal("150"),
            hours=160,
            municipality_name="København",
        )
    )
    with_tips = calculate_monthly_withholding(
        SalaryInput(
            income_type=IncomeType.HOURLY_WAGE,
            hourly_wage=Decimal("150"),
            hours=160,
            municipality_name="København",
            tips=Decimal("2000"),
        )
    )
    assert with_tips.gross_income == without_tips.gross_income + Decimal("2000")
    # Net should NOT simply be old_net + 2000 (tips get taxed too, unlike
    # the old app's naive after-tax addition would never have done since
    # the old app didn't support tips-after-tax either, but this guards
    # against a regression to that pattern).
    assert with_tips.net_income < without_tips.net_income + Decimal("2000")
    assert with_tips.net_income > without_tips.net_income


def test_base_gross_and_tips_reported_separately():
    result = calculate_monthly_withholding(
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("30000"),
            municipality_name="København",
            tips=Decimal("1500"),
        )
    )
    assert result.base_gross_income == Decimal("30000")
    assert result.tips == Decimal("1500")
    assert result.gross_income == Decimal("31500")


def test_tips_feed_atp_and_am_bidrag_base():
    """Tips are taxable A-income, so they increase the AM-bidrag base."""
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
    assert with_tips.am_bidrag > without_tips.am_bidrag


def test_extra_deduction_reduces_net_tax():
    without_deduction = calculate_monthly_withholding(
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("30000"),
            municipality_name="København",
        )
    )
    with_deduction = calculate_monthly_withholding(
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("30000"),
            municipality_name="København",
            extra_deduction=Decimal("1000"),
        )
    )
    assert with_deduction.net_income > without_deduction.net_income
    # Only municipal/church tax base should move — state tax (personlig
    # indkomst based) must be identical, since extra_deduction only
    # reduces skattepligtig indkomst, never personlig indkomst.
    assert with_deduction.bundskat == without_deduction.bundskat
    assert with_deduction.municipal_tax < without_deduction.municipal_tax


def test_extra_deduction_does_not_duplicate_personal_allowance():
    """A small extra_deduction must not zero out municipal tax by itself
    — it should stack on top of, not replace, the automatic personfradrag."""
    result = calculate_monthly_withholding(
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("30000"),
            municipality_name="København",
            extra_deduction=Decimal("100"),
        )
    )
    assert result.municipal_tax > 0
