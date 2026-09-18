from decimal import Decimal

from app.calculations.allowances import compute_employment_allowance, compute_job_allowance
from app.data_loader import load_tax_rules

RULES = load_tax_rules()
EMP = RULES["employment_allowance"]
JOB = RULES["job_allowance"]


def test_employment_allowance_percentage_below_cap():
    base = Decimal("100000")
    result = compute_employment_allowance(
        base, Decimal(str(EMP["rate"])), Decimal(str(EMP["max_annual"]))
    )
    assert result == base * Decimal(str(EMP["rate"]))


def test_employment_allowance_capped_at_max():
    base = Decimal("1000000")  # well above the point the cap kicks in
    result = compute_employment_allowance(
        base, Decimal(str(EMP["rate"])), Decimal(str(EMP["max_annual"]))
    )
    assert result == Decimal(str(EMP["max_annual"]))


def test_job_allowance_zero_below_floor():
    base = Decimal(str(JOB["floor_annual"])) - Decimal("1")
    result = compute_job_allowance(
        base,
        Decimal(str(JOB["rate"])),
        Decimal(str(JOB["floor_annual"])),
        Decimal(str(JOB["max_annual"])),
    )
    assert result == Decimal(0)


def test_job_allowance_percentage_of_excess_above_floor():
    base = Decimal(str(JOB["floor_annual"])) + Decimal("10000")
    result = compute_job_allowance(
        base,
        Decimal(str(JOB["rate"])),
        Decimal(str(JOB["floor_annual"])),
        Decimal(str(JOB["max_annual"])),
    )
    assert result == Decimal("10000") * Decimal(str(JOB["rate"]))


def test_job_allowance_capped_at_max():
    base = Decimal("2000000")
    result = compute_job_allowance(
        base,
        Decimal(str(JOB["rate"])),
        Decimal(str(JOB["floor_annual"])),
        Decimal(str(JOB["max_annual"])),
    )
    assert result == Decimal(str(JOB["max_annual"]))
