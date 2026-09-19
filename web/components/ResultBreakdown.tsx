"use client";

import { useEffect, useState } from "react";
import type { CalculateResponse } from "@/lib/api";
import CurrencySection from "@/components/CurrencySection";
import HolidayPaySection from "@/components/HolidayPaySection";
import TotalWithHolidaySection from "@/components/TotalWithHolidaySection";

// A brief, one-shot celebratory burst of emoji when a result appears,
// matching the Streamlit app's animation. Purely decorative and removes
// itself from the DOM once it finishes playing.
const CELEBRATION_EMOJI = ["💰", "🎉", "💸", "✨", "💰", "🎉"];

function Celebration() {
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    const timer = setTimeout(() => setVisible(false), 2600);
    return () => clearTimeout(timer);
  }, []);
  if (!visible) return null;
  return (
    <div className="celebration" aria-hidden="true">
      {CELEBRATION_EMOJI.map((emoji, i) => (
        <span
          key={i}
          className="celebration-emoji"
          style={{
            left: `${8 + i * (84 / CELEBRATION_EMOJI.length)}%`,
            animationDelay: `${i * 0.12}s`,
          }}
        >
          {emoji}
        </span>
      ))}
    </div>
  );
}

function formatDKK(amount: number): string {
  const rounded = Math.round(amount);
  return new Intl.NumberFormat("da-DK").format(rounded) + " kr.";
}

const METHOD_LABELS: Record<string, string> = {
  standard_estimate: "Standard estimate (2026 rules)",
  tax_card: "Your tax card figures",
  frikort: "Frikort (tax-free up to your balance)",
  monthly_payslip: "Estimated from your municipality and the 2026 rules",
};

