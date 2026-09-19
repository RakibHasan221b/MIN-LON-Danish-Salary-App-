"""Currency conversion — backend-only, so the API key (if any) never
reaches the frontend. See docs/research_2026.md item 13b.

Two providers:
- No-key fallback (default): open.er-api.com — free, keyless, confirmed
  to serve DKK-based rates for USD/EUR/BDT.
- Optional keyed provider: if CURRENCY_API_KEY is set in the environment,
  currencyfreaks.com is used instead (the old app's provider, but with
  the key read from the environment rather than hardcoded in source).

If both fail, callers get a CurrencyUnavailableError and the frontend
falls back to a manual exchange-rate entry — the DKK calculation itself
never depends on this module succeeding.
"""
from __future__ import annotations

import os
import time
from decimal import Decimal

import requests

# Every EU and EEA currency, plus the currencies most commonly wanted by
# people working in Denmark and sending money home. open.er-api.com returns
# a full DKK-based rates table, so anything listed here resolves from the
# same single request the three original currencies used.
SUPPORTED_CURRENCY_NAMES: dict[str, str] = {
    # Euro area and the rest of the EU
    "EUR": "Euro",
    "BGN": "Bulgarian lev",
    "CZK": "Czech koruna",
    "HUF": "Hungarian forint",
    "PLN": "Polish złoty",
    "RON": "Romanian leu",
    "SEK": "Swedish krona",
    # Rest of the EEA, plus Switzerland and the UK
    "NOK": "Norwegian krone",
    "ISK": "Icelandic króna",
    "CHF": "Swiss franc",
    "GBP": "British pound",
    # Widely used elsewhere
    "USD": "US dollar",
    "CAD": "Canadian dollar",
    "AUD": "Australian dollar",
    "NZD": "New Zealand dollar",
    "JPY": "Japanese yen",
    "CNY": "Chinese yuan",
    "HKD": "Hong Kong dollar",
    "SGD": "Singapore dollar",
    "KRW": "South Korean won",
    "INR": "Indian rupee",
    "BDT": "Bangladeshi taka",
    "PKR": "Pakistani rupee",
    "LKR": "Sri Lankan rupee",
    "NPR": "Nepalese rupee",
    "IDR": "Indonesian rupiah",
    "MYR": "Malaysian ringgit",
    "PHP": "Philippine peso",
    "THB": "Thai baht",
    "VND": "Vietnamese dong",
    "TRY": "Turkish lira",
    "UAH": "Ukrainian hryvnia",
    "RUB": "Russian ruble",
    "AED": "UAE dirham",
    "SAR": "Saudi riyal",
    "ILS": "Israeli shekel",
    "EGP": "Egyptian pound",
    "MAD": "Moroccan dirham",
    "NGN": "Nigerian naira",
    "KES": "Kenyan shilling",
    "GHS": "Ghanaian cedi",
    "ZAR": "South African rand",
    "BRL": "Brazilian real",
    "MXN": "Mexican peso",
    "ARS": "Argentine peso",
    "COP": "Colombian peso",
    "CLP": "Chilean peso",
}

SUPPORTED_CURRENCIES = set(SUPPORTED_CURRENCY_NAMES)

_CACHE_TTL_SECONDS = 600
_cache: dict[str, tuple[float, Decimal, str]] = {}  # currency -> (fetched_at, rate, source)


class CurrencyUnavailableError(Exception):
    pass


def _fetch_via_open_er_api(currency: str) -> Decimal:
    resp = requests.get("https://open.er-api.com/v6/latest/DKK", timeout=5)
    resp.raise_for_status()
    data = resp.json()
    if data.get("result") != "success":
        raise CurrencyUnavailableError("open.er-api.com did not return a successful result")
    rate = data.get("rates", {}).get(currency)
    if rate is None:
        raise CurrencyUnavailableError(f"open.er-api.com did not return a rate for {currency}")
    return Decimal(str(rate))


def _fetch_via_currencyfreaks(currency: str, api_key: str) -> Decimal:
    url = "https://api.currencyfreaks.com/latest"
    resp = requests.get(
        url, params={"apikey": api_key, "symbols": f"DKK,{currency}"}, timeout=5
    )
    resp.raise_for_status()
    data = resp.json()
    rates = data.get("rates", {})
    dkk_per_usd = rates.get("DKK")
    target_per_usd = rates.get(currency) if currency != "USD" else "1"
    if dkk_per_usd is None or target_per_usd is None:
        raise CurrencyUnavailableError("currencyfreaks.com response missing required rates")
    # rates are USD-based: 1 USD = dkk_per_usd DKK = target_per_usd <currency>
    # -> 1 DKK = (target_per_usd / dkk_per_usd) <currency>
    return Decimal(str(target_per_usd)) / Decimal(str(dkk_per_usd))


def get_exchange_rate(currency: str) -> tuple[Decimal, str]:
    """Returns (rate, source_label) for 1 DKK -> `currency`. Raises
    CurrencyUnavailableError if no provider succeeds. Cached in-memory for
    a few minutes to avoid hammering the provider on every /calculate."""
    currency = currency.upper()
    if currency not in SUPPORTED_CURRENCIES:
        raise ValueError(f"Unsupported currency: {currency}. Supported: {SUPPORTED_CURRENCIES}")

    cached = _cache.get(currency)
    if cached and (time.time() - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1], cached[2]

    api_key = os.environ.get("CURRENCY_API_KEY")
    errors = []

    if api_key:
        try:
            rate = _fetch_via_currencyfreaks(currency, api_key)
            _cache[currency] = (time.time(), rate, "currencyfreaks.com")
            return rate, "currencyfreaks.com"
        except Exception as exc:  # noqa: BLE001 — fall through to the free provider
            errors.append(f"currencyfreaks.com: {exc}")

    try:
        rate = _fetch_via_open_er_api(currency)
        _cache[currency] = (time.time(), rate, "open.er-api.com")
        return rate, "open.er-api.com"
    except Exception as exc:  # noqa: BLE001
        errors.append(f"open.er-api.com: {exc}")

    raise CurrencyUnavailableError("; ".join(errors))
