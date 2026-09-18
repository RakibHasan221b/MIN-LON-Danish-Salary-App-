"""V1.2 section 10: plain-language validation errors, and hovedkort vs
bikort producing genuinely different results (not just different labels)."""
from decimal import Decimal

import pytest

from app.calculations.engine import calculate_monthly_withholding
from app.models.salary_input import IncomeType, SalaryInput, TaxCardMode, TaxCardType


def test_missing_income_fields_message_is_plain_language():
    with pytest.raises(ValueError, match="Please enter your fixed monthly salary"):
        SalaryInput(income_type=IncomeType.FIXED_SALARY, municipality_name="København")


def test_missing_hourly_fields_message_is_plain_language():
    with pytest.raises(ValueError, match="Please enter your hourly wage and hours worked"):
        SalaryInput(income_type=IncomeType.HOURLY_WAGE, municipality_name="København")


def test_negative_tips_rejected_plain_language():
    with pytest.raises(ValueError, match="Tips can't be negative"):
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("10000"),
            municipality_name="København",
            tips=Decimal("-1"),
        )


def test_negative_extra_deduction_rejected_plain_language():
    with pytest.raises(ValueError, match="Additional deduction can't be negative"):
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("10000"),
            municipality_name="København",
            extra_deduction=Decimal("-1"),
        )


def test_withholding_percentage_out_of_range_rejected():
    with pytest.raises(ValueError, match="between 0% and 100%"):
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("10000"),
            municipality_name="København",
            tax_card_mode=TaxCardMode.MY_TAX_CARD,
            tax_card_type=TaxCardType.BIKORT,
            tax_card_percentage=Decimal("1.5"),
        )


def test_negative_monthly_deduction_rejected():
    with pytest.raises(ValueError, match="Monthly deduction can't be negative"):
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("10000"),
            municipality_name="København",
            tax_card_mode=TaxCardMode.MY_TAX_CARD,
            tax_card_type=TaxCardType.HOVEDKORT,
            tax_card_percentage=Decimal("0.37"),
            tax_card_monthly_deduction=Decimal("-1"),
        )


def test_hovedkort_and_bikort_are_mutually_exclusive_by_construction():
    """tax_card_type is a single enum field, so a request can never select
    both at once — this is structural, not something extra validation
    needs to enforce."""
    hovedkort = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="København",
        tax_card_mode=TaxCardMode.MY_TAX_CARD,
        tax_card_type=TaxCardType.HOVEDKORT,
        tax_card_percentage=Decimal("0.37"),
        tax_card_monthly_deduction=Decimal("4508"),
    )
    assert hovedkort.tax_card_type is TaxCardType.HOVEDKORT
    assert hovedkort.tax_card_type is not TaxCardType.BIKORT


def test_hovedkort_and_bikort_produce_different_withheld_tax():
    base_kwargs = dict(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="København",
        tax_card_mode=TaxCardMode.MY_TAX_CARD,
        tax_card_percentage=Decimal("0.37"),
    )
    hovedkort = calculate_monthly_withholding(
        SalaryInput(**base_kwargs, tax_card_type=TaxCardType.HOVEDKORT, tax_card_monthly_deduction=Decimal("4508"))
    )
    bikort = calculate_monthly_withholding(
        SalaryInput(**base_kwargs, tax_card_type=TaxCardType.BIKORT)
    )
    # Hovedkort subtracts a monthly fradrag before applying the
    # percentage; bikort does not — so the withheld tax must differ.
    assert hovedkort.state_tax_total != bikort.state_tax_total
    assert hovedkort.net_income > bikort.net_income
