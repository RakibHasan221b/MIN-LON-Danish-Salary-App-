"""FastAPI wrapper around app.calculations.engine — the seam a future
Android client can call directly (see docs/research_2026.md and the
build plan's Android-reuse rationale)."""
from __future__ import annotations

import os
from decimal import Decimal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.calculations.engine import calculate_annual_tax, calculate_monthly_withholding
from app.data_loader import load_municipalities
from app.models.salary_input import IncomeType, SalaryInput, TaxCardMode, TaxCardType
from app.models.tax_result import TaxResult
from api.currency import CurrencyUnavailableError, get_exchange_rate
from api.schemas import (
    BreakdownLineOut,
    CalculateRequest,
    CalculateResponse,
    ExchangeRateResponse,
    HolidayPayOut,
    MunicipalityOut,
    TotalWithHolidayOut,
)

app = FastAPI(title="Min Løn API", version="0.2.0")

# CORS: which frontend origin(s) are allowed to call this API from a
# browser. Configured via the CORS_ALLOWED_ORIGINS environment variable
# (comma-separated, e.g. "https://min-loen.vercel.app,https://www.min-loen.dk").
# If unset, defaults to the standard local Next.js dev origins only, never
# a wildcard, so a deployed backend is never accidentally left open to
# every website on the internet. See docs/deployment.md for the full
# production setup.
_DEFAULT_DEV_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]


def _load_cors_allowed_origins() -> list[str]:
    raw = os.environ.get("CORS_ALLOWED_ORIGINS", "").strip()
    if not raw:
        return _DEFAULT_DEV_ORIGINS
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or _DEFAULT_DEV_ORIGINS


app.add_middleware(
    CORSMiddleware,
    allow_origins=_load_cors_allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Row labels that are shown even when their amount is 0 — everything else
# with a zero amount is hidden from the breakdown per the spec.
_ALWAYS_SHOW_LABELS = {
    "Gross income",
    "Total gross",
    "Base gross",
    "Estimated net salary",
    "Income tax (Frikort — tax-free)",
    "Gross salary",
    "Monthly fradrag",
    "Taxable after fradrag",
    "A-tax / withheld tax",
    # ATP and AM-bidrag are always shown even at 0 kr (e.g. a shift short
    # enough that ATP doesn't apply), matching the user's reference app,
    # which always prints these lines regardless of amount.
    "ATP",
    "AM-bidrag",
    "State Tax / A-skat (tax card)",
}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/municipalities", response_model=list[MunicipalityOut])
def municipalities() -> list[dict]:
    return load_municipalities()


def _to_salary_input(req: CalculateRequest) -> SalaryInput:
    return SalaryInput(
        income_type=IncomeType(req.income_type),
        hourly_wage=req.hourly_wage,
        hours=req.hours,
        minutes=req.minutes,
        fixed_monthly_salary=req.fixed_monthly_salary,
        municipality_name=req.municipality_name,
        is_church_member=req.is_church_member,
        age=req.age,
        tax_card_mode=TaxCardMode(req.tax_card_mode),
        tax_card_type=TaxCardType(req.tax_card_type),
        tax_card_percentage=req.tax_card_percentage,
        tax_card_monthly_deduction=req.tax_card_monthly_deduction,
        remaining_frikort_amount=req.remaining_frikort_amount,
        monthly_deduction=req.monthly_deduction,
        tax_percentage=req.tax_percentage,
        tips=req.tips or Decimal(0),
        extra_deduction=req.extra_deduction or Decimal(0),
    )


def _to_response(result: TaxResult) -> CalculateResponse:
    return CalculateResponse(
        period=result.period,
        calculation_basis=result.calculation_basis.value,
        tax_year=result.tax_year,
        municipality_name=result.municipality_name,
        is_church_member=result.is_church_member,
        base_gross_income=float(result.base_gross_income),
        tips=float(result.tips),
        gross_income=float(result.gross_income),
        atp_employee_contribution=float(result.atp_employee_contribution),
        am_bidrag=float(result.am_bidrag),
        employment_allowance=float(result.employment_allowance),
        job_allowance=float(result.job_allowance),
        extra_deduction_applied=float(result.extra_deduction_applied),
        taxable_income=float(result.taxable_income),
        bundskat=float(result.bundskat),
        mellemskat=float(result.mellemskat),
        topskat=float(result.topskat),
        ekstra_topskat=float(result.ekstra_topskat),
        state_tax_total=float(result.state_tax_total),
        municipal_tax=float(result.municipal_tax),
        church_tax=float(result.church_tax),
        other_adjustments=float(result.other_adjustments),
        total_tax=float(result.total_tax),
        net_income=float(result.net_income),
        effective_tax_rate=float(result.effective_tax_rate),
        age_am_bidrag_exempt=result.age_am_bidrag_exempt,
        remaining_frikort_amount=(
            float(result.remaining_frikort_amount)
            if result.remaining_frikort_amount is not None
            else None
        ),
        monthly_deduction_applied=(
            float(result.monthly_deduction_applied)
            if result.monthly_deduction_applied is not None
            else None
        ),
        tax_percentage_used=(
            float(result.tax_percentage_used) if result.tax_percentage_used is not None else None
        ),
        tax_percentage_estimated=result.tax_percentage_estimated,
        holiday_pay=HolidayPayOut(
            rate_label=result.holiday_pay.rate_label,
            gross=float(result.holiday_pay.gross),
            am_bidrag=float(result.holiday_pay.am_bidrag),
            income_tax=float(result.holiday_pay.income_tax),
            net=float(result.holiday_pay.net),
        ),
        total_with_holiday=TotalWithHolidayOut(
            gross=float(result.total_with_holiday.gross),
            tax=float(result.total_with_holiday.tax),
            net=float(result.total_with_holiday.net),
        ),
        breakdown=[
            BreakdownLineOut(label=line.label, amount=float(line.amount))
            for line in result.breakdown()
            if line.amount != 0 or line.label in _ALWAYS_SHOW_LABELS
        ],
        assumptions=result.assumptions,
    )


@app.post("/calculate", response_model=CalculateResponse)
def calculate(req: CalculateRequest) -> CalculateResponse:
    try:
        salary_input = _to_salary_input(req)
        result = (
            calculate_annual_tax(salary_input)
            if req.period == "annual"
            else calculate_monthly_withholding(salary_input)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@app.get("/exchange-rate/{currency}", response_model=ExchangeRateResponse)
def exchange_rate(currency: str) -> ExchangeRateResponse:
    """1 DKK -> `currency`. Currency conversion always happens AFTER the
    Danish tax calculation — this endpoint only ever converts already-
    computed DKK figures, never feeds a converted amount back into
    /calculate. See docs/research_2026.md item 13b."""
    try:
        rate, source = get_exchange_rate(currency)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except CurrencyUnavailableError as exc:
        raise HTTPException(
            status_code=503, detail="Currency conversion temporarily unavailable."
        ) from exc
    return ExchangeRateResponse(currency=currency.upper(), rate=float(rate), source=source)
