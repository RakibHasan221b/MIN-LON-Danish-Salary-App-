# V1.2 implementation audit

Written after inspecting the current repository (file tree, `app/calculations/*`, `app/models/*`, `app/data/*.json`, `api/*`, `web/app/page.tsx`, `web/components/*`, and `app/tests/*`) — before any V1.2 code changes. 93 tests passing at the start of this task.

## What already works

- **Monthly Wage / Monthly Salary**: `app/models/salary_input.py` (`IncomeType`), `app/calculations/salary.py`. Both modes converge on one `gross_income` figure before anything else runs — confirmed in `engine._run`.
- **Gross income, tips**: `salary.compute_monthly_gross_income` returns the base; `engine._run` adds `tips` on top, scaled by period. `TaxResult.base_gross_income` / `.tips` / `.gross_income` already separate, per the V1.1 restoration.
- **ATP**: `app/calculations/atp.py`, data-driven from `atp_2026.json`, keyed by hours worked and pay frequency. Verified against two sources (documented in `research_2026.md` item 7).
- **AM-bidrag**: `app/calculations/am_bidrag.py` — flat 8% of `gross - ATP`, **no age handling at all today**. This is the main gap this task is meant to close.
- **Extra deduction**: `SalaryInput.extra_deduction`, subtracted from `skattepligtig_indkomst` (not `personlig_indkomst`) in `engine._standard_estimate` — correctly kept separate from the automatic personfradrag.
- **Employment allowance / job allowance**: `app/calculations/allowances.py`, both computed on `am_bidrag_base`, capped per `tax_rules_2026.json`.
- **State tax / municipal tax / church tax**: `app/calculations/tax.py` and `municipal_tax.py`, correctly implementing personlig-indkomst vs skattepligtig-indkomst bases (see `research_2026.md` item 9). Church tax is 0 unless `is_church_member`.
- **Standard Estimate / Hovedkort / Bikort**: `TaxCardMode` (standard_estimate vs my_tax_card) x `TaxCardType` (hovedkort vs bikort). `withholding.py` applies the user-supplied percentage directly; hovedkort subtracts a monthly deduction, bikort does not. Hovedkort and bikort cannot be selected simultaneously today because `tax_card_type` is a single enum field — this is already structurally impossible, not something that needs new validation.
- **Annual vs monthly**: `engine.calculate_annual_tax` / `calculate_monthly_withholding`, sharing all lower-level bracket/allowance functions via `_scaled_tax_rules` (annual constants used as-is; monthly constants divided by 12). The frontend currently **always requests `period: "monthly"`** — there is no user-facing annual/monthly toggle yet, even though the backend fully supports both.
- **Holiday pay**: `app/calculations/holiday_pay.py` — 12.5% feriegodtgørelse (hourly wage) / 1% ferietillæg (fixed salary), always a separate stream, never auto-added to ordinary net. Tax treatment uses a documented marginal-rate approximation (`research_2026.md` item 13a).
- **Total including holiday pay**: `TotalWithHolidayResult`, summed from the two independently-computed streams.
- **Currency conversion**: `api/currency.py`, keyless `open.er-api.com` fallback with an optional `CURRENCY_API_KEY`-gated keyed provider, `/exchange-rate/{currency}` endpoint, manual-rate fallback already in the frontend (`CurrencySection.tsx`). Correctly happens after the DKK calculation — the frontend only multiplies already-computed DKK figures.
- **Municipality data**: all 98, `MunicipalitySearch.tsx`, searchable.
- **Result breakdown**: `TaxResult.breakdown()` already hides zero-value rows (except a small always-show set) and separates gross/tips/allowances/tax lines — but the frontend (`ResultBreakdown.tsx`) currently renders this as two flat cards (top summary + one long breakdown list) rather than the three explicit levels (main result / main breakdown / expandable details) this task asks for.

## What is incomplete (before this task's changes)

