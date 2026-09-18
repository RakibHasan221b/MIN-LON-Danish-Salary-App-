from decimal import Decimal

import pytest

from app.calculations.atp import get_atp_employee_contribution


@pytest.mark.parametrize(
    "hours,expected",
    [
        (Decimal("117"), Decimal("99.00")),
        (Decimal("160"), Decimal("99.00")),
        (Decimal("116"), Decimal("66.00")),
        (Decimal("78"), Decimal("66.00")),
        (Decimal("77"), Decimal("33.00")),
        (Decimal("39"), Decimal("33.00")),
        (Decimal("38"), Decimal("0.00")),
        (Decimal("0"), Decimal("0.00")),
    ],
)
def test_monthly_atp_brackets(hours, expected):
    assert get_atp_employee_contribution(hours, "monthly") == expected


def test_atp_boundary_just_below_and_above_117():
    assert get_atp_employee_contribution(Decimal("116.99"), "monthly") == Decimal("66.00")
    assert get_atp_employee_contribution(Decimal("117.00"), "monthly") == Decimal("99.00")


def test_biweekly_brackets():
    assert get_atp_employee_contribution(Decimal("54"), "biweekly") == Decimal("52.20")
    assert get_atp_employee_contribution(Decimal("17"), "biweekly") == Decimal("0.00")


def test_weekly_brackets():
    assert get_atp_employee_contribution(Decimal("27"), "weekly") == Decimal("26.10")
    assert get_atp_employee_contribution(Decimal("8"), "weekly") == Decimal("0.00")


def test_unknown_pay_frequency_raises():
    with pytest.raises(ValueError):
        get_atp_employee_contribution(Decimal("100"), "daily")
