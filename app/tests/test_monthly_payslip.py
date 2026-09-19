"""Monthly-first default flow (product decision: no Hovedkort/Bikort/
Frikort or annual-tax understanding required for the main path).

Covers all three calculation-behavior cases from the spec:
1. deduction + percentage both given -> direct payslip-style withholding
2. deduction given, percentage blank -> percentage estimated from
   standard 2026 rules, clearly labelled as an estimate
3. deduction blank -> falls through to the existing standard estimate,
   completely unchanged (regression guard, not a new behavior)

test_matches_real_payslip_partial_period_example is a regression test
against a real DataLøn payslip (gross 1,050 / ATP 99 / AM-bidrag 76 on a
base of 951 / A-Indkomst 875 / A-skat 0 / net 875) that caught two bugs
in the original implementation: AM-bidrag was computed on gross income
instead of gross-minus-ATP, and the taxable-fradrag step never subtracted
ATP either. Both are fixed; the numeric expectations below for the
30,000 DKK examples were recomputed to match the corrected order.
"""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from api.main import app
from app.calculations.engine import calculate_monthly_withholding
from app.calculations.payslip import compute_payslip_withholding
from app.models.salary_input import IncomeType, SalaryInput, TaxCardMode, TaxCardType

client = TestClient(app)


# ---------------------------------------------------------------------
# app/calculations/payslip.py — pure function
# ---------------------------------------------------------------------


def test_payslip_withholding_follows_spec_order():
    result = compute_payslip_withholding(
        gross_income=Decimal("30000"),
        am_bidrag_amount=Decimal("2400"),
        monthly_deduction=Decimal("5207"),
        tax_percentage=Decimal("0.37"),
        atp_employee_contribution=Decimal("99"),
    )
    # taxable = gross - ATP - AM-bidrag - fradrag (ATP subtracted before
    # fradrag is applied, matching a real payslip's A-Indkomst step)
    assert result.taxable_after_fradrag == Decimal("30000") - Decimal("99") - Decimal("2400") - Decimal("5207")
    assert result.withheld_tax == result.taxable_after_fradrag * Decimal("0.37")
    expected_net = Decimal("30000") - Decimal("99") - Decimal("2400") - result.withheld_tax
    assert result.net_income == expected_net


def test_matches_real_payslip_partial_period_example():
    """Regression test against a real DataLøn payslip: 7 hours at 150
    DKK/hour, gross 1,050 kr, ATP 99, AM-bidrag base 951 (gross - ATP),
    AM-bidrag 76, fradrag consumed 875 (covers the whole A-Indkomst so
    A-skat is 0), net 875."""
    result = compute_payslip_withholding(
        gross_income=Decimal("1050"),
        am_bidrag_amount=(Decimal("1050") - Decimal("99")) * Decimal("0.08"),
        monthly_deduction=Decimal("875"),
        tax_percentage=Decimal("0.38"),
        atp_employee_contribution=Decimal("99"),
    )
    assert round(result.taxable_after_fradrag) == 0
    assert round(result.withheld_tax) == 0
    assert round(result.net_income) == 875


def test_payslip_taxable_floored_at_zero():
    result = compute_payslip_withholding(
        gross_income=Decimal("1000"),
        am_bidrag_amount=Decimal("80"),
        monthly_deduction=Decimal("5207"),  # bigger than what's left
        tax_percentage=Decimal("0.37"),
        atp_employee_contribution=Decimal("0"),
    )
    assert result.taxable_after_fradrag == Decimal(0)
    assert result.withheld_tax == Decimal(0)


# ---------------------------------------------------------------------
# Engine — case 1: deduction + percentage both given
# ---------------------------------------------------------------------


def test_case1_direct_payslip_withholding_matches_known_figures():
    salary_input = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="København",
        is_church_member=False,
        monthly_deduction=Decimal("5207"),
        tax_percentage=Decimal("0.37"),
    )
    result = calculate_monthly_withholding(salary_input)

    assert result.calculation_basis.value == "monthly_payslip"
    # AM-bidrag is 8% of (gross - ATP) = 8% of 29,901, matching real payslips
    assert result.am_bidrag == Decimal("2392")
    assert result.monthly_deduction_applied == Decimal("5207")
    assert result.taxable_income == Decimal("22302")
    assert result.tax_percentage_used == Decimal("0.37")
    assert result.tax_percentage_estimated is False
    assert result.atp_employee_contribution == Decimal("99")
    assert result.state_tax_total == Decimal("8252")
    assert result.net_income == Decimal("19257")
    # gross - total_tax must reconcile exactly with the displayed net figure
    assert result.gross_income - result.total_tax == result.net_income


