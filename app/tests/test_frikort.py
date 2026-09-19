"""V1.2: Frikort (tax-free card). See docs/research_2026.md item 15 and
app/calculations/frikort.py's module docstring for the exact scope: only
the well-verified "income within remaining balance" case is supported;
income that exceeds the balance is rejected with a clear error rather
than silently handled by another mode."""
from decimal import Decimal

import pytest

from app.calculations.frikort import (
    FrikortBalanceExceededError,
    compute_frikort_withholding,
)
from app.calculations.engine import calculate_monthly_withholding
from app.models.salary_input import IncomeType, SalaryInput, TaxCardMode, TaxCardType
from app.models.tax_result import CalculationBasis


def test_frikort_within_balance_is_tax_free():
    result = compute_frikort_withholding(
        gross_income=Decimal("5000"),
        atp_employee_contribution=Decimal("99"),
        am_bidrag=Decimal("400"),
        remaining_frikort_amount=Decimal("10000"),
    )
    assert result.withheld_tax == Decimal(0)
    assert result.withholding_base == Decimal("5000") - Decimal("99") - Decimal("400")


def test_frikort_exceeding_balance_raises_clear_error():
    with pytest.raises(FrikortBalanceExceededError, match="B-card"):
        compute_frikort_withholding(
            gross_income=Decimal("15000"),
            atp_employee_contribution=Decimal("99"),
            am_bidrag=Decimal("400"),
            remaining_frikort_amount=Decimal("10000"),
        )


def test_frikort_exact_balance_is_supported():
    """Boundary: income exactly equal to the remaining balance is the
    supported case (<=), not the exceeded case."""
    result = compute_frikort_withholding(
        gross_income=Decimal("10000"),
        atp_employee_contribution=Decimal("0"),
        am_bidrag=Decimal("0"),
        remaining_frikort_amount=Decimal("10000"),
    )
    assert result.withheld_tax == Decimal(0)


def test_salary_input_requires_remaining_frikort_amount():
    with pytest.raises(ValueError, match="Frikort amount"):
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("5000"),
            municipality_name="København",
            tax_card_mode=TaxCardMode.MY_TAX_CARD,
            tax_card_type=TaxCardType.FRIKORT,
        )


def test_salary_input_frikort_rejects_withholding_percentage():
    """Frikort must not be mixed with hovedkort/bikort-only fields — this
    guards against silently ignoring a percentage the user thinks applies."""
    with pytest.raises(ValueError, match="doesn't use a withholding percentage"):
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("5000"),
            municipality_name="København",
            tax_card_mode=TaxCardMode.MY_TAX_CARD,
            tax_card_type=TaxCardType.FRIKORT,
            remaining_frikort_amount=Decimal("10000"),
            tax_card_percentage=Decimal("0.37"),
        )


def test_engine_frikort_within_balance_end_to_end():
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("5000"),
        municipality_name="København",
        tax_card_mode=TaxCardMode.MY_TAX_CARD,
        tax_card_type=TaxCardType.FRIKORT,
        remaining_frikort_amount=Decimal("10000"),
    )
    result = calculate_monthly_withholding(inp)
    assert result.calculation_basis is CalculationBasis.FRIKORT
    assert result.state_tax_total == Decimal(0)
    assert result.municipal_tax == Decimal(0)
    assert result.church_tax == Decimal(0)
    assert result.am_bidrag > Decimal(0)  # AM-bidrag still applies under frikort
    assert result.net_income == result.gross_income - result.am_bidrag - result.atp_employee_contribution


def test_engine_frikort_exceeding_balance_raises_not_silently_falls_back():
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("20000"),
        municipality_name="København",
        tax_card_mode=TaxCardMode.MY_TAX_CARD,
        tax_card_type=TaxCardType.FRIKORT,
        remaining_frikort_amount=Decimal("5000"),
    )
    with pytest.raises(FrikortBalanceExceededError):
        calculate_monthly_withholding(inp)


def test_engine_frikort_with_age_exemption_stacks():
    """AM-bidrag age exemption and Frikort are independent — both can
    apply at once, and neither silently overrides the other."""
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("5000"),
        municipality_name="København",
        age=16,
        tax_card_mode=TaxCardMode.MY_TAX_CARD,
        tax_card_type=TaxCardType.FRIKORT,
        remaining_frikort_amount=Decimal("10000"),
    )
    result = calculate_monthly_withholding(inp)
    assert result.am_bidrag == Decimal(0)
    assert result.age_am_bidrag_exempt is True
    assert result.state_tax_total == Decimal(0)


def test_negative_remaining_frikort_amount_rejected():
    with pytest.raises(ValueError, match="can't be negative"):
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("5000"),
            municipality_name="København",
            tax_card_mode=TaxCardMode.MY_TAX_CARD,
            tax_card_type=TaxCardType.FRIKORT,
            remaining_frikort_amount=Decimal("-100"),
        )
