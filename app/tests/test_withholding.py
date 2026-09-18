from decimal import Decimal

from app.calculations.withholding import compute_tax_card_withholding
from app.models.salary_input import TaxCardType


def test_hovedkort_applies_monthly_deduction():
    result = compute_tax_card_withholding(
        gross_income=Decimal("30000"),
        atp_employee_contribution=Decimal("99"),
        am_bidrag=Decimal("2392"),
        tax_card_percentage=Decimal("0.37"),
        tax_card_type=TaxCardType.HOVEDKORT,
        tax_card_monthly_deduction=Decimal("4508"),
    )
    expected_base = Decimal("30000") - Decimal("99") - Decimal("2392") - Decimal("4508")
    assert result.withholding_base == expected_base
    assert result.withheld_tax == expected_base * Decimal("0.37")


def test_bikort_applies_no_deduction():
    result = compute_tax_card_withholding(
        gross_income=Decimal("10000"),
        atp_employee_contribution=Decimal("0"),
        am_bidrag=Decimal("800"),
        tax_card_percentage=Decimal("0.45"),
        tax_card_type=TaxCardType.BIKORT,
        tax_card_monthly_deduction=Decimal("4508"),  # must be ignored for bikort
    )
    expected_base = Decimal("10000") - Decimal("800")
    assert result.withholding_base == expected_base
    assert result.withheld_tax == expected_base * Decimal("0.45")


def test_withholding_base_never_negative():
    result = compute_tax_card_withholding(
        gross_income=Decimal("1000"),
        atp_employee_contribution=Decimal("99"),
        am_bidrag=Decimal("80"),
        tax_card_percentage=Decimal("0.37"),
        tax_card_type=TaxCardType.HOVEDKORT,
        tax_card_monthly_deduction=Decimal("4508"),
    )
    assert result.withholding_base == Decimal(0)
    assert result.withheld_tax == Decimal(0)
