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
} from "@/lib/api";
import { loadLastInputs, saveLastInputs } from "@/lib/storage";

type IncomeMode = "hourly_wage" | "fixed_salary" | null;

// Plain-language tax card choice for the primary flow. "a" and "b" both
// run through the same estimated-from-kommune/church-rules calculation
// (app.calculations.engine._monthly_payslip_estimate): "a" may include
// a monthly fradrag, "b" never does. "frikort" is the one choice that
// still uses the backend's tax_card_mode="my_tax_card" path, unchanged.
type TaxCardChoice = "a" | "b" | "frikort";

type ChurchMembership = "yes" | "no" | "unknown" | null;

interface FormState {
  incomeMode: IncomeMode;
  hourlyWage: string;
  hours: string;
  minutes: string;
  fixedSalary: string;
  municipalityName: string;
  churchMembership: ChurchMembership;
  isAdult: boolean | null;
  taxCardChoice: TaxCardChoice;

  // A-card only.
  monthlyDeduction: string;
  // Frikort only.
  remainingFrikortAmount: string;
}

const DEFAULT_STATE: FormState = {
  incomeMode: null,
  hourlyWage: "",
  hours: "",
  minutes: "0",
  fixedSalary: "",
  municipalityName: "København",
  churchMembership: null,
  isAdult: null,
  taxCardChoice: "a",
  monthlyDeduction: "",
  remainingFrikortAmount: "",
};