# ---------------------------------------------------------------------
# Engine — case 2: deduction given, percentage blank
# ---------------------------------------------------------------------


def test_case2_estimates_percentage_from_standard_rules():
    standard_input = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="København",
        is_church_member=False,
    )
    standard_result = calculate_monthly_withholding(standard_input)

    payslip_input = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="København",
        is_church_member=False,
        monthly_deduction=Decimal("5207"),
    )
    result = calculate_monthly_withholding(payslip_input)

    assert result.calculation_basis.value == "monthly_payslip"
    assert result.tax_percentage_estimated is True
    assert any("estimated" in a.lower() for a in result.assumptions)

    # This deliberately does NOT assert equality with effective_tax_rate.
    # It used to, and that encoded a real bug: effective_tax_rate is total
    # tax (AM-bidrag and ATP included) over GROSS, but a trækprocent is
    # charged on income after AM-bidrag and after fradrag. Deriving a rate
    # on one base and applying it to a smaller one made the two flows
    # disagree for the same person and understated the tax.
    # A larger-than-standard fradrag must mean strictly less tax than the
    # standard estimate, never more.
    assert result.total_tax < standard_result.total_tax


def test_estimated_percentage_reproduces_the_standard_estimate_exactly():
    """The invariant the estimated trækprocent has to satisfy: a user whose
    monthly fradrag is just the standard personfradrag (54,100/12) must get
    the same answer as someone who left the fradrag blank. Before the
    derivation was fixed these two disagreed by over 100 kr/month for the
    same person."""
    common = dict(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("26850"),
        municipality_name="København",
        is_church_member=False,
    )
    standard = calculate_monthly_withholding(SalaryInput(**common))
    standard_personfradrag = Decimal("54100") / 12
    payslip = calculate_monthly_withholding(
        SalaryInput(**common, monthly_deduction=standard_personfradrag)
    )

    assert payslip.total_tax == standard.total_tax
    assert payslip.net_income == standard.net_income


def test_estimated_percentage_is_zero_when_income_is_below_the_allowance():
    """A short shift earns less than the monthly personfradrag, so no income
    tax is due and the estimated rate must be 0%. It previously came out as
    8%, which is the AM-bidrag rate leaking into the A-skat line and being
    shown to the user as their tax percentage."""
    result = calculate_monthly_withholding(
        SalaryInput(
            income_type=IncomeType.HOURLY_WAGE,
            hourly_wage=Decimal("150"),
            hours=7,
            minutes=0,
            municipality_name="København",
            is_church_member=False,
            monthly_deduction=Decimal("5207"),
        )
    )
    assert result.tax_percentage_used == Decimal(0)
    assert result.state_tax_total == Decimal(0)
    assert result.net_income == Decimal("966")


# ---------------------------------------------------------------------
# Engine — case 3: deduction blank -> existing standard estimate, unchanged
# ---------------------------------------------------------------------


def test_case3_falls_through_to_standard_estimate_unchanged():
    salary_input = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="København",
        is_church_member=False,
    )
    result = calculate_monthly_withholding(salary_input)
    assert result.calculation_basis.value == "standard_estimate"
    assert result.net_income == Decimal("20319")  # known-good reference figure


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------


def test_monthly_deduction_cannot_combine_with_tax_card_mode():
    with pytest.raises(ValueError, match="can't be combined"):
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("30000"),
            municipality_name="København",
            tax_card_mode=TaxCardMode.MY_TAX_CARD,
            tax_card_type=TaxCardType.HOVEDKORT,
            tax_card_percentage=Decimal("0.37"),
            tax_card_monthly_deduction=Decimal("5207"),
            monthly_deduction=Decimal("5207"),
        )


def test_negative_monthly_deduction_rejected():
    with pytest.raises(ValueError, match="can't be negative"):
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("30000"),
            municipality_name="København",
            monthly_deduction=Decimal("-1"),
        )


def test_tax_percentage_out_of_range_rejected():
    with pytest.raises(ValueError, match="between 0% and 100%"):
        SalaryInput(
            income_type=IncomeType.FIXED_SALARY,
            fixed_monthly_salary=Decimal("30000"),
            municipality_name="København",
            monthly_deduction=Decimal("5207"),
            tax_percentage=Decimal("1.5"),
        )


# ---------------------------------------------------------------------
# API layer
# ---------------------------------------------------------------------


