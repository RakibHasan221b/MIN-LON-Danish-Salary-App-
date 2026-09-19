export type IncomeType = "hourly_wage" | "fixed_salary";
export type TaxCardMode = "standard_estimate" | "my_tax_card";
export type TaxCardType = "hovedkort" | "bikort" | "frikort";

export interface Municipality {
  name: string;
  municipality_code: string | null;
  municipal_tax_rate: number;
  church_tax_rate: number;
}

export interface CalculateRequest {
  income_type: IncomeType;
  hourly_wage?: number;
  hours?: number;
  minutes?: number;
  fixed_monthly_salary?: number;
  municipality_name: string;
  is_church_member: boolean;
  age?: number;
  tips?: number;
  extra_deduction?: number;
  tax_card_mode: TaxCardMode;
  tax_card_type: TaxCardType;
  tax_card_percentage?: number;
  tax_card_monthly_deduction?: number;
  remaining_frikort_amount?: number;

  // Monthly-first simplified default flow. Both optional; mutually
  // exclusive with tax_card_mode="my_tax_card".
  monthly_deduction?: number;
  tax_percentage?: number;

  period: "monthly" | "annual";
}

export interface BreakdownLine {
  label: string;
  amount: number;
}

export interface HolidayPay {
  rate_label: string;
  gross: number;
  am_bidrag: number;
  income_tax: number;
  net: number;
}

export interface TotalWithHoliday {
  gross: number;
  tax: number;
  net: number;
}

export interface CalculateResponse {
  period: string;
  calculation_basis: string;
  tax_year: number;
  municipality_name: string;
  is_church_member: boolean;
  base_gross_income: number;
  tips: number;
  gross_income: number;
  atp_employee_contribution: number;
  am_bidrag: number;
  employment_allowance: number;
  job_allowance: number;
  extra_deduction_applied: number;
  taxable_income: number;
  bundskat: number;
  mellemskat: number;
  topskat: number;
  ekstra_topskat: number;
  state_tax_total: number;
  municipal_tax: number;
  church_tax: number;
  other_adjustments: number;
  total_tax: number;
  net_income: number;
  effective_tax_rate: number;
  age_am_bidrag_exempt: boolean;
  remaining_frikort_amount: number | null;
  monthly_deduction_applied: number | null;
  tax_percentage_used: number | null;
  tax_percentage_estimated: boolean;
  holiday_pay: HolidayPay;
  total_with_holiday: TotalWithHoliday;
  breakdown: BreakdownLine[];
  assumptions: string[];
}

/** Currency codes are validated by the backend's own list, which now covers
 *  the EU/EEA plus the currencies people most often send money home in, so
 *  this is a plain string rather than a hardcoded union of three. */
export type SupportedCurrency = string;

export interface Currency {
  code: string;
  name: string;
}

export interface ExchangeRateResponse {
  currency: string;
  rate: number;
  source: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchCurrencies(): Promise<Currency[]> {
  const res = await fetch(`${API_BASE}/currencies`, { cache: "force-cache" });
  if (!res.ok) throw new Error("Could not load currencies");
  return res.json();
}

export async function fetchMunicipalities(): Promise<Municipality[]> {
  const res = await fetch(`${API_BASE}/municipalities`, { cache: "force-cache" });
  if (!res.ok) throw new Error("Could not load municipalities");
  return res.json();
}

export async function calculate(req: CalculateRequest): Promise<CalculateResponse> {
  const res = await fetch(`${API_BASE}/calculate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Calculation failed");
  }
  return res.json();
}

/** Currency conversion is a separate call, made AFTER the DKK salary
 * calculation already exists — never used to convert inputs beforehand.
 * Returns null (never throws) if the live rate is unavailable, so the
 * caller can fall back to a manual rate without breaking the page. */
export async function fetchExchangeRate(
  currency: SupportedCurrency
): Promise<ExchangeRateResponse | null> {
  try {
    const res = await fetch(`${API_BASE}/exchange-rate/${currency}`);
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}
