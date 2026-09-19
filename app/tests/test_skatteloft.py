"""Skatteloft (PSL 19): the combined rate of state personal-income tax plus
municipal tax is capped, tiered by band.

This was previously not enforced at all. The data file carried a note
claiming the ceiling could never be reached, but that note only added up the
state rates (12.01 + 7.5 + 7.5 + 5 = 32.01%) and forgot that the ceiling
covers municipal tax as well. With 2026 municipal rates running from 23.39%
to 26.30%, the ceiling binds for everyone above the mellemskat threshold in
any municipality above roughly 25.06%, which is 75 of the 98.
"""
from decimal import Decimal

import pytest

from app.calculations.engine import load_tax_rules
from app.calculations.tax import compute_state_tax

PERSONAL_ALLOWANCE = Decimal("54100")
HIGHEST_MUNICIPAL_RATE = Decimal("0.2630")   # Vordingborg / Svendborg / Vesthimmerlands
LOWEST_MUNICIPAL_RATE = Decimal("0.2339")    # København


@pytest.fixture
def rules():
    return load_tax_rules(2026)


def _marginal_combined_rate(personlig_indkomst, municipal_rate, rules):
    """Combined state + municipal rate on the next 1,000 kr of income."""
    brackets, loft = rules["state_tax_brackets"], rules["skatteloft"]
    lo = compute_state_tax(
        personlig_indkomst, PERSONAL_ALLOWANCE, brackets,
        municipal_rate=municipal_rate, skatteloft=loft,
    ).total
    hi = compute_state_tax(
        personlig_indkomst + 1000, PERSONAL_ALLOWANCE, brackets,
        municipal_rate=municipal_rate, skatteloft=loft,
    ).total
    return float((hi - lo) / 1000 + municipal_rate)


def test_ceiling_binds_in_the_topskat_band_for_a_high_tax_municipality(rules):
    combined = _marginal_combined_rate(Decimal("900000"), HIGHEST_MUNICIPAL_RATE, rules)
    assert combined == pytest.approx(0.5207, abs=1e-6)


def test_ceiling_does_not_bind_where_the_municipal_rate_is_low(rules):
    """København is below the rate where the ceiling starts to bite, so the
    full statutory rates apply and nothing is reduced."""
    combined = _marginal_combined_rate(Decimal("900000"), LOWEST_MUNICIPAL_RATE, rules)
    expected = float(
        Decimal("0.1201") + Decimal("0.075") + Decimal("0.075") + LOWEST_MUNICIPAL_RATE
    )
    assert combined == pytest.approx(expected, abs=1e-6)
    assert combined < 0.5207


def test_ceiling_binds_in_the_mellemskat_band(rules):
    combined = _marginal_combined_rate(Decimal("700000"), HIGHEST_MUNICIPAL_RATE, rules)
    assert combined == pytest.approx(0.4457, abs=1e-6)


def test_ceiling_binds_in_the_ekstra_topskat_band(rules):
    combined = _marginal_combined_rate(Decimal("3000000"), HIGHEST_MUNICIPAL_RATE, rules)
    assert combined == pytest.approx(0.5707, abs=1e-6)


def test_ordinary_earners_are_untouched_by_the_ceiling(rules):
    """Someone below the mellemskat threshold pays bundskat + municipal, which
    is far below the ceiling, so enforcing it must change nothing for them."""
    brackets, loft = rules["state_tax_brackets"], rules["skatteloft"]
    income = Decimal("350000")
    with_ceiling = compute_state_tax(
        income, PERSONAL_ALLOWANCE, brackets,
        municipal_rate=HIGHEST_MUNICIPAL_RATE, skatteloft=loft,
    ).total
    without_ceiling = compute_state_tax(income, PERSONAL_ALLOWANCE, brackets).total
    assert with_ceiling == without_ceiling


def test_all_three_ceiling_tiers_are_present_in_the_data(rules):
    loft = rules["skatteloft"]
    assert loft["mellemskat_band_rate"] == 0.4457
    assert loft["topskat_band_rate"] == 0.5207
    assert loft["ekstra_topskat_band_rate"] == 0.5707