def test_api_case1_round_trips_monthly_deduction_and_percentage():
    resp = client.post(
        "/calculate",
        json={
            "income_type": "fixed_salary",
            "fixed_monthly_salary": 30000,
            "municipality_name": "København",
            "monthly_deduction": 5207,
            "tax_percentage": 0.37,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["calculation_basis"] == "monthly_payslip"
    assert body["monthly_deduction_applied"] == 5207
    assert body["tax_percentage_used"] == 0.37
    assert body["tax_percentage_estimated"] is False
    labels = {line["label"] for line in body["breakdown"]}
    assert labels == {
        "Gross salary",
        "AM-bidrag",
        "Monthly fradrag",
        "Taxable after fradrag",
        "A-tax / withheld tax",
        "ATP",
        "Estimated net salary",
    }


def test_api_case2_flags_estimated_percentage():
    resp = client.post(
        "/calculate",
        json={
            "income_type": "fixed_salary",
            "fixed_monthly_salary": 30000,
            "municipality_name": "København",
            "monthly_deduction": 5207,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["calculation_basis"] == "monthly_payslip"
    assert body["tax_percentage_estimated"] is True
    assert body["tax_percentage_used"] is not None


def test_api_case3_no_deduction_uses_standard_estimate():
    resp = client.post(
        "/calculate",
        json={
            "income_type": "fixed_salary",
            "fixed_monthly_salary": 30000,
            "municipality_name": "København",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["calculation_basis"] == "standard_estimate"


def test_api_rejects_monthly_deduction_combined_with_tax_card_mode():
    resp = client.post(
        "/calculate",
        json={
            "income_type": "fixed_salary",
            "fixed_monthly_salary": 30000,
            "municipality_name": "København",
            "tax_card_mode": "my_tax_card",
            "tax_card_type": "hovedkort",
            "tax_card_percentage": 0.37,
            "tax_card_monthly_deduction": 5207,
            "monthly_deduction": 5207,
        },
    )
    assert resp.status_code == 422
    assert "can't be combined" in resp.json()["detail"][0]["msg"]


# ---------------------------------------------------------------------
# Simplified UI (2026-09-19 product decision): the frontend no longer
# collects a Hovedkort/Bikort withholding percentage for a second job.
# Instead it sends the plain-language "B-card / second job" choice as
# monthly_deduction=0 through the same simplified monthly-payslip flow
# an "A-card" with a fradrag uses, so the tax is estimated from the
# kommune/church/2026 rules with no fradrag applied. This is a contract
# test against that exact request shape, standing in for a frontend
# unit test since this repo has no JS test runner (see
# web/lib/municipalitySearch.test.mjs for the one piece of frontend
# logic that is pure enough to test directly with Node's built-in
# runner).
# ---------------------------------------------------------------------


def test_api_second_job_bcard_shape_estimates_without_fradrag():
    """The simplified "B-card / Second job" choice sends monthly_deduction=0
    (not omitted) and no tax_card_mode, so it estimates tax from the
    standard 2026 rules with no fradrag subtracted."""
    resp = client.post(
        "/calculate",
        json={
            "income_type": "fixed_salary",
            "fixed_monthly_salary": 15000,
            "municipality_name": "København",
            "is_church_member": False,
            "monthly_deduction": 0,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["calculation_basis"] == "monthly_payslip"
    assert body["tax_percentage_estimated"] is True
    assert body["monthly_deduction_applied"] in (0, None)
    # No fradrag was applied, so taxable income should equal gross minus
    # AM-bidrag (minus ATP, which is 0 for a fixed monthly salary here).
    assert body["taxable_income"] == pytest.approx(
        body["gross_income"] - body["am_bidrag"] - body["atp_employee_contribution"], abs=1
    )


# ---------------------------------------------------------------------
# ATP correction (2026-09-19): a short shift below the ATP bracket's
# first threshold (39 hours/month) must show ATP as 0, rule-based from
# app/data/atp_2026.json, never forced to match one employer's own
# payroll figure for a one-day trial shift. This exercises the full
# engine dispatch (not just the pure compute_payslip_withholding
# function above), with the exact numbers the user independently
# verified: 7 hours at 150 DKK/hour = 1,050 kr gross, AM-bidrag 8% of
# the full 1,050 (no ATP to subtract) = 84, and net 966 when the
# monthly fradrag entered is large enough to cover the rest, so A-skat
# is 0.
# ---------------------------------------------------------------------


def test_hourly_shift_below_atp_threshold_is_not_forced_to_a_fixed_value():
    salary_input = SalaryInput(
        income_type=IncomeType.HOURLY_WAGE,
        hourly_wage=Decimal("150"),
        hours=7,
        minutes=0,
        municipality_name="København",
        is_church_member=False,
        monthly_deduction=Decimal("966"),
    )
    result = calculate_monthly_withholding(salary_input)
    assert result.atp_employee_contribution == Decimal("0")
    assert result.am_bidrag == Decimal("84")
    assert result.taxable_income == Decimal("0")
    assert result.net_income == Decimal("966")
