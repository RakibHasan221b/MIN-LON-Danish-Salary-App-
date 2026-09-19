"""V1.2 API-layer tests: age and Frikort fields round-trip through the
FastAPI schema/endpoint, and the Frikort balance-exceeded error surfaces
as a clear 400, not a silent fallback."""
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_calculate_with_age_returns_am_bidrag_exempt_flag():
    resp = client.post(
        "/calculate",
        json={
            "income_type": "fixed_salary",
            "fixed_monthly_salary": 10000,
            "municipality_name": "København",
            "age": 16,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["age_am_bidrag_exempt"] is True
    assert body["am_bidrag"] == 0


def test_calculate_without_age_defaults_to_not_exempt():
    resp = client.post(
        "/calculate",
        json={
            "income_type": "fixed_salary",
            "fixed_monthly_salary": 10000,
            "municipality_name": "København",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["age_am_bidrag_exempt"] is False
    assert body["am_bidrag"] > 0


def test_calculate_frikort_within_balance():
    resp = client.post(
        "/calculate",
        json={
            "income_type": "fixed_salary",
            "fixed_monthly_salary": 5000,
            "municipality_name": "København",
            "tax_card_mode": "my_tax_card",
            "tax_card_type": "frikort",
            "remaining_frikort_amount": 10000,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["calculation_basis"] == "frikort"
    assert body["state_tax_total"] == 0
    assert body["remaining_frikort_amount"] == 10000


def test_calculate_frikort_exceeding_balance_returns_400_not_silent_fallback():
    resp = client.post(
        "/calculate",
        json={
            "income_type": "fixed_salary",
            "fixed_monthly_salary": 20000,
            "municipality_name": "København",
            "tax_card_mode": "my_tax_card",
            "tax_card_type": "frikort",
            "remaining_frikort_amount": 5000,
        },
    )
    assert resp.status_code == 400
    assert "B-card" in resp.json()["detail"]


def test_calculate_frikort_missing_amount_returns_422():
    resp = client.post(
        "/calculate",
        json={
            "income_type": "fixed_salary",
            "fixed_monthly_salary": 5000,
            "municipality_name": "København",
            "tax_card_mode": "my_tax_card",
            "tax_card_type": "frikort",
        },
    )
    assert resp.status_code == 422


def test_calculate_invalid_age_returns_422():
    resp = client.post(
        "/calculate",
        json={
            "income_type": "fixed_salary",
            "fixed_monthly_salary": 5000,
            "municipality_name": "København",
            "age": 500,
        },
    )
    assert resp.status_code == 422
