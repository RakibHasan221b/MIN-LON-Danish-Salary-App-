# Min Løn — 2026 Danish Tax Rules Research Report

Status: V1 research, current as of 2026-09-18. This document is the single source of truth for every constant in `app/data/*.json`. If a number changes, this file is updated first and the JSON files second.

## Method and source priority

Primary sources, in order of authority: **skat.dk** (Danish Tax Agency) for national tax mechanics and thresholds, **svmn.dk** (Ministry of Taxation's local-government statistics unit, the successor site `skm.dk` now redirects to) and **Danmarks Statistik / Statistikbanken** for municipal tax rates, **borger.dk / virk.dk** (the official ATP guidance mirrored on citizen/business portals) for ATP contribution tables. Third-party payroll/accounting sites (skatteguiden.dk, skatteberegneren.dk, martinsen.dk, etc.) are used only to corroborate figures already found on an official source, or, for the full 98-municipality table specifically, because the official site's per-municipality table is rendered through an interactive picker that plain fetching cannot extract — in that one case the third-party transcription is cross-checked against the official site's published aggregate statistics (min, max, national average) before being accepted. That cross-check is documented in item 8 below.

---

### 1. National tax rates (2026 reform)

2026 is the first year of a restructured Danish state tax system that splits the old topskat into three tiers.

| Bracket | Rate | Base |
|---|---|---|
| Bundskat (bottom tax) | 12.01% | Personal income + positive net capital income, above the personal allowance |
| Mellemskat (middle tax) — **new in 2026** | 7.5% | Personal income above DKK 641,200 (also applies to capital income above DKK 55,000) |
| Topskat (top tax) | 7.5% | Personal income above DKK 777,900 |
| Ekstra topskat / "top-topskat" (additional top tax) — **new in 2026** | 5.0% | Personal income above DKK 2,592,700 |

Source: [skat.dk — Bottom bracket, middle bracket, top bracket and additional top bracket tax](https://skat.dk/en-us/help/botton-bracket-middle-bracket-top-bracket-and-additional-top-bracket-tax).

**Conflict found and resolved:** skat.dk's English page states these three thresholds "after labour market contribution" (641,200 / 777,900 / 2,592,700), while several Danish accounting summaries (skatteguiden.dk, martinsen.dk) quote them "before AM-bidrag" (697,000 / 845,500 / 2,818,000). The two sets are consistent: 697,000 × (1 − 0.08) ≈ 641,240; 845,500 × 0.92 ≈ 777,860; 2,818,000 × 0.92 ≈ 2,592,560 (small residual rounding). This is not a factual conflict, just two presentations of the same bracket point. **Resolution:** the engine applies brackets to *personlig indkomst* as computed after the AM-bidrag deduction, so the after-AM-bidrag figures (641,200 / 777,900 / 2,592,700) are the ones stored and used directly — no further conversion needed at calculation time.

**Skatteloft (tax ceiling):** a combined ceiling on state-level personal-income tax of 44.57% is published for 2026 (skatteguiden.dk). Implication: bundskat + mellemskat + topskat + ekstra topskat = 12.01 + 7.5 + 7.5 + 5 = 32.01%, which never reaches 44.57% under the flat 2026 rates, so the ceiling cannot bind for ordinary personal income in V1. It is recorded in the data file for completeness but the engine does not need ceiling-clamping logic for V1's personal-income-only scope.

### 2. Personal allowance (personfradrag)

**DKK 54,100** for adults (2026). Confirmed by skat.dk-derived summaries and independently by skatteguiden.dk and løntal.dk. Applied against bundskat (and, per Danish rules, also reduces the base for kommuneskat/church tax — see item 9). Stored in `tax_rules_2026.json`, never hard-coded in calculation functions, per the spec's explicit requirement.

Source: [Løntal.dk — Personfradrag 2026](https://xn--lntal-vua.dk/blog/personfradrag-2026), cross-checked via [skatteguiden.dk](https://www.skatteguiden.dk/skattesatser/).

### 3. Employment allowance (beskæftigelsesfradrag)

**Rate: 12.75%. Maximum: DKK 63,300** (2026). Base: income subject to AM-bidrag (i.e. AM-bidragsgrundlag, wage income including what will become the 8% AM-bidrag — the allowance is computed on the pre-AM-bidrag-deduction wage base, not on the post-deduction "personal income"). Full DKK 63,300 allowance is reached at income of DKK 496,471.

Source: [skat.dk — Employment and job allowances](https://skat.dk/en-us/individuals/deductions-and-allowances/deductions-and-allowances-when-working/employment-and-job-allowances) (the "63,3000" figure returned by one fetch is a transcription artefact of that page's formatting; cross-checked against skatteguiden.dk which independently states DKK 63,300 — 63,300 is used).

### 4. Job allowance (jobfradrag)

**Rate: 4.50%** of income **above DKK 235,200** (the "bundgrænse"/floor). **Maximum: DKK 3,100.** Full allowance reached at income of DKK 304,089. Same official source as item 3.

### 5. AM-bidrag (labour market contribution)

**8%**, unchanged for 2026. Calculated on the AM-bidragsgrundlag (essentially gross wage income minus the employee's own ATP contribution — see ordering note below), *before* the bundskat/mellemskat/topskat/ekstra-topskat calculation and before the employment/job allowances are subtracted from the tax base. Source: skatteguiden.dk 2026 rate table, consistent across every source consulted (uncontested figure).

**Ordering, as implemented:**
1. Gross income (from either input mode).
2. Subtract the employee's ATP contribution (see item 7) — ATP is deducted from wage income before AM-bidrag is calculated on it.
3. AM-bidragsgrundlag = gross − ATP(employee share).
4. AM-bidrag = 8% × AM-bidragsgrundlag.
5. Personal income (for bund/mellem/top/ekstra-top tax) = AM-bidragsgrundlag − AM-bidrag, minus the personal allowance for bundskat specifically.
6. Employment allowance and job allowance are computed on the AM-bidragsgrundlag (step 3), *before* the 8% is subtracted, per item 3's official wording — they reduce the taxable base for bund/mellem/topskat, not the AM-bidrag itself.

This matches the spec's required ordering exactly (gross → ATP → AM income → 8% AM-bidrag → subsequent income-tax calculations) and is the ordering `app/calculations/engine.py` implements.

### 6. Church tax (kirkeskat)

Optional, membership-based, not automatically applied. If the user is a member of Folkekirken, the municipality's 2026 kirkeskat rate (item 8) is applied to the same base as municipal tax. If not a member, church tax = 0 and the row is hidden from the result breakdown (per the "don't display zero-value rows" instruction). National average for 2026: 0.639% (svmn.dk aggregate figure, see item 8's cross-check).

### 7. ATP (Arbejdsmarkedets Tillægspension) — employee contribution, 2026

ATP for ordinary wage earners is a **fixed DKK table keyed by hours worked per pay period**, not a percentage of salary, and it depends on pay frequency (monthly / biweekly / weekly). Only the employee's own third is deducted from net pay; the employer's two-thirds is not part of this calculator. Verified across two official/quasi-official sources (virk.dk's ATP employer guidance and borger.dk's citizen-facing ATP page), which agree exactly:

**Monthly-paid employees (A-sats, employee's 1/3 share):**

| Hours worked per month | Employee share (DKK) |
|---|---|
| ≥ 117 hours | 99.00 |
| 78 – 116 hours | 66.00 |
| 39 – 77 hours | 33.00 |
| < 39 hours | 0.00 |

**Biweekly-paid employees:**

| Hours per 14 days | Employee share (DKK) |
|---|---|
| ≥ 54 | 52.20 |
| 36 – 53 | 34.80 |
| 18 – 35 | 17.40 |
| < 18 | 0.00 |

**Weekly-paid employees:**

| Hours per week | Employee share (DKK) |
|---|---|
| ≥ 27 | 26.10 |
| 18 – 26 | 17.40 |
| 9 – 17 | 8.70 |
| < 9 | 0.00 |

**Important note on the spec's caution:** the spec explicitly warned not to reuse the old prototype's "≥117=99, 78–116=66, 39–77=33" table without verifying it against 2026 sources. Having verified it independently against virk.dk (2026 ATP satser page) and borger.dk (2026 ATP satser for private virksomhed page), **these exact monthly figures are confirmed correct and unchanged for 2026** — the ATP employee-contribution table has been stable at these DKK amounts for a number of years and 2026 is no exception. The biweekly/weekly tables above are new additions this calculator supports for future pay-frequency flexibility (V1 UI only collects monthly hours, so only the monthly table is wired into the UI for now; the others are stored in `atp_2026.json` for architectural completeness).

Source: [virk.dk — Gældende satser for ATP-bidrag](https://virk.dk/vejledning/atp/atp-arbejdsgiver/atp-satser/), [borger.dk — ATP-satser for privat virksomhed](https://www.borger.dk/pension-og-efterloen/ATP-Livslang-pension-oversigt/atp-bidraget/atp-satser-for-privat-virksomhed).

**Monthly-salary mode implication:** a user on Option 2 (fixed monthly salary) is assumed full-time (≥117 hours/month) unless the V1 UI later adds an hours field for salaried staff too; documented as an assumption (see item 13).

### 8. Municipal tax rates — all 98 municipalities

Official aggregate figures, from svmn.dk (the Ministry of Taxation's successor site for local-government tax statistics, `skm.dk` redirects here): for 2026, **lowest municipal tax rate 23.39% (Copenhagen), highest 26.30%, national (population-weighted) average municipal tax 25.049%, national average church tax 0.639%**.

The per-municipality breakdown itself is published by the same ministry as an interactive picker / downloadable spreadsheet ("Kommuneskatteprocenter siden 1977") that could not be scraped row-by-row through automated fetching in this session. A full 98-row table (name, municipal tax %, church tax %) was obtained from a third-party payroll-reference site (skatteberegneren.dk) and validated against the official aggregate figures above: **the transcribed table's minimum (23.39%, Copenhagen) and maximum (26.30%, shared by several municipalities including Lolland, Sorø, Svendborg, Vordingborg) match the official published range exactly**, which is strong (though not 100%-complete-row) corroboration.

**Recommendation / open risk flagged to the user:** this per-municipality table should ideally be spot-checked against the official downloadable spreadsheet before this app is relied on for real financial decisions; the data-validation test suite (Phase 4) checks internal consistency (98 unique municipalities, all rates numeric and in a plausible 20–30% / 0–2% range) but cannot itself prove every single row matches the ministry's spreadsheet byte-for-byte. This is documented rather than silently assumed away, per the spec's explicit instruction not to invent or silently resolve conflicting data.

Full table stored in `app/data/municipalities_2026.json`, rates as decimals (23.39% → 0.2339).

Sources: [svmn.dk — Kommuneskatter, gennemsnitsprocenter 2007–2026](https://svmn.dk/tal-og-metode/satser/statistik-i-kommunerne/kommuneskatter-gennemsnitsprocenter-2007-2026) (aggregate/official), cross-check table transcription via skatteberegneren.dk's 2026 municipality list.

### 9. Tax bases: personlig indkomst vs skattepligtig indkomst

This is the detail the spec's "never do `gross × municipal_tax_rate`" warning is really about, so it is spelled out precisely rather than approximated:

- **Personlig indkomst** (personal income) = gross wage income − ATP (employee share) − AM-bidrag. This is the base for **bundskat, mellemskat, topskat and ekstra topskat**. The employment allowance and job allowance do **not** reduce this base — they are "ligningsmæssige fradrag", which only affect the base below.
- **Skattepligtig indkomst** (taxable income) = personlig indkomst − employment allowance − job allowance. This is the base for **municipal tax and church tax**.
- The **personal allowance** (item 2) is subtracted once more, at the point of calculating each tax: bundskat = 12.01% × max(0, personlig indkomst − personfradrag); municipal/church tax = rate × max(0, skattepligtig indkomst − personfradrag). Mellemskat/topskat/ekstra-topskat are **not** reduced by the personal allowance — their published thresholds (item 1) already have this built in, consistent with Danish tax law since the 2010 reform which decoupled top-bracket taxation from the personal allowance.

This is the standard structure used by SKAT's own forskudsopgørelse mechanics for ordinary wage earners, and is what `app/calculations/tax.py` and `app/calculations/municipal_tax.py` implement — never a flat percentage of gross.

### 10. Tax card (skattekort) rules

Two card types:
- **Hovedkort (main card):** used at a person's primary employer. Includes a monthly *fradrag* (deduction) amount (derived from the annual personal allowance and any other allowances on the person's forskudsopgørelse) subtracted from wage income before the withholding percentage is applied.
- **Bikort (secondary card):** used at a second/additional employer. No monthly fradrag — the withholding percentage applies to the full wage amount from the first krone.

**V1 design decision (per spec):** the engine does **not** attempt to reconstruct an individual's actual SKAT-issued withholding percentage or fradrag from salary and municipality alone — that number depends on a person's full forskudsopgørelse (other income, deductions, etc.) which this calculator does not collect. Instead two distinct, clearly-labelled modes are offered: (a) **Standard estimate** — the engine computes an *estimated* annual/monthly tax using the brackets, allowances and rates above; (b) **"Use my tax card"** — the user supplies their actual withholding percentage (and, for hovedkort, their actual monthly fradrag), and `withholding.py` applies that directly instead of running the bracket calculation. The UI never claims the standard-estimate mode reproduces an exact payslip.

### 11. Annual vs monthly calculation

`calculate_annual_tax()` computes brackets, allowances and the personal allowance on their true annual bases. `calculate_monthly_withholding()` divides the relevant annual constants by 12 (personal allowance/12, bracket thresholds/12, allowance caps/12) and applies the same bracket logic to the monthly gross figure — this mirrors how Danish payroll withholding actually works (SKAT publishes monthly trækprocent tables derived from annual figures, not a separate monthly rule set). Both share the same underlying bracket/allowance functions parameterised by period length, per the spec's explicit requirement that they "share lower-level tax functions" rather than duplicate logic.

### 12. Rounding assumptions

- All money amounts are computed internally using Python's `Decimal` type (never native float), with intermediate results kept unrounded through the pipeline.
- Each line of the final breakdown (ATP, AM-bidrag, allowances, each tax bracket's contribution, municipal tax, church tax, net) is rounded to the nearest whole DKK (`ROUND_HALF_UP`) only at the point it is displayed/returned from the engine, matching how Danish payslips present whole-krone line items.
- Percentage rates are stored as exact decimals (e.g. 0.2339) to avoid the 23.39/100 floating-point representation issue entirely.
- The effective tax rate shown in the UI is computed from the *rounded* net and gross figures (net/gross), which can introduce a sub-0.01-percentage-point discrepancy versus computing it from unrounded internals; this is accepted as immaterial and documented rather than hidden.

### 13a. Holiday pay (feriepenge) — V1.1 addition

Denmark's holiday-pay system splits by employment type:

- **Timelønnede (hourly-paid, no full sick/holiday pay continuation)** — the population this app's "Monthly Wage" mode targets — receive **feriegodtgørelse: 12.5% of gross wage**, paid separately (historically via FerieKonto / Lønmodtagernes Feriemidler) rather than folded into ordinary pay. Source: [dataloen.dk — Feriegodtgørelse](https://www.dataloen.dk/ordbog/feriegodtgoerelse/).
- **Funktionærer (salaried employees under the Salaried Employees Act)** — this app's "Monthly Salary" mode — get paid holiday leave directly (their ordinary salary continues during holiday) plus a **ferietillæg: 1% of pensionable annual salary** (some collective agreements pay 1.5–2%; V1.1 uses the statutory 1% baseline and documents this as a simplification). Source: [loen.dk — Ferietillæg 2026](https://loen.dk/blog/ferietillaeg-2026).

**V1.1 implementation decision:** the "Show Holiday Pay Calculation" feature computes 12.5% for Monthly Wage mode and 1% for Monthly Salary mode, applied to *total* gross income (base + tips) — tips are included because employer-paid tips processed through ordinary payroll are themselves A-indkomst and feriepligtig, unlike the old prototype which excluded tips from the holiday base without explanation.

**Tax treatment of holiday pay**, per the same sources: it is ordinary A-indkomst, subject to the **8% AM-bidrag**, and taxed "at your regular withholding rate" — i.e. SKAT does not re-run a fresh personal-allowance/bracket calculation for a supplementary payout in the same period; it applies the trækprocent (withholding percentage) already in effect. V1.1 models this as follows, which is a documented approximation, not a SKAT-verified formula for every case:

- **ATP**: not charged on holiday pay. ATP accrues on hours actually worked in a period; holiday pay is not tied to hours worked in the payout period. (Not found explicitly stated for 2026 in the sources consulted — treated as a reasonable, standard assumption and flagged as such.)
- **Standard-estimate mode**: since the ordinary salary in the same month has already consumed the personal allowance and the lower brackets, holiday pay is taxed at the person's current **marginal** combined rate: municipal tax rate + church tax rate (if a member) + bundskat rate + mellemskat rate (only if the ordinary month's personlig indkomst already exceeds the mellemskat threshold) + topskat rate (only if already above that threshold) + ekstra-topskat rate (only if already above that threshold). This mirrors how an extra krone of income is actually taxed once the allowance is used up, without double-applying the personal allowance to a second income stream in the same month.
- **Tax-card mode**: the user's supplied `tax_card_percentage` is applied directly to the AM-bidrag-reduced holiday base, with **no** monthly fradrag subtracted a second time (the fradrag was already used against the ordinary salary in the same month) — consistent with how SKAT applies a trækprocent to a supplementary payout.

This is flagged as the area of this V1.1 update with the least official primary-source specificity (SKAT's exact administrative treatment of a same-month supplementary payout was not directly located); the marginal-rate approach is the standard, defensible approximation used by payroll systems for this situation, and is clearly labelled as an estimate in the UI.

### 13b. Currency conversion — V1.1 addition

DKK amounts are converted to a display currency only, strictly *after* the full Danish tax calculation — never before. Two providers are used:

- **No-key fallback (default): [open.er-api.com](https://open.er-api.com/v6/latest/DKK)**, a free, keyless exchange-rate API, confirmed to return DKK-based rates for USD, EUR and BDT (verified live during this research: 1 DKK ≈ 0.1535 USD / 0.1338 EUR / 18.92 BDT on 2026-09-18). This replaces the old app's hardcoded-key provider by default, so currency conversion works without requiring any secret at all.
- **Optional keyed provider**: if a `CURRENCY_API_KEY` environment variable is set on the backend, the app can use a keyed provider (e.g. currencyfreaks.com, the old app's provider) for potentially fresher/more reliable rates. The key is read server-side only via `os.environ` and is never sent to or exposed in the frontend, unlike the old app's `API_KEY = "50c81616ae69471da10d264e01c474cc"` hardcoded directly in the Streamlit source.
- If both the keyed and no-key providers fail, the API returns a clear "unavailable" status and the frontend falls back to a manual exchange-rate entry, exactly as the old app allowed — the core DKK salary calculation is never blocked by a currency-provider failure.

### 13c. "Personal deduction" — reinterpreted for 2026

The old app's free-text "Personal Tax Deduction Amount" effectively stood in for the personal allowance itself (it was subtracted from the base before a flat 38% was applied, since the old app had no built-in personfradrag). V1 already applies the correct, automatic 2026 personfradrag (DKK 54,100/year, item 2) to every calculation. Reintroducing the old field as a second personal allowance would double-count it. Instead, V1.1 restores it as an **optional additional deduction** representing a ligningsmæssigt fradrag the engine does not automatically know about (e.g. fagforeningskontingent, kørselsfradrag) — it reduces **skattepligtig indkomst** (the municipal/church tax base), the same base the employment and job allowances reduce, not personlig indkomst (the state-bracket base) and not the personfradrag itself. This is a documented reinterpretation, not a like-for-like restoration of the old formula, per the explicit instruction not to reuse the old flat-38% logic.

### 14. AM-bidrag age exemption — V1.2 addition

Danish AM-bidrag has a minors' exemption: the exemption runs through the income year in which the person turns 17 — i.e. it is a **whole-tax-year rule** keyed to whether the person turns 18 at any point during the tax year, not the person's age at the moment a calculation is run. A worker who is 17 today but turns 18 later in the same tax year is, under this verified rule, **not** exempt for the full year.

**Known limitation, documented rather than hidden:** V1.2 only collects the user's current age (a plain integer), not their date of birth. It therefore cannot implement the exact whole-year rule. The app uses a simplified rule instead: **age ≤ 17 → AM-bidrag exempt**. This can over-exempt someone who is 17 now but will turn 18 later in the same tax year. This limitation is stated in `app/data/tax_rules_2026.json`'s `am_bidrag_age_exemption` block, is applied consistently by `app.calculations.am_bidrag.is_exempt_by_age`, and is surfaced to the user in the result's `assumptions` list whenever the exemption is actually applied — it is never silently assumed away, and adult behaviour (AM-bidrag charged normally) is never hardcoded as the only path; the exemption is a real, tested branch.

**Not verified in V1.2, left as open items** (see `docs/tax_data_verification_checklist.md`):
- ATP eligibility by age — Danish ATP membership has historically had its own minimum-age rules distinct from the AM-bidrag age rule; not independently confirmed for 2026 within this task's research budget. ATP is left unchanged (charged per the existing hours-based table regardless of age).
- Employment allowance (beskæftigelsesfradrag), job allowance (jobfradrag) and personfradrag for minors — no source was found stating these differ for someone under 18; V1.2 assumes they apply unchanged. This is an assumption, not a verified fact.

Source consulted for the whole-year rule: SKAT guidance on AM-bidrag exemption for persons under 18, cross-referenced during V1.2 research (see the app's assumptions text and this document as the recorded rationale — no single stable URL is cited here because the guidance is distributed across SKAT's minors/AM-bidrag help pages rather than one canonical page; treat this as a lower-confidence source than the numbered brackets above and re-verify before relying on it for a real payslip).

### 15. Frikort (tax-free card) — V1.2 addition

A frikort lets a person earn income completely free of state/municipal/church income tax up to a running annual balance ("resterende frikortbeløb" / remaining Frikort amount) shown on their forskudsopgørelse. Two points confirmed during V1.2 research:

1. **AM-bidrag still applies under frikort** (except where the age exemption in item 14 applies) — frikort exempts income tax, not the labour-market contribution.
2. **Once the frikort balance is exhausted, the employee switches to bikort withholding for the remainder** — this is not an automatic blended calculation SKAT performs on a single payslip; it is a change in which card applies going forward.

**What V1.2 implements:** only the well-verified case — the income being calculated is within the user's stated remaining balance, so income tax on it is 0. This is implemented in `app.calculations.frikort.compute_frikort_withholding`.

**What V1.2 deliberately does NOT implement:** if the entered income exceeds the remaining balance, the app does not attempt to reconstruct how much of that period's income falls before vs after the balance is exhausted (this would require information the app does not collect, such as exactly when in the period the balance ran out). Rather than inventing a blended tax figure or silently falling back to hovedkort/bikort/standard-estimate, `compute_frikort_withholding` raises `FrikortBalanceExceededError` with a message directing the user to switch to Bikort or lower the entered income — see `docs/v1_2_implementation_audit.md` and the dedicated tests in `app/tests/test_frikort.py`.

**Documented assumption (not independently verified):** whether SKAT compares the frikort balance against gross A-indkomst or an AM-bidrag-adjusted figure. V1.2 compares against gross income. Flagged in `docs/tax_data_verification_checklist.md`.

### 13. Explicitly excluded from V1 (documented, not silently dropped)

Complex pension arrangements beyond the standard ATP employee contribution, foreign income, capital income (beyond the fact that mellemskat/topskat bases technically include positive net capital income — V1 assumes DKK 0 capital income for all users), special/commuter deductions, spouse-related joint taxation, senior allowances, single-parent allowances, multiple simultaneous employers (beyond the hovedkort/bikort distinction as a withholding-mode toggle), B-income, self-employment, benefits in kind, stock compensation, expatriate tax schemes (forskerskatteordningen), and the skatteloft-clamping logic (item 1) since it cannot bind under 2026's flat rates for ordinary personal income. Fixed monthly salary mode (Option 2) is assumed full-time (≥117 ATP hours/month) since V1 does not collect an hours field for that mode — flagged for a future V1.1 refinement if part-time salaried users need accurate ATP.
