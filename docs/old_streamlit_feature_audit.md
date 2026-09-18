# Old Streamlit app — feature audit

Source: the Streamlit `.py` file the user pasted in chat (2026-09-18), single-file app, no other modules. Read in full before this table was built — nothing here is guessed.

Old app's calculation logic (for reference, all being replaced): total hours rounded to nearest quarter-hour; `base_gross_salary = total_hours × hourly_rate`; `gross_salary = base_gross_salary + tip`; ATP via the same fixed DKK table we already verified; `am_bidrag = 8% × (gross_salary − ATP)`; `a_skat = 38% × (gross_salary − ATP − am_bidrag − manual_tax_deduction)` — a single flat guess at combined state+municipal tax, no municipality, no brackets; `other_tax = user-entered % × net_salary` — a generic stand-in for "Church Tax etc." with no real municipality/church rate; holiday pay = `12.5% × base_gross_salary` (tip excluded) run through the same flat 8%/38% formulas; currency conversion via currencyfreaks.com with an API key hardcoded in the source.

| Old Feature | Exists in V1? | Restore/Keep? | New Implementation |
|---|---|---|---|
| Monthly wage calculation (hours × rate) | Yes | Keep | Unchanged concept — `app/calculations/salary.py` |
| Monthly Salary (fixed) mode | No (old app had no such mode) | New in V1, kept | `app/calculations/salary.py` — V1 addition, not a regression |
| Gross Earned | Yes | Keep | `TaxResult.gross_income` |
| Total Tax Paid | Yes | Keep | Sum of ATP + AM-bidrag + state tax + municipal + church + other adjustments |
| Net Earned | Yes | Keep | `TaxResult.net_income` |
| ATP | Yes | Keep | `app/calculations/atp.py`, verified 2026 table (unchanged from old app's table — it was already correct) |
| AM-bidrag (8%) | Yes | Keep | `app/calculations/am_bidrag.py` — rate unchanged, base now correctly ties into the personlig-indkomst pipeline |
| A-skat (flat 38%) | Was collapsed into one flat number | **Replaced**, not restored as-is | Old flat 38% approximated state+municipal tax combined with no municipality input. V1 already replaced this correctly with real progressive bundskat/mellemskat/topskat/ekstra-topskat (`tax.py`) **plus** municipality-specific municipal tax (`municipal_tax.py`) — strictly more correct and more detailed than the old single number. |
| "Other Tax" (user-typed %, applied to net) | Was a generic stand-in for church tax | **Replaced**, not restored as-is | V1 already replaced this with a real municipality-specific church tax row, gated on actual Folkekirken membership — see item 8 below. The generic "type any %" field itself is not restored (it was a workaround for not having real municipality data, which V1 now has). |
| Personal Tax Deduction (manually entered) | Missing in V1 | **Restored, this task** | New optional `extra_deduction` input — see "Personal deduction" note below for the 2026 reinterpretation |
| Estimated Tip (Optional) | Missing in V1 | **Restored, this task** | New `tips` input, added to the taxable AM-bidrag base — see engine changes |
| Holiday Pay ("Show Holiday Pay Calculation") | Missing in V1 | **Restored, this task** | New `holiday_pay` block — 12.5%/1% split by income mode, real marginal-rate taxation instead of flat 38% — see engine changes |
| Net Holiday Pay | Missing in V1 | **Restored, this task** | `holiday_pay.net` |
| Total Salary Including Holiday Pay | Missing in V1 | **Restored, this task** | New `total_with_holiday` block, summed from the two already-computed streams (no double counting) |
| Currency Conversion (enable/disable) | Missing in V1 | **Restored, this task** | New backend endpoint + frontend section |
| BDT | Missing in V1 | **Restored, this task** | Supported currency |
| USD | Missing in V1 | **Restored, this task** | Supported currency |
| EUR | Missing in V1 | **Restored, this task** | Supported currency |
| Manual exchange rate override | Missing in V1 | **Restored, this task** | Frontend "Manual exchange rate" input, used automatically if the live rate fetch fails |
| Include Holiday Pay in currency conversion | Missing in V1 | **Restored, this task** | Checkbox, mirrors old app's toggle |
| Currency API key hardcoded in source | N/A (security bug, not a feature) | **Removed, not restored** | Moved to a backend-only `CURRENCY_API_KEY` env var; a no-key fallback provider is used by default so conversion works without requiring a paid key at all (see report) |
| Blue "Calculate" button styling / red-blue-green colour-coded numbers | Cosmetic only | Not restored literally | V1's own design system already gives gross/net/tax visually distinct treatment; the specific old hex colours are not preserved as a requirement, the *information density* is |
| Footer "© Rakib Hasan 2025" | Cosmetic | Not restored | Not a functional feature; can be re-added on request |
| Quarter-hour rounding of hours worked (`round(x×4)/4`) | Not in V1 | **Not restored** | V1 uses exact decimal hours (down to the minute) rather than rounding to the nearest 15 minutes — this is a precision *improvement*, not a missing feature, and is called out here so it's a deliberate choice rather than a silent behaviour change |
| Municipality selection | N/A (old app had none) | New in V1, kept | All 98 municipalities, official rates — see item 7 |
| Folkekirken Yes/No | N/A (old app had none) | New in V1, kept | Real per-municipality church tax, gated on membership |
| Tax card (hovedkort/bikort) | N/A (old app had none) | New in V1, kept | Standard estimate vs "my tax card" modes |

## Notes on the two intentionally-replaced calculations

- **Old flat 38% "A-skat"**: this single percentage stood in for the combined effect of state tax + municipal tax with no municipality selected. It could not be correct for any specific person, since Danish municipal tax alone ranges 23.39%–26.30% and state tax is genuinely progressive (12.01% / +7.5% / +7.5% / +5% across four brackets in 2026). V1 already replaced this with the verified bracket engine; this task does not reintroduce the flat number anywhere — it only re-adds the pieces of information density (tips, personal deduction, holiday pay, currency, "other adjustments" row) that sat around that flawed core calculation.
- **Old "Other Tax" as a free-typed percentage of net income**: this was a workaround for not having real per-municipality church tax data. V1 already has that data, so church tax is a first-class row driven by the selected municipality and the Folkekirken toggle, not a generic user-typed percentage. An `other_adjustments` row remains in the new result model as an architectural placeholder for a genuine miscellaneous adjustment in a future version, but it is not populated by a free-text percentage field.