export default function ResultBreakdown({
  result,
  onBack,
}: {
  result: CalculateResponse;
  onBack: () => void;
}) {
  const isTaxCard = result.calculation_basis === "tax_card";
  const isFrikort = result.calculation_basis === "frikort";
  const isStandard = result.calculation_basis === "standard_estimate";
  const isMonthlyPayslip = result.calculation_basis === "monthly_payslip";
  const [showDetails, setShowDetails] = useState(false);
  const [showHoliday, setShowHoliday] = useState(false);
  const [showTotalWithHoliday, setShowTotalWithHoliday] = useState(false);
  const [showCurrency, setShowCurrency] = useState(false);

  // Level 2: the main breakdown lines. Monthly-first flow (product
  // decision): use the backend's own exact-order breakdown (Gross
  // salary / AM-bidrag / Monthly fradrag / Taxable after fradrag /
  // A-tax / ATP / Estimated net salary), with a zero "Monthly fradrag"
  // line hidden since it means no fradrag was used (e.g. a B-card /
  // second job, which deliberately doesn't apply one) rather than that
  // the line is meaningful at 0.
  const level2Lines: { label: string; amount: number }[] = isMonthlyPayslip
    ? result.breakdown
        .filter((l) => !(l.label === "Monthly fradrag" && l.amount === 0))
        .map((l) => ({ label: l.label, amount: l.amount }))
    : [
        { label: "Gross income", amount: result.gross_income },
        ...(result.tips ? [{ label: "of which tips", amount: result.tips }] : []),
        { label: "ATP", amount: -result.atp_employee_contribution },
        { label: "AM-bidrag", amount: -result.am_bidrag },
        ...(isStandard
          ? [
              { label: "State tax", amount: -result.state_tax_total },
              { label: "Municipal tax", amount: -result.municipal_tax },
            ]
          : [{ label: isFrikort ? "Income tax (tax-free)" : "Withheld tax", amount: -result.state_tax_total }]),
        ...(result.is_church_member && result.church_tax
          ? [{ label: "Church tax", amount: -result.church_tax }]
          : []),
        { label: "Total tax", amount: -result.total_tax },
        { label: "Net income", amount: result.net_income },
      ];

  return (
    <div>
      <button className="back-link" onClick={onBack}>
        ← Edit inputs
      </button>

      {/* LEVEL 1 — main result */}
      <Celebration />
      <div className="card">
        <p className="hint" style={{ marginTop: 0, marginBottom: 4 }}>
          {METHOD_LABELS[result.calculation_basis] || result.calculation_basis}
        </p>
        <h1 style={{ fontSize: "1.15rem", margin: "4px 0 20px" }}>
          💰 Estimated net salary (this month)
        </h1>
        <div className="stat-grid">
          <div className="stat-tile">
            <div className="stat-label">Gross Earned</div>
            <div className="stat-value stat-blue">{formatDKK(result.gross_income)}</div>
          </div>
          <div className="stat-tile">
            <div className="stat-label">Total Tax Paid</div>
            <div className="stat-value stat-red">-{formatDKK(result.total_tax)}</div>
          </div>
          <div className="stat-tile">
            <div className="stat-label">Net Earned</div>
            <div className="stat-value stat-green">{formatDKK(result.net_income)}</div>
          </div>
        </div>
        {isStandard && (
          <p className="hint" style={{ marginTop: 8 }}>
            This is an estimate, not an exact payslip, it does not use your personal
            SKAT-issued tax card.
          </p>
        )}
        {isMonthlyPayslip && (
          <p className="hint" style={{ marginTop: 8 }}>
            {result.tax_percentage_estimated
              ? "We estimated your tax from your municipality, church membership and the 2026 rules, not your actual SKAT-issued tax percentage."
              : "Calculated payslip-style from the monthly deduction and tax percentage you entered, the same way your employer's payroll would."}
          </p>
        )}
        {result.age_am_bidrag_exempt && (
          <p className="hint" style={{ marginTop: 8 }}>
            No AM-bidrag was applied, based on the age you entered.
          </p>
        )}
        <p className="hint" style={{ marginTop: 8 }}>
          Your payslip may differ if your employer deducted ATP or used different
          payroll-period rules.
        </p>
      </div>

      {/* LEVEL 2 — main breakdown */}
      <div className="card">
        <h2 style={{ fontSize: "1.05rem", marginTop: 0 }}>🧮 Breakdown</h2>
        {level2Lines.map((line) => (
          <div
            key={line.label}
            className={`breakdown-line ${
              line.label === "Net income" || line.label === "Estimated net salary" ? "total" : ""
            }`}
          >
            <span>{line.label}</span>
            <span
              className={
                line.amount < 0
                  ? "amount-negative"
                  : ["Net income", "Gross income", "Gross salary", "Estimated net salary", "Taxable after fradrag"].includes(
                      line.label
                    )
                  ? undefined
                  : "amount-positive"
              }
            >
              {line.amount < 0 ? "-" : ""}
              {formatDKK(Math.abs(line.amount))}
            </span>
          </div>
        ))}
        <div className="effective-rate">
          Effective tax rate: <strong>{(result.effective_tax_rate * 100).toFixed(1)}%</strong>
        </div>
      </div>

      {/* Holiday pay and currency, one click each, right on the main
          screen (matches the old Streamlit app's layout), not tucked
          inside the collapsed details section below. */}
      <div className="card">
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 600 }}>
          <input
            type="checkbox"
            checked={showHoliday}
            onChange={(e) => {
              setShowHoliday(e.target.checked);
              if (!e.target.checked) setShowTotalWithHoliday(false);
            }}
          />
          Show Holiday Pay Calculation
        </label>
        {showHoliday && <HolidayPaySection holidayPay={result.holiday_pay} />}
        {showHoliday && (
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              fontWeight: 600,
              marginTop: 12,
            }}
          >
            <input
              type="checkbox"
              checked={showTotalWithHoliday}
              onChange={(e) => setShowTotalWithHoliday(e.target.checked)}
            />
            Show Total Salary Including Holiday Pay
          </label>
        )}
        {showHoliday && showTotalWithHoliday && (
          <TotalWithHolidaySection total={result.total_with_holiday} />
        )}

        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontWeight: 600,
            marginTop: showHoliday ? 20 : 12,
          }}
        >
          <input
            type="checkbox"
            checked={showCurrency}
            onChange={(e) => setShowCurrency(e.target.checked)}
          />
          Enable Currency Conversion
        </label>
        {showCurrency && <CurrencySection result={result} />}
      </div>

      {/* LEVEL 3 — expandable additional details, progressive disclosure */}
      <details className="card" open={showDetails} onToggle={(e) => setShowDetails((e.target as HTMLDetailsElement).open)}>
        <summary style={{ cursor: "pointer", fontWeight: 600 }}>
          Additional details (allowances, assumptions)
        </summary>

        <div style={{ marginTop: 16 }}>
          <h3 style={{ fontSize: "0.95rem" }}>Allowances &amp; deductions</h3>
          {result.employment_allowance > 0 && (
            <div className="breakdown-line">
              <span>Employment allowance</span>
              <span className="amount-positive">{formatDKK(result.employment_allowance)}</span>
            </div>
          )}
          {result.job_allowance > 0 && (
            <div className="breakdown-line">
              <span>Job allowance</span>
              <span className="amount-positive">{formatDKK(result.job_allowance)}</span>
            </div>
          )}
          {result.extra_deduction_applied > 0 && (
            <div className="breakdown-line">
              <span>Additional deduction</span>
              <span className="amount-positive">{formatDKK(result.extra_deduction_applied)}</span>
            </div>
          )}

          {isStandard && (
            <>
              <h3 style={{ fontSize: "0.95rem" }}>State tax, bracket by bracket</h3>
              {result.breakdown
                .filter((l) => ["Bottom tax (bundskat)", "Middle tax (mellemskat)", "Top tax (topskat)", "Additional top tax"].includes(l.label))
                .map((l) => (
                  <div key={l.label} className="breakdown-line">
                    <span>{l.label}</span>
                    <span className={l.amount < 0 ? "amount-negative" : undefined}>
                      {l.amount < 0 ? "-" : ""}
                      {formatDKK(Math.abs(l.amount))}
                    </span>
                  </div>
                ))}
            </>
          )}

          <h3 style={{ fontSize: "0.95rem" }}>Assumptions</h3>
          <p className="hint">
            Method used: {METHOD_LABELS[result.calculation_basis] || result.calculation_basis}.
            {isFrikort && result.remaining_frikort_amount != null && (
              <> Remaining Frikort amount entered: {formatDKK(result.remaining_frikort_amount)}.</>
            )}
            {isMonthlyPayslip && result.tax_percentage_used != null && (
              <>
                {" "}
                Tax percentage used: {(result.tax_percentage_used * 100).toFixed(1)}%
                {result.tax_percentage_estimated ? " (estimated)" : " (as you entered it)"}.
              </>
            )}
          </p>
          {result.assumptions.length > 0 && (
            <ul className="assumption-list">
              {result.assumptions.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          )}
        </div>
      </details>

      <div className="disclaimer">
        Estimated net salary based on 2026 Danish tax rules and the information
        provided. This is{" "}
        {isTaxCard
          ? "based on the tax card figures you supplied"
          : isFrikort
          ? "based on the Frikort balance you supplied"
          : isMonthlyPayslip
          ? result.tax_percentage_estimated
            ? "estimated from your municipality, church membership and the 2026 standard rules"
            : "based on the monthly deduction and tax percentage you supplied"
          : "a standard estimate"}{" "}
        and does not claim to be exactly what your employer will pay you unless your
        actual SKAT tax-card details were used.
      </div>
    </div>
  );
}
