from decimal import Decimal
from unittest.mock import patch

import pytest

from api.currency import CurrencyUnavailableError, get_exchange_rate, _cache


@pytest.fixture(autouse=True)
def clear_cache():
    _cache.clear()
    yield
    _cache.clear()


def test_unsupported_currency_raises_value_error():
    with pytest.raises(ValueError):
        get_exchange_rate("GBP")


def test_no_key_provider_used_when_env_var_unset(monkeypatch):
    monkeypatch.delenv("CURRENCY_API_KEY", raising=False)
    with patch("api.currency._fetch_via_open_er_api", return_value=Decimal("0.134")) as mock_fetch:
        rate, source = get_exchange_rate("EUR")
    assert rate == Decimal("0.134")
    assert source == "open.er-api.com"
    mock_fetch.assert_called_once()


def test_keyed_provider_used_when_env_var_set(monkeypatch):
    monkeypatch.setenv("CURRENCY_API_KEY", "test-key-not-real")
    with patch("api.currency._fetch_via_currencyfreaks", return_value=Decimal("0.135")) as mock_keyed:
        with patch("api.currency._fetch_via_open_er_api") as mock_fallback:
            rate, source = get_exchange_rate("EUR")
    assert rate == Decimal("0.135")
    assert source == "currencyfreaks.com"
    mock_keyed.assert_called_once()
    mock_fallback.assert_not_called()


def test_falls_back_to_no_key_provider_if_keyed_provider_fails(monkeypatch):
    monkeypatch.setenv("CURRENCY_API_KEY", "test-key-not-real")
    with patch("api.currency._fetch_via_currencyfreaks", side_effect=Exception("boom")):
        with patch("api.currency._fetch_via_open_er_api", return_value=Decimal("0.134")) as mock_fallback:
            rate, source = get_exchange_rate("EUR")
    assert source == "open.er-api.com"
    mock_fallback.assert_called_once()


def test_raises_currency_unavailable_when_all_providers_fail(monkeypatch):
    monkeypatch.delenv("CURRENCY_API_KEY", raising=False)
    with patch("api.currency._fetch_via_open_er_api", side_effect=Exception("network down")):
        with pytest.raises(CurrencyUnavailableError):
            get_exchange_rate("USD")


def test_result_is_cached_and_provider_not_called_twice(monkeypatch):
    monkeypatch.delenv("CURRENCY_API_KEY", raising=False)
    with patch("api.currency._fetch_via_open_er_api", return_value=Decimal("18.9")) as mock_fetch:
        get_exchange_rate("BDT")
        get_exchange_rate("BDT")
    assert mock_fetch.call_count == 1


def test_api_endpoint_returns_503_with_clear_message_when_unavailable():
    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)
    with patch("api.main.get_exchange_rate", side_effect=CurrencyUnavailableError("down")):
        resp = client.get("/exchange-rate/EUR")
    assert resp.status_code == 503
    assert "temporarily unavailable" in resp.json()["detail"].lower()


def test_api_endpoint_returns_rate_on_success():
    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)
    with patch("api.main.get_exchange_rate", return_value=(Decimal("0.134"), "open.er-api.com")):
        resp = client.get("/exchange-rate/EUR")
    assert resp.status_code == 200
    body = resp.json()
    assert body["currency"] == "EUR"
    assert body["rate"] == pytest.approx(0.134)


def test_dkk_salary_calculation_unaffected_by_currency_failure():
    """The main /calculate endpoint must work regardless of currency
    provider state — currency conversion is a separate, optional call."""
    from decimal import Decimal as D

    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)
    with patch("api.currency._fetch_via_open_er_api", side_effect=Exception("down")):
        resp = client.post(
            "/calculate",
            json={
                "income_type": "fixed_salary",
                "fixed_monthly_salary": 30000,
                "municipality_name": "København",
            },
        )
    assert resp.status_code == 200
    assert resp.json()["gross_income"] == 30000.0
