# Phase 6 — Realistic validation examples

Run via `app/calculations/engine.calculate_monthly_withholding`, tax year 2026. All figures in DKK/month.

| Case | Gross | Net | Effective rate | Basis |
|---|---|---|---|---|
| 150 kr/h × 160h, Copenhagen, church member | 24,000 | 16,445 | 31.5% | standard estimate |
| 30,000 fixed, Vejle, not a church member | 30,000 | 20,317 | 32.3% | standard estimate |
| 30,000 fixed, Læsø (highest municipal+church rate), member | 30,000 | 19,522 | 34.9% | standard estimate |
| 45,000 fixed, Aarhus | 45,000 | 29,222 | 35.1% | standard estimate |
| 75,000 fixed, Odense (topskat territory, 900k/year) | 75,000 | 44,814 | 40.2% | standard estimate |
| 120 kr/h × 173h37m, Esbjerg (odd minutes) | 20,834 | 14,228 | 31.7% | standard estimate |
| 8,000 fixed, bikort 45%, Copenhagen | 8,000 | 3,998 | 50.0% | tax card |

Sanity checks performed:
- Net income is always positive and never exceeds gross, across the full test suite (`test_edge_cases.py`).
- A higher municipal/church tax rate (Læsø) produces a strictly lower net income than a lower-rate municipality (Copenhagen) for the same gross salary (`test_engine_integration.py::test_higher_municipal_tax_rate_means_lower_net_income`).
- Effective rates rise smoothly with income (31–35% for typical wages, crossing into the low 40s once topskat applies around 700–900k DKK/year), consistent with published expectations for the Danish system and in line with the ballpark figures quoted by third-party Danish salary calculators for comparable gross incomes — no attempt was made to match any one external calculator exactly, since this V1 standard estimate explicitly does not reproduce an individual's exact tax-card withholding (see docs/research_2026.md item 10).
- The bikort case's ~50% effective rate is consistent with the arithmetic: AM-bidrag (8%) + a 45% withholding rate applied to the AM-bidrag-reduced base ≈ 8% + 45% × 92% ≈ 49.4%, close to the observed 50.0% once ATP and rounding are included.
- Odd hours/minutes (173h37m) are converted to decimal hours correctly and produce a gross income that matches hourly_wage × decimal_hours exactly.

All 65 automated tests in `app/tests/` pass (`pytest app/tests/`), including the two worked examples from the spec, the 98-municipality data-validation suite, and bracket-boundary tests for every 2026 threshold.
