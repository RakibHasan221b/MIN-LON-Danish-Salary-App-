"use client";

import { useEffect, useState } from "react";
import MunicipalitySearch from "@/components/MunicipalitySearch";
import ResultBreakdown from "@/components/ResultBreakdown";
import {
  calculate,
  fetchMunicipalities,
  type CalculateRequest,
  type CalculateResponse,
  type Municipality,
  type TaxCardType,
} from "@/lib/api";
import { loadLastInputs, saveLastInputs } from "@/lib/storage";

type IncomeMode = "hourly_wage" | "fixed_salary" | null;

type Period = "monthly" | "annual";

interface FormState {
  incomeMode: IncomeMode;
  hourlyWage: string;
  hours: string;
  minutes: string;
  fixedSalary: string;
  municipalityName: string;
  isChurchMember: boolean | null;
  age: string;
  tips: string;
  extraDeduction: string;
  useTaxCard: boolean;
  taxCardType: TaxCardType;
  taxCardPercentage: string;
  taxCardMonthlyDeduction: string;
  remainingFrikortAmount: string;
  period: Period;
}

const DEFAULT_STATE: FormState = {
  incomeMode: null,
  hourlyWage: "",
  hours: "",
  minutes: "0",
  fixedSalary: "",
  municipalityName: "København",
  isChurchMember: null,
  age: "",
  tips: "",
  extraDeduction: "",
  useTaxCard: false,
  taxCardType: "hovedkort",
  taxCardPercentage: "",
  taxCardMonthlyDeduction: "",
  remainingFrikortAmount: "",
  period: "monthly",
};

