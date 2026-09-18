"""Integration tests verifying the COMPLETE result object — per the
V1.1 spec's requirement #16: gross, tax breakdown, net, holiday pay and
total-with-holiday must all be present and internally consistent for
both spec examples."""
from decimal import Decimal

from app.calculations.engine import calculate_monthly_withholding
from app.models.salary_input import IncomeType, SalaryInput


def _assert_complete_result(result):
    assert result.gross_income > 0
    assert result.net_income > 0
    assert result.net_income < result.gross_income
    assert result.total_tax > 0
    assert result.total_tax == result.gross_income - result.net_income

    # Holiday pay block present and internally consistent
    hp = result.holiday_pay
    assert hp is not None
    assert hp.gross > 0
    assert hp.net == hp.gross - hp.am_bidrag - hp.income_tax

    # Total-with-holiday block present and consistent with the two streams
    twh = result.total_with_holiday
    assert twh is not None
    assert twh.gross == result.gross_income + hp.gross
    assert twh.net == result.net_income + hp.net


def test_monthly_wage_150_x_160_complete_result():
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
    _assert_complete_result(result)


def test_monthly_salary_30000_complete_result():
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="Aarhus",
        is_church_member=False,
    )
    result = calculate_monthly_withholding(inp)
    assert result.gross_income == Decimal("30000")
    _assert_complete_result(result)


def test_folkekirken_yes_includes_church_tax():
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="Odense",
        is_church_member=True,
    )
    result = calculate_monthly_withholding(inp)
    assert result.church_tax > 0


def test_folkekirken_no_zero_church_tax():
    inp = SalaryInput(
        income_type=IncomeType.FIXED_SALARY,
        fixed_monthly_salary=Decimal("30000"),
        municipality_name="Odense",
        is_church_member=False,
    )
    result = calculate_monthly_withholding(inp)
    assert result.church_tax == Decimal(0)


def test_api_full_result_shape_for_both_income_modes():
    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)

    for payload in (
        {
            "income_type": "hourly_wage",
            "hourly_wage": 150,
            "hours": 160,
            "minutes": 0,
            "municipality_name": "København",
            "is_church_member": True,
        },
        {
            "income_type": "fixed_salary",
            "fixed_monthly_salary": 30000,
            "municipality_name": "Aarhus",
            "is_church_member": False,
        },
    ):
        resp = client.post("/calculate", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        for key in (
            "gross_income",
            "base_gross_income",
            "tips",
            "atp_employee_contribution",
            "am_bidrag",
            "state_tax_total",
            "municipal_tax",
            "church_tax",
            "other_adjustments",
            "total_tax",
            "net_income",
            "holiday_pay",
            "total_with_holiday",
        ):
            assert key in body, f"missing {key} for {payload['income_type']}"
        assert set(body["holiday_pay"]) >= {"rate_label", "gross", "am_bidrag", "income_tax", "net"}
        assert set(body["total_with_holiday"]) >= {"gross", "tax", "net"}
