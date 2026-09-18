from decimal import Decimal

from app.calculations.tax import compute_personlig_indkomst, compute_state_tax
from app.data_loader import load_tax_rules

RULES = load_tax_rules()
BRACKETS = RULES["state_tax_brackets"]
PERSONAL_ALLOWANCE = Decimal(str(RULES["personal_allowance"]["annual"]))


def test_income_below_personal_allowance_pays_no_bundskat():
    result = compute_state_tax(Decimal("50000"), PERSONAL_ALLOWANCE, BRACKETS)
    assert result.bundskat == Decimal(0)
    assert result.total == Decimal(0)


def test_bundskat_applies_only_above_personal_allowance():
    income = Decimal("100000")
    result = compute_state_tax(income, PERSONAL_ALLOWANCE, BRACKETS)
    expected_bund = (income - PERSONAL_ALLOWANCE) * Decimal(str(BRACKETS["bundskat"]["rate"]))
    assert result.bundskat == expected_bund
    # Not simply income * rate (the spec's "never flat % of gross" rule):
    assert result.bundskat != income * Decimal(str(BRACKETS["bundskat"]["rate"]))


def test_mellemskat_not_charged_below_threshold():
    threshold = Decimal(str(BRACKETS["mellemskat"]["threshold"]))
    result = compute_state_tax(threshold - Decimal("1"), PERSONAL_ALLOWANCE, BRACKETS)
    assert result.mellemskat == Decimal(0)


def test_mellemskat_charged_above_threshold():
    threshold = Decimal(str(BRACKETS["mellemskat"]["threshold"]))
    income = threshold + Decimal("10000")
    result = compute_state_tax(income, PERSONAL_ALLOWANCE, BRACKETS)
    expected = Decimal("10000") * Decimal(str(BRACKETS["mellemskat"]["rate"]))
    assert result.mellemskat == expected


def test_topskat_boundary():
    threshold = Decimal(str(BRACKETS["topskat"]["threshold"]))
    just_below = compute_state_tax(threshold, PERSONAL_ALLOWANCE, BRACKETS)
    just_above = compute_state_tax(threshold + Decimal("1"), PERSONAL_ALLOWANCE, BRACKETS)
    assert just_below.topskat == Decimal(0)
    assert just_above.topskat == Decimal("1") * Decimal(str(BRACKETS["topskat"]["rate"]))


def test_ekstra_topskat_only_for_very_high_income():
    threshold = Decimal(str(BRACKETS["ekstra_topskat"]["threshold"]))
    below = compute_state_tax(threshold - Decimal("1"), PERSONAL_ALLOWANCE, BRACKETS)
    above = compute_state_tax(threshold + Decimal("100000"), PERSONAL_ALLOWANCE, BRACKETS)
    assert below.ekstra_topskat == Decimal(0)
    assert above.ekstra_topskat == Decimal("100000") * Decimal(str(BRACKETS["ekstra_topskat"]["rate"]))


def test_all_brackets_stack_for_very_high_earner():
    """A very high earner should pay bund + mellem + top + ekstra-top
    simultaneously, each on its own slice."""
    income = Decimal(str(BRACKETS["ekstra_topskat"]["threshold"])) + Decimal("500000")
    result = compute_state_tax(income, PERSONAL_ALLOWANCE, BRACKETS)
    assert result.bundskat > 0
    assert result.mellemskat > 0
    assert result.topskat > 0
    assert result.ekstra_topskat > 0


def test_personlig_indkomst_is_am_base_minus_am_bidrag():
    am_base = Decimal("30000")
    am_bidrag = Decimal("2400")
    assert compute_personlig_indkomst(am_base, am_bidrag) == Decimal("27600")


def test_never_flat_percentage_of_gross():
    """Regression guard for the spec's explicit warning: state tax must
    never equal gross x a single flat rate."""
    gross = Decimal("40000")
    result = compute_state_tax(gross, PERSONAL_ALLOWANCE, BRACKETS)
    naive_flat_38pct = gross * Decimal("0.38")
    assert result.total != naive_flat_38pct
