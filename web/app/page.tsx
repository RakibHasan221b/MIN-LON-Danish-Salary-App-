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
  tips: string;
  municipalityName: string;
  churchMembership: ChurchMembership;
  isAdult: boolean | null;
  taxCardChoice: TaxCardChoice;

  // A-card only.
  monthlyDeduction: string;
  // A-card and B-card: the trækprocent printed on the payslip, optional.
  taxPercentage: string;
  // Frikort only.
  remainingFrikortAmount: string;
}

const DEFAULT_STATE: FormState = {
  incomeMode: null,
  hourlyWage: "",
  hours: "",
  minutes: "0",
  fixedSalary: "",
  tips: "",
  municipalityName: "København",
  churchMembership: null,
  isAdult: null,
  taxCardChoice: "a",
  monthlyDeduction: "",
  taxPercentage: "",
  remainingFrikortAmount: "",
};

export default function Home() {
  const [municipalities, setMunicipalities] = useState<Municipality[]>([]);
  const [form, setForm] = useState<FormState>(DEFAULT_STATE);
  const [result, setResult] = useState<CalculateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showFradragHelp, setShowFradragHelp] = useState(false);
  const [showTaxPercentHelp, setShowTaxPercentHelp] = useState(false);

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
      ...(form.tips !== "" ? { tips: parseFloat(form.tips) } : {}),
      ...(form.taxCardChoice === "frikort"
        ? { remaining_frikort_amount: parseFloat(form.remainingFrikortAmount) }
        : {}),
      // A-card: send the fradrag only if the user actually entered one. A
      // blank fradrag is not a fradrag of zero, and the backend now falls
      // back to the standard personal allowance rather than taxing the whole
      // income, so it must be able to tell blank from zero.
      ...(form.taxCardChoice === "a" && form.monthlyDeduction !== ""
        ? { monthly_deduction: parseFloat(form.monthlyDeduction) }
        : {}),
      // B-card (second job): no monthly fradrag of its own.
      ...(form.taxCardChoice === "b" ? { monthly_deduction: 0 } : {}),
      // Trækprocent is a percentage on the payslip (38) but a fraction in
      // the API (0.38). Frikort uses a different path and ignores it.
      ...(form.taxCardChoice !== "frikort" && form.taxPercentage !== ""
        ? { tax_percentage: parseFloat(form.taxPercentage) / 100 }
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

  return (
    <main>
      <h1 className="page-title">Min Løn</h1>
      <p className="subtitle page-title">Your estimated Danish net salary, 2026 rules</p>

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
          <div className="field">
            <label className="field-label" htmlFor="tips">
              Estimated tip (optional)
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
            <p className="hint">
              Tips paid through your payroll. They are taxed like ordinary pay, so
              leave this blank if your tips are cash you receive directly.
            </p>
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
            <label className="field-label">Are you a member of Folkekirken (Church of Denmark)?</label>
            <p className="hint" style={{ marginTop: -4, marginBottom: 8 }}>
              Folkekirken is Denmark&apos;s national Lutheran church. People baptised into it
              stay members until they opt out, and members pay a small church tax on top
              of municipal tax. If you moved to Denmark, you are almost certainly not a
              member.
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
              The A-card is your main job, and most people have this one. The B-card is for
              a second job you hold at the same time, and it carries no tax-free
              allowance of its own. Frikort is the tax-free card you get while your
              yearly income stays under the tax-free allowance. On skat.dk these are
              called hovedkort, bikort and frikort.
            </p>
          </div>

          {form.taxCardChoice === "a" && (
            <div className="field">
              <label className="field-label" htmlFor="monthly-deduction">
                Monthly deduction / Fradrag (DKK){" "}
                <button
                  type="button"
                  aria-label="What is Fradrag?"
                  onClick={() => setShowFradragHelp((v) => !v)}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: 18,
                    height: 18,
                    borderRadius: "50%",
                    border: "1px solid var(--text)",
                    background: "none",
                    color: "var(--text)",
                    fontFamily: "inherit",
                    fontSize: 12,
                    lineHeight: 1,
                    cursor: "pointer",
                    verticalAlign: "middle",
                  }}
                >
                  ?
                </button>
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
                The amount of your monthly salary that is tax-free. Find it on your
                skattekort or payslip.
                <br />
                Example: 5,500 kr.
              </p>
              {showFradragHelp && (
                <p className="hint">
                  <strong>What is Fradrag?</strong>
                  <br />
                  Fradrag is the amount of your monthly income that is deducted before
                  A-skat is calculated. It reduces the amount of your salary that is
                  taxed.
                </p>
              )}
            </div>
          )}

          {form.taxCardChoice !== "frikort" && (
            <div className="field">
              <label className="field-label" htmlFor="tax-percentage">
                Your tax percentage / Trækprocent{" "}
                <button
                  type="button"
                  aria-label="What is Trækprocent?"
                  onClick={() => setShowTaxPercentHelp((v) => !v)}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: 18,
                    height: 18,
                    borderRadius: "50%",
                    border: "1px solid var(--text)",
                    background: "none",
                    color: "var(--text)",
                    fontFamily: "inherit",
                    fontSize: 12,
                    lineHeight: 1,
                    cursor: "pointer",
                    verticalAlign: "middle",
                  }}
                >
                  ?
                </button>
              </label>
              <input
                id="tax-percentage"
                type="number"
                inputMode="decimal"
                min={0}
                max={100}
                value={form.taxPercentage}
                onChange={(e) => update("taxPercentage", e.target.value)}
                placeholder="e.g. 38"
              />
              <p className="hint">
                The percentage used to calculate the A-skat withheld from your salary.
                Find it on your payslip or skattekort.
                <br />
                Example: 38%
              </p>
              {showTaxPercentHelp && (
                <p className="hint">
                  <strong>What is Trækprocent?</strong>
                  <br />
                  Your Trækprocent is the percentage used to calculate the A-skat withheld
                  from your salary. On your payslip, it is usually shown next to A-skat.
                  You can also find it on your skattekort. It is often around
                  37&ndash;38%, but your exact percentage may be different.
                </p>
              )}
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

      {result && <ResultBreakdown result={result} municipalities={municipalities} />}
    </main>
  );
}