1. **No age field anywhere** — not in `SalaryInput`, not in the API schema, not in the frontend. AM-bidrag is charged at a flat 8% regardless of age, which is factually wrong for 2026 (see `docs/research_2026.md` item 14, added by this task).
2. **No Frikort support** — `TaxCardType` only has `hovedkort` / `bikort`. Selecting a third card type is not possible today.
3. **No explicit annual/monthly toggle in the UI** — backend-ready, frontend doesn't expose it.
4. **Result screen is not organized into the three levels this task asks for.** Everything currently sits in one or two cards; there's no progressive disclosure (expandable "advanced" section).
5. **Validation messages are functional but written for developers, not end users** — e.g. `"hourly_wage and hours are required for Monthly Wage input"` is clear enough, but nothing currently validates age range, frikort-specific fields, or produces the plain-language error copy this task asks for (`"Please enter a valid income amount in DKK."` style).

## What should be changed (this task's scope)

- Add `age` to `SalaryInput` / API schema, thread it through `am_bidrag.py`, and use it to determine AM-bidrag exemption for under-18s (2026 rule, verified and documented — see research doc for the exact boundary and its limitation).
- Add `TaxCardType.FRIKORT` and a dedicated calculation path (`app/calculations/frikort.py`) with a `remaining_frikort_amount` input. Implement the well-verified case (income within the remaining balance → tax-free) correctly; for income that exceeds the balance, return a clear, actionable error rather than inventing a blended tax rate (see research doc item 15).
- Restructure the frontend result screen into the three explicit levels the task specifies, using `<details>`-based progressive disclosure for level 3.
- Add an explicit Annual / Monthly choice to the frontend, with the exact wording the task specifies.
- Broaden and simplify validation error text across `SalaryInput.__post_init__` and the Pydantic schema.
- Add `docs/tax_data_verification_checklist.md`.

## What must not be broken

- All 93 existing tests, and the underlying tax logic they lock in (bracket boundaries, ATP table, personlig-indkomst vs skattepligtig-indkomst split, tips/extra-deduction/holiday-pay/currency behavior). New fields (`age`, `remaining_frikort_amount`, new `TaxCardType.FRIKORT`) are added as optional/additive wherever possible so every existing caller (including all current tests) keeps working unchanged.
- The `CalculationBasis` distinction between standard estimate and tax-card modes — Frikort becomes a third, clearly distinct basis, never silently folded into `TAX_CARD` or `STANDARD_ESTIMATE`.
- The "never a flat % of gross" and "personal allowance vs extra deduction" invariants already covered by existing tests.
- The currency module's fail-safe behavior (DKK calculation must keep working even if the currency provider is down).

## Tax-rule uncertainty requiring verification

1. **AM-bidrag under-18 exemption — exact boundary.** Verified: the exemption runs "through the income year in which the person turns 17" — i.e. it is a whole-year rule keyed to whether the person turns 18 at any point during the tax year, not the person's age at the moment of calculation. A person who is 17 today but turns 18 later this year is **not** exempt for the full year, per the source consulted. This app only collects current age (an integer), not date of birth, so it **cannot** correctly implement the exact rule — it uses "age ≤ 17 → exempt" as a documented simplification that can over-exempt someone who turns 18 later in the same tax year. Flagged clearly in the UI and in `research_2026.md`, not silently assumed away.
2. **ATP eligibility by age** — not verified in this task. Danish ATP membership has historically had its own minimum-age rules distinct from the AM-bidrag age rule; this was not independently confirmed for 2026 within this task's research budget, so ATP is left unchanged (charged per the existing hours-based table regardless of age) and flagged as an open item in the verification checklist.
3. **Employment allowance / job allowance / personfradrag for minors** — no source found stating these differ for someone under 18; V1.2 assumes they apply unchanged. Documented as an assumption, not a verified fact.
4. **Frikort remaining-balance base** — not independently verified whether SKAT compares the frikort balance against gross A-indkomst or some AM-bidrag-adjusted figure. V1.2 compares against gross income and documents this as an assumption.
5. **Per-municipality tax-rate rows** — as already flagged in `research_2026.md` item 8, the 98-row table was validated against official aggregate statistics (min/max/average) but not row-by-row against the Ministry's own spreadsheet. See the new `docs/tax_data_verification_checklist.md` for the full per-source status.
