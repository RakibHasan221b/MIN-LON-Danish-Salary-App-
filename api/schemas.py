"""Pydantic request/response schemas for the FastAPI layer.

This module and main.py are the ONLY place that knows about HTTP/JSON.
No tax logic lives here — every field is validated and then handed
straight to app.calculations, which is fully independent of FastAPI.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class CalculateRequest(BaseModel):
    income_type: Literal["hourly_wage", "fixed_salary"]

    # Option 1 — Monthly Wage
    hourly_wage: Optional[Decimal] = Field(default=None, ge=0)
    hours: Optional[int] = Field(default=None, ge=0)
    minutes: Optional[int] = Field(default=None, ge=0, le=59)

    # Option 2 — Monthly Salary
    fixed_monthly_salary: Optional[Decimal] = Field(default=None, ge=0)

    # Common
    municipality_name: str
    is_church_member: bool = False

    # V1.2 — age. See docs/research_2026.md item 14 for the AM-bidrag
    # age-exemption rule this feeds and its documented limitation.
    age: Optional[int] = Field(default=None, ge=0, le=120)

    # V1.1 restorations from the old Streamlit prototype
    tips: Optional[Decimal] = Field(default=None, ge=0)
    extra_deduction: Optional[Decimal] = Field(default=None, ge=0)

    # Tax card
    tax_card_mode: Literal["standard_estimate", "my_tax_card"] = "standard_estimate"
    tax_card_type: Literal["hovedkort", "bikort", "frikort"] = "hovedkort"
    tax_card_percentage: Optional[Decimal] = Field(default=None, ge=0, le=1)
    tax_card_monthly_deduction: Optional[Decimal] = Field(default=None, ge=0)

    # V1.2 — Frikort. See docs/research_2026.md item 15.
    remaining_frikort_amount: Optional[Decimal] = Field(default=None, ge=0)

    # Monthly-first simplified default flow. Both optional; mutually
    # exclusive with tax_card_mode="my_tax_card" (the advanced flow).
    monthly_deduction: Optional[Decimal] = Field(default=None, ge=0)
    tax_percentage: Optional[Decimal] = Field(default=None, ge=0, le=1)

    period: Literal["monthly", "annual"] = "monthly"

    @model_validator(mode="after")
    def check_mode_specific_fields(self) -> "CalculateRequest":
        if self.income_type == "hourly_wage":
            if self.hourly_wage is None or self.hours is None:
                raise ValueError("Please enter your hourly wage and hours worked.")
        else:
            if self.fixed_monthly_salary is None:
                raise ValueError("Please enter your fixed monthly salary in DKK.")

        if self.tax_card_mode == "my_tax_card":
            if self.tax_card_type == "frikort":
                if self.remaining_frikort_amount is None:
                    raise ValueError(
                        "Please enter your remaining Frikort amount (from your forskudsopgørelse)."
                    )
                if self.tax_card_percentage is not None or self.tax_card_monthly_deduction is not None:
                    raise ValueError(
                        "Frikort doesn't use a withholding percentage or monthly deduction — "
                        "only the remaining Frikort amount."
                    )
            else:
                if self.tax_card_percentage is None:
                    raise ValueError("Please enter your tax card withholding percentage.")
                if self.tax_card_type == "hovedkort" and self.tax_card_monthly_deduction is None:
                    raise ValueError(
                        "Please enter your monthly deduction (fradrag) for your hovedkort."
                    )
            if self.monthly_deduction is not None or self.tax_percentage is not None:
                raise ValueError(
                    "Choose one: either let us estimate your tax from your municipality, or "
                    "enter your own tax card figures. They can't be combined."
                )
        return self


class BreakdownLineOut(BaseModel):
    label: str
    amount: float


class HolidayPayOut(BaseModel):
    rate_label: str
    gross: float
    am_bidrag: float
    income_tax: float
    net: float


class TotalWithHolidayOut(BaseModel):
    gross: float
    tax: float
    net: float


class CalculateResponse(BaseModel):
    period: str
    calculation_basis: str
    tax_year: int
    municipality_name: str
    is_church_member: bool

    base_gross_income: float
    tips: float
    gross_income: float
    atp_employee_contribution: float
    am_bidrag: float
    employment_allowance: float
    job_allowance: float
    extra_deduction_applied: float
    taxable_income: float
    bundskat: float
    mellemskat: float
    topskat: float
    ekstra_topskat: float
    state_tax_total: float
    municipal_tax: float
    church_tax: float
    other_adjustments: float
    total_tax: float
    net_income: float
    effective_tax_rate: float

    age_am_bidrag_exempt: bool
    remaining_frikort_amount: Optional[float] = None

    monthly_deduction_applied: Optional[float] = None
    tax_percentage_used: Optional[float] = None
    tax_percentage_estimated: bool = False

    holiday_pay: HolidayPayOut
    total_with_holiday: TotalWithHolidayOut

    breakdown: list[BreakdownLineOut]
    assumptions: list[str]


class MunicipalityOut(BaseModel):
    name: str
    municipality_code: Optional[str] = None
    municipal_tax_rate: float
    church_tax_rate: float


class ExchangeRateResponse(BaseModel):
    currency: str
    rate: float
    source: str


class ExchangeRateErrorResponse(BaseModel):
    detail: str = "Currency conversion temporarily unavailable."