export default function Home() {
  const [municipalities, setMunicipalities] = useState<Municipality[]>([]);
  const [form, setForm] = useState<FormState>(DEFAULT_STATE);
  const [result, setResult] = useState<CalculateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMunicipalities().then(setMunicipalities).catch(() => setError("Could not load municipality list."));
    const saved = loadLastInputs<FormState>();
    if (saved) setForm((f) => ({ ...f, ...saved }));
  }, []);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  const taxCardFieldsComplete =
    form.taxCardType === "frikort"
      ? form.remainingFrikortAmount !== ""
      : form.taxCardPercentage !== "" &&
        (form.taxCardType === "bikort" || form.taxCardMonthlyDeduction !== "");

  const canCalculate =
    form.incomeMode !== null &&
    form.isChurchMember !== null &&
    form.municipalityName &&
    (form.incomeMode === "hourly_wage"
      ? form.hourlyWage !== "" && form.hours !== ""
      : form.fixedSalary !== "") &&
    (!form.useTaxCard || taxCardFieldsComplete);

  async function handleCalculate() {
    if (!canCalculate || !form.incomeMode) return;
    setLoading(true);
    setError(null);

    const req: CalculateRequest = {
      income_type: form.incomeMode,
      municipality_name: form.municipalityName,
      is_church_member: !!form.isChurchMember,
      age: form.age !== "" ? parseInt(form.age, 10) : undefined,
      tips: form.tips !== "" ? parseFloat(form.tips) : undefined,
      extra_deduction: form.extraDeduction !== "" ? parseFloat(form.extraDeduction) : undefined,
      tax_card_mode: form.useTaxCard ? "my_tax_card" : "standard_estimate",
      tax_card_type: form.taxCardType,
      period: form.period,
      ...(form.incomeMode === "hourly_wage"
        ? {
            hourly_wage: parseFloat(form.hourlyWage),
            hours: parseInt(form.hours, 10),
            minutes: parseInt(form.minutes || "0", 10),
          }
        : { fixed_monthly_salary: parseFloat(form.fixedSalary) }),
      ...(form.useTaxCard && form.taxCardType === "frikort"
        ? { remaining_frikort_amount: parseFloat(form.remainingFrikortAmount) }
        : {}),
      ...(form.useTaxCard && form.taxCardType !== "frikort"
        ? {
            tax_card_percentage: parseFloat(form.taxCardPercentage) / 100,
            ...(form.taxCardType === "hovedkort"
              ? { tax_card_monthly_deduction: parseFloat(form.taxCardMonthlyDeduction) }
              : {}),
          }
        : {}),
    };

    try {
      const res = await calculate(req);
      setResult(res);
      saveLastInputs(form);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  if (result) {
    return (
      <main>
        <ResultBreakdown result={result} onBack={() => setResult(null)} />
      </main>
    );
  }

  return (
    <main>
      <h1>MIN LØN</h1>
      <p className="subtitle">Calculate your estimated Danish net salary — 2026 rules</p>

      {error && <div className="error-box">{error}</div>}

      <div className="card">
        <label className="field-label">How are you paid?</label>
        <div className="toggle-group">
          <button
            type="button"
            className={`toggle-btn ${form.incomeMode === "hourly_wage" ? "active" : ""}`}
            onClick={() => update("incomeMode", "hourly_wage")}
          >
            Monthly Wage
          </button>
          <button
            type="button"
            className={`toggle-btn ${form.incomeMode === "fixed_salary" ? "active" : ""}`}
            onClick={() => update("incomeMode", "fixed_salary")}
          >
            Monthly Salary
          </button>
        </div>
      </div>

      {form.incomeMode === "hourly_wage" && (
        <div className="card">
          <div className="field">
            <label className="field-label" htmlFor="hourly-wage">
              Hourly wage (DKK/hour)
            </label>
            <input
              id="hourly-wage"
              type="number"
              inputMode="decimal"
              min={0}
              value={form.hourlyWage}
              onChange={(e) => update("hourlyWage", e.target.value)}
              placeholder="e.g. 150"
            />
          </div>
          <div className="row">
            <div className="field">
              <label className="field-label" htmlFor="hours">
                Hours worked
              </label>
              <input
                id="hours"
                type="number"
                inputMode="numeric"
                min={0}
                value={form.hours}
                onChange={(e) => update("hours", e.target.value)}
                placeholder="e.g. 160"
              />
            </div>
            <div className="field">
              <label className="field-label" htmlFor="minutes">
                Minutes
              </label>
              <input
                id="minutes"
                type="number"
                inputMode="numeric"
                min={0}
                max={59}
                value={form.minutes}
                onChange={(e) => update("minutes", e.target.value)}
              />
            </div>
          </div>
        </div>
      )}

      {form.incomeMode === "fixed_salary" && (
        <div className="card">
          <div className="field">
            <label className="field-label" htmlFor="fixed-salary">
              Fixed monthly salary (DKK)
            </label>
            <input
              id="fixed-salary"
              type="number"
              inputMode="decimal"
              min={0}
              value={form.fixedSalary}
              onChange={(e) => update("fixedSalary", e.target.value)}
              placeholder="e.g. 30000"
            />
          </div>
        </div>
      )}

      {form.incomeMode && (
        <div className="card">
          <MunicipalitySearch
            municipalities={municipalities}
            value={form.municipalityName}
            onChange={(name) => update("municipalityName", name)}
          />

          <div className="field">
            <label className="field-label">Are you a member of Folkekirken?</label>
            <div className="toggle-group">
              <button
                type="button"
                className={`toggle-btn ${form.isChurchMember === true ? "active" : ""}`}
                onClick={() => update("isChurchMember", true)}
              >
                Yes
              </button>
              <button
                type="button"
                className={`toggle-btn ${form.isChurchMember === false ? "active" : ""}`}
                onClick={() => update("isChurchMember", false)}
              >
                No
              </button>
            </div>
          </div>

          <div className="field">
            <label className="field-label" htmlFor="age">
              Age (Optional)
            </label>
            <input
              id="age"
              type="number"
              inputMode="numeric"
              min={0}
              max={120}
              value={form.age}
              onChange={(e) => update("age", e.target.value)}
              placeholder="e.g. 25"
              style={{ maxWidth: 160 }}
            />
            <p className="hint" style={{ marginTop: 4 }}>
              Your age is required because Danish tax rules for 2026 treat AM-bidrag
              differently depending on your age.
            </p>
          </div>

          <div className="field">
            <label className="field-label">How should we calculate this?</label>
            <div className="toggle-group">
              <button
                type="button"
                className={`toggle-btn ${form.period === "monthly" ? "active" : ""}`}
                onClick={() => update("period", "monthly")}
              >
                Monthly withholding
              </button>
              <button
                type="button"
                className={`toggle-btn ${form.period === "annual" ? "active" : ""}`}
                onClick={() => update("period", "annual")}
              >
                Annual tax estimate
              </button>
            </div>
            <p className="hint">
              {form.period === "monthly"
                ? "Monthly withholding estimate: what a typical month's payslip might show, based on this month's income."
                : "Annual tax estimate: your full-year tax, using the true yearly brackets and allowances rather than a monthly approximation."}
            </p>
          </div>

          <div className="row">
            <div className="field">
              <label className="field-label" htmlFor="tips">
                Estimated Tip (Optional)
              </label>
              <input
                id="tips"
                type="number"
                inputMode="decimal"
                min={0}
                value={form.tips}
                onChange={(e) => update("tips", e.target.value)}
                placeholder="e.g. 500"
              />
            </div>
            <div className="field">
              <label className="field-label" htmlFor="extra-deduction">
                Additional deduction (Optional)
              </label>
              <input
                id="extra-deduction"
                type="number"
                inputMode="decimal"
                min={0}
                value={form.extraDeduction}
                onChange={(e) => update("extraDeduction", e.target.value)}
                placeholder="e.g. union dues"
              />
            </div>
          </div>
          <p className="hint" style={{ marginTop: -8, marginBottom: 16 }}>
            Tips are taxed as ordinary income, added before tax. The additional
            deduction reduces your municipal/church tax base — it&apos;s on top of the
            automatic 2026 personal allowance, not a replacement for it.
          </p>

          <div className="field">
            <label className="field-label">Tax card</label>
            <div className="toggle-group">
              <button
                type="button"
                className={`toggle-btn ${!form.useTaxCard ? "active" : ""}`}
                onClick={() => update("useTaxCard", false)}
              >
                Standard estimate
              </button>
              <button
                type="button"
                className={`toggle-btn ${form.useTaxCard ? "active" : ""}`}
                onClick={() => update("useTaxCard", true)}
              >
                Use my tax card
              </button>
            </div>
            <p className="hint">
              Standard estimate uses the 2026 brackets and allowances. &ldquo;Use my
              tax card&rdquo; applies your actual SKAT withholding percentage instead.
            </p>
          </div>

          {form.useTaxCard && (
            <>
              <div className="field">
                <label className="field-label">Card type</label>
                <div className="toggle-group">
                  <button
                    type="button"
                    className={`toggle-btn ${form.taxCardType === "hovedkort" ? "active" : ""}`}
                    onClick={() => update("taxCardType", "hovedkort")}
                  >
                    Hovedkort
                  </button>
                  <button
                    type="button"
                    className={`toggle-btn ${form.taxCardType === "bikort" ? "active" : ""}`}
                    onClick={() => update("taxCardType", "bikort")}
                  >
                    Bikort
                  </button>
                  <button
                    type="button"
                    className={`toggle-btn ${form.taxCardType === "frikort" ? "active" : ""}`}
                    onClick={() => update("taxCardType", "frikort")}
                  >
                    Frikort
                  </button>
                </div>
              </div>

              {form.taxCardType === "frikort" ? (
                <div className="field">
                  <label className="field-label" htmlFor="frikort-amount">
                    Remaining Frikort amount (DKK)
                  </label>
                  <input
                    id="frikort-amount"
                    type="number"
                    inputMode="decimal"
                    min={0}
                    value={form.remainingFrikortAmount}
                    onChange={(e) => update("remainingFrikortAmount", e.target.value)}
                    placeholder="e.g. 10000"
                  />
                  <p className="hint">
                    This is the tax-free balance left on your forskudsopgørelse — not your
                    annual personal allowance (personfradrag). We can only estimate Frikort
                    correctly when this period&apos;s income fits within that remaining
                    balance; if it doesn&apos;t, we&apos;ll ask you to use Bikort instead
                    rather than guess.
                  </p>
                </div>
              ) : (
                <div className="row">
                  <div className="field">
                    <label className="field-label" htmlFor="tax-card-pct">
                      Withholding %
                    </label>
                    <input
                      id="tax-card-pct"
                      type="number"
                      inputMode="decimal"
                      min={0}
                      max={100}
                      value={form.taxCardPercentage}
                      onChange={(e) => update("taxCardPercentage", e.target.value)}
                      placeholder="e.g. 37"
                    />
                  </div>
                  {form.taxCardType === "hovedkort" && (
                    <div className="field">
                      <label className="field-label" htmlFor="tax-card-deduction">
                        Monthly deduction (DKK)
                      </label>
                      <input
                        id="tax-card-deduction"
                        type="number"
                        inputMode="decimal"
                        min={0}
                        value={form.taxCardMonthlyDeduction}
                        onChange={(e) => update("taxCardMonthlyDeduction", e.target.value)}
                        placeholder="e.g. 4508"
                      />
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          <button
            className="calculate-btn"
            disabled={!canCalculate || loading}
            onClick={handleCalculate}
          >
            {loading ? "Calculating..." : "Calculate"}
          </button>
        </div>
      )}
    </main>
  );
}
