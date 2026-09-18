"""Data-validation tests for municipalities_2026.json — required by the
spec: exactly 98 municipalities, unique names, every rate present,
numeric, and represented as a decimal."""
from app.data_loader import load_municipalities


def test_exactly_98_municipalities():
    assert len(load_municipalities()) == 98


def test_municipality_names_are_unique():
    names = [m["name"] for m in load_municipalities()]
    assert len(names) == len(set(names))


def test_every_municipality_has_required_fields():
    for m in load_municipalities():
        assert "name" in m and isinstance(m["name"], str) and m["name"]
        assert "municipal_tax_rate" in m
        assert "church_tax_rate" in m


def test_rates_are_numeric():
    for m in load_municipalities():
        assert isinstance(m["municipal_tax_rate"], (int, float))
        assert isinstance(m["church_tax_rate"], (int, float))


def test_rates_are_decimals_not_percent_literals():
    """23.39% must be stored as 0.2339, not 23.39."""
    for m in load_municipalities():
        assert 0 < m["municipal_tax_rate"] < 1, m["name"]
        assert 0 <= m["church_tax_rate"] < 1, m["name"]


def test_rates_within_plausible_range():
    for m in load_municipalities():
        assert 0.20 <= m["municipal_tax_rate"] <= 0.30, m["name"]
        assert 0.0 <= m["church_tax_rate"] <= 0.02, m["name"]


def test_known_extremes_match_official_aggregate_stats():
    """Cross-check against the official svmn.dk aggregate figures cited
    in docs/research_2026.md item 8: lowest 23.39% (Copenhagen), highest
    26.30%."""
    rates = {m["name"]: m["municipal_tax_rate"] for m in load_municipalities()}
    assert min(rates.values()) == 0.2339
    assert rates["København"] == 0.2339
    assert max(rates.values()) == 0.263


def test_every_municipality_has_a_code():
    for m in load_municipalities():
        assert m.get("municipality_code"), m["name"]
