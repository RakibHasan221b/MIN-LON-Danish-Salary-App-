"""V1.2: age-based AM-bidrag exemption. See docs/research_2026.md item 14
for the verified rule and its documented age-only-input limitation."""
from decimal import Decimal

import pytest

from app.calculations.am_bidrag import compute_am_bidrag, is_exempt_by_age
from app.calculations.engine import calculate_monthly_withholding
from app.models.salary_input import IncomeType, SalaryInput


def test_is_exempt_by_age_under_18():
    assert is_exempt_by_age(17) is True
    assert is_exempt_by_age(10) is True
    assert is_exempt_by_age(0) is True


def test_is_exempt_by_age_adult():
    assert is_exempt_by_age(18) is False
    assert is_exempt_by_age(30) is False
    assert is_exempt_by_age(65) is False


def test_is_exempt_by_age_none_is_not_exempt():
    """Age not provided must NEVER be silently treated as exempt —
    default behaviour stays the adult (no exemption) case."""
    assert is_exempt_by_age(None) is False


def test_compute_am_bidrag_exempt_returns_zero():
    assert compute_am_bidrag(Decimal("10000"), Decimal("0.08"), exempt=True) == Decimal(0)


def test_compute_am_bidrag_not_exempt_unchanged():
    assert compute_am_bidrag(Decimal("10000"), Decimal("0.08"), exempt=False) == Decimal("800")


def test_engine_under_18_pays_no_am_bidrag():
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("10000"),
        municipality_name="København",
        age=16,
    )
    result = calculate_monthly_withholding(inp)
    assert result.am_bidrag == Decimal(0)
    assert result.age_am_bidrag_exempt is True
    assert any("AM-bidrag" in a for a in result.assumptions)


def test_engine_turning_18_this_year_still_flagged_as_simplified():
    """A person who states age 17 is exempt under this app's simplified
    rule, even though the verified rule (research_2026.md item 14) would
    only exempt them for the full year if they do NOT turn 18 during it.
    This test locks in the documented simplification, not the exact rule."""
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("10000"),
        municipality_name="København",
        age=17,
    )
    result = calculate_monthly_withholding(inp)
    assert result.am_bidrag == Decimal(0)
    assert result.age_am_bidrag_exempt is True


def test_engine_adult_pays_am_bidrag_normally():
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("10000"),
        municipality_name="København",
        age=25,
    )
    result = calculate_monthly_withholding(inp)
    assert result.am_bidrag > Decimal(0)
    assert result.age_am_bidrag_exempt is False


def test_engine_no_age_provided_defaults_to_adult_behaviour():
    """Not providing age must not be treated as exemption — this locks in
    the 'never hardcode/assume exemption silently' requirement."""
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("10000"),
        municipality_name="København",
    )
    result = calculate_monthly_withholding(inp)
    assert result.am_bidrag > Decimal(0)
    assert result.age_am_bidrag_exempt is False


def test_invalid_age_rejected():
    with pytest.raises(ValueError, match="realistic age"):
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("10000"),
            municipality_name="København",
            age=-1,
        )
    with pytest.raises(ValueError, match="realistic age"):
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("10000"),
            municipality_name="København",
            age=200,
        )