export default function Home() {
  const [municipalities, setMunicipalities] = useState<Municipality[]>([]);
  const [form, setForm] = useState<FormState>(DEFAULT_STATE);
  const [result, setResult] = useState<CalculateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMunicipalities().then(setMunicipalities).catch(() => setError("Could not load municipality list."));
    const saved = loadLastInputs<Partial<FormState>>();
    if (saved) setForm((f) => ({ ...f, ...saved }));
  }, []);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  const canCalculate =
    form.incomeMode !== null &&
    form.churchMembership !== null &&
    form.municipalityName !== "" &&
    (form.incomeMode === "hourly_wage"
      ? form.hourlyWage !== "" && form.hours !== ""
      : form.fixedSalary !== "") &&
    (form.taxCardChoice !== "frikort" || form.remainingFrikortAmount !== "");

  async function handleCalculate() {
    if (!canCalculate || !form.incomeMode) return;
    setLoading(true);
    setError(null);

    const req: CalculateRequest = {
      income_type: form.incomeMode,
      municipality_name: form.municipalityName,
      // "I don't know" defaults to not-a-member (the safer assumption:
      // it never charges church tax the user didn't confirm they owe).
      is_church_member: form.churchMembership === "yes",
      age: form.isAdult === false ? 17 : undefined,
      tax_card_mode: form.taxCardChoice === "frikort" ? "my_tax_card" : "standard_estimate",
      tax_card_type: form.taxCardChoice === "frikort" ? "frikort" : "hovedkort",
      period: "monthly",
      ...(form.incomeMode === "hourly_wage"
        ? {
            hourly_wage: parseFloat(form.hourlyWage),
            hours: parseInt(form.hours, 10),
            minutes: parseInt(form.minutes || "0", 10),
          }
        : { fixed_monthly_salary: parseFloat(form.fixedSalary) }),
      ...(form.taxCardChoice === "frikort"
        ? { remaining_frikort_amount: parseFloat(form.remainingFrikortAmount) }
        : {}),
      // A-card: fradrag if entered, otherwise the standard 2026 estimate.
      ...(form.taxCardChoice === "a" && form.monthlyDeduction !== ""
        ? { monthly_deduction: parseFloat(form.monthlyDeduction) }
        : {}),
      // B-card (second job): estimated from kommune/church/2026 rules,
      // deliberately with no monthly fradrag applied.
      ...(form.taxCardChoice === "b" ? { monthly_deduction: 0 } : {}),
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
            Hourly Wage
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
          <div className="row">
            <div className="field">
              <label className="field-label" htmlFor="hours">
                Enter Hours Worked
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
                Enter Minutes Worked
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
            <p className="hint" style={{ marginTop: -4, marginBottom: 8 }}>
              Folkekirken is Denmark&apos;s national (Lutheran) church. Most people born in
              Denmark are automatically members unless they opted out, this affects a small
              church tax. If you moved to Denmark, you likely are not a member.
            </p>
            <div className="toggle-group">
              <button
                type="button"
                className={`toggle-btn ${form.churchMembership === "yes" ? "active" : ""}`}
                onClick={() => update("churchMembership", "yes")}
              >
                Yes
              </button>
              <button
                type="button"
                className={`toggle-btn ${form.churchMembership === "no" ? "active" : ""}`}
                onClick={() => update("churchMembership", "no")}
              >
                No
              </button>
              <button
                type="button"
                className={`toggle-btn ${form.churchMembership === "unknown" ? "active" : ""}`}
                onClick={() => update("churchMembership", "unknown")}
              >
                I don&apos;t know
              </button>
            </div>
            {form.churchMembership === "unknown" && (
              <p className="hint">
                We&apos;ll assume you&apos;re not a member, so we never charge church tax you
                didn&apos;t confirm. Check skat.dk or your skattekort if you want to be sure.
              </p>
            )}
          </div>

          <div className="field">
            <label className="field-label">Are you 18 or older?</label>
            <div className="toggle-group">
              <button
                type="button"
                className={`toggle-btn ${form.isAdult === true ? "active" : ""}`}
                onClick={() => update("isAdult", true)}
              >
                Yes
              </button>
              <button
                type="button"
                className={`toggle-btn ${form.isAdult === false ? "active" : ""}`}
                onClick={() => update("isAdult", false)}
              >
                No
              </button>
            </div>
            <p className="hint">
              Only matters for AM-bidrag, which doesn&apos;t apply if you&apos;re 17 or under.
              Leave unanswered if you&apos;re an adult, it&apos;s the default.
            </p>
          </div>

          <div className="field">
            <label className="field-label">Which tax card is this job on?</label>
            <div className="toggle-group">
              <button
                type="button"
                className={`toggle-btn ${form.taxCardChoice === "a" ? "active" : ""}`}
                onClick={() => update("taxCardChoice", "a")}
              >
                A-card / Main job
              </button>
              <button
                type="button"
                className={`toggle-btn ${form.taxCardChoice === "b" ? "active" : ""}`}
                onClick={() => update("taxCardChoice", "b")}
              >
                B-card / Second job
              </button>
              <button
                type="button"
                className={`toggle-btn ${form.taxCardChoice === "frikort" ? "active" : ""}`}
                onClick={() => update("taxCardChoice", "frikort")}
              >
                Frikort / Tax-free card
              </button>
            </div>
            <p className="hint">
              A-card is your main job, most people have this. B-card is for a second job at
              the same time, it has no tax-free allowance of its own. Frikort is the
              tax-free card students and young people often use, up to a set balance.
            </p>
          </div>

          {form.taxCardChoice === "a" && (
            <div className="field">
              <label className="field-label" htmlFor="monthly-deduction">
                Monthly deduction / Fradrag (DKK, optional)
              </label>
              <input
                id="monthly-deduction"
                type="number"
                inputMode="decimal"
                min={0}
                value={form.monthlyDeduction}
                onChange={(e) => update("monthlyDeduction", e.target.value)}
                placeholder="e.g. 5207"
              />
              <p className="hint">
                Example: 5207 kr. You can find this on your payslip or skattekort. We&apos;ll
                estimate your tax from your municipality and the 2026 rules, no need to know
                your exact tax percentage.
              </p>
            </div>
          )}

          {form.taxCardChoice === "frikort" && (
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
                This is the tax-free balance left on your forskudsopgørelse. If this
                period&apos;s income is within that balance, it&apos;s tax-free; if it goes
                over, we&apos;ll show a clear message instead of guessing.
              </p>
            </div>
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
