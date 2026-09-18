# Min Løn — Danish Salary Calculator (2026)

A Danish salary/wage calculator for tax year 2026: two income-entry modes (hourly wage, or fixed monthly salary) feeding one shared, independently-tested tax calculation engine.

## Structure

```
app/            Pure Python calculation engine (no web framework dependency)
  calculations/ salary, atp, am_bidrag, allowances, tax, municipal_tax, withholding, engine
  data/         tax_rules_2026.json, municipalities_2026.json (all 98), atp_2026.json
  models/       SalaryInput, TaxResult (incl. HolidayPayResult, TotalWithHolidayResult)
  tests/        pytest suite (126 tests)
api/            FastAPI wrapper exposing the engine over HTTP (/municipalities, /calculate,
                /exchange-rate/{currency}) and the currency-conversion module (api/currency.py)
web/            Next.js (TypeScript, mobile-first) frontend
docs/
  research_2026.md                    Research report — every constant's source and rationale
  validation_examples.md              Phase 6 realistic validation runs
  old_streamlit_feature_audit.md      V1.1: every feature from the original Streamlit prototype,
                                       audited against V1, and how each was restored/replaced
  v1_2_implementation_audit.md        V1.2: pre-implementation audit of the existing repo
  tax_data_verification_checklist.md  V1.2: source/date/status for every tax constant
  deployment.md                       Deployment: Vercel (frontend) + Render/Railway (backend) setup
```

## Running it

**Engine tests:**
```
pip install -r requirements-dev.txt   # runtime deps + pytest/httpx for testing
pytest app/tests/ -v
```

**API:**
```
uvicorn api.main:app --reload --port 8000
```

**Web app** (in a second terminal):
```
cd web
npm install
npm run dev
```
Then open http://localhost:3000. The frontend calls the API at `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`).

## Design notes

- Every tax constant lives in `app/data/*.json`, never hard-coded in calculation functions — see `docs/research_2026.md` for the source and rationale behind each figure.
- The engine is pure Python with no FastAPI/Next.js dependency, so it is independently testable and reusable: an Android app can call the same FastAPI service, or (if full offline support is needed later) use this engine's JSON data files and test cases as a verified reference for a Kotlin port.
- `calculate_annual_tax()` and `calculate_monthly_withholding()` share every lower-level bracket/allowance function — only the constants they're called with differ (annual vs ÷12).
- Money is handled with `Decimal` throughout the pipeline and only rounded (half-up, to the nearest whole DKK) at the point a line is returned for display.
- Two calculation bases are supported and clearly labelled: a standard 2026-rules estimate, and a tax-card mode that applies a user-supplied SKAT withholding percentage/deduction directly — the engine never claims to reconstruct an individual's exact tax card.
- V1.1 restored every user-facing feature from the original Streamlit prototype (see `docs/old_streamlit_feature_audit.md`) — tips, an optional extra deduction, holiday pay, total-with-holiday, and currency conversion (EUR/USD/BDT, with a manual-rate fallback) — while replacing the prototype's flat 38% tax approximation and hardcoded API key with the verified 2026 engine and a backend-only `CURRENCY_API_KEY` (optional; a no-key fallback provider is used by default).
- Every result is returned as ONE structured object from the backend (`TaxResult` / `CalculateResponse`), including nested `holiday_pay` and `total_with_holiday` blocks — the frontend only renders, it never recomputes tax logic, so the same result model is ready to be consumed by a future Android client.
- V1.2 (see `docs/v1_2_implementation_audit.md`) simplifies the app for ordinary users: an optional age field (with its 2026 AM-bidrag age-exemption rationale explained inline), a Frikort tax-card option that only handles the well-verified "income within remaining balance" case and otherwise stops with a clear message rather than guessing, an explicit Annual/Monthly choice on the input screen, plain-language validation errors, and a results screen restructured into three levels (main result, main breakdown, expandable additional details).

## Known limitations (V1 / V1.2)

See `docs/research_2026.md` item 13 for the full list (foreign income, capital income, B-income, self-employment, multiple employers beyond hovedkort/bikort, etc.) and item 8 for a flagged data-provenance caveat on the per-municipality tax-rate table (verified against official aggregate statistics; recommended to spot-check individual rows against the Ministry of Taxation's own spreadsheet before relying on this for real financial decisions). V1.2 adds two further documented limitations: the AM-bidrag age exemption uses current age rather than date of birth (item 14), and Frikort only supports income within the remaining balance, not the balance-exceeded case (item 15). See `docs/tax_data_verification_checklist.md` for the full per-item verification status.
