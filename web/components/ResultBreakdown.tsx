"use client";

import { useEffect, useState } from "react";
import type { CalculateResponse, Municipality } from "@/lib/api";
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

function formatDKKStat(amount: number): string {
  return (
    new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount) + " DKK"
  );
}

function formatDKKLine(amount: number): string {
  return Math.round(amount).toString() + " DKK";
}

const METHOD_LABELS: Record<string, string> = {
  standard_estimate: "Standard estimate (2026 rules)",
  tax_card: "Your tax card figures",
  frikort: "Frikort (tax-free up to your balance)",
  monthly_payslip: "Estimated from your municipality and the 2026 rules",
};

export default function ResultBreakdown({
  result,
  municipalities,
}: {
  result: CalculateResponse;
  municipalities: Municipality[];
}) {
  const municipality = municipalities.find((m) => m.name === result.municipality_name);
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
  // Percentage suffixes on line labels, matching the old Streamlit app's
  // "AM-bidrag (8%)" / "A-skat (38%)" style, using our real (not flat-guessed)
  // rates: 8% is the statutory AM-bidrag rate, municipal/church rates come
  // from the selected municipality, and the A-tax/withheld rate comes from
  // whichever percentage the calculation actually used.
  const pct = (fraction: number) => `${(fraction * 100).toFixed(2).replace(/\.?0+$/, "")}%`;
  const amBidragLabel = "AM-bidrag (8%)";
  const municipalTaxLabel =
    municipality != null ? `Municipal tax (${pct(municipality.municipal_tax_rate)})` : "Municipal tax";
  const churchTaxLabel =
    municipality != null ? `Church tax (${pct(municipality.church_tax_rate)})` : "Church tax";
  const withheldRateLabel =
    result.tax_percentage_used != null ? ` (${pct(result.tax_percentage_used)})` : "";

  function labelWithRate(label: string): string {
    if (label === "AM-bidrag") return amBidragLabel;
    if (label === "Municipal tax") return municipalTaxLabel;
    if (label === "Church tax") return churchTaxLabel;
    if (/^A-tax|withheld tax/i.test(label)) return `A-skat${withheldRateLabel}`;
    return label;
  }

  // Lines already shown as the three big stat tiles (Gross/Total tax/Net)
  // are not repeated in the dash-bullet list below them, matching the
  // reference app: the tiles cover the totals, the bullets cover only the
  // components that make them up (ATP, AM-bidrag, fradrag, tax, etc).
  const STAT_TILE_LABELS = new Set([
    "Gross income",
    "Gross salary",
    "Net income",
    "Estimated net salary",
    "Total tax",
  ]);

  const level2Lines: { label: string; rawLabel: string; amount: number }[] = isMonthlyPayslip
    ? result.breakdown
        .filter((l) => !(l.label === "Monthly fradrag" && l.amount === 0))
        .map((l) => ({
          label: labelWithRate(l.label),
          rawLabel: l.label,
          amount: l.amount,
        }))
    : [
        { label: "Gross income", rawLabel: "Gross income", amount: result.gross_income },
        ...(result.tips
          ? [{ label: "of which tips", rawLabel: "of which tips", amount: result.tips }]
          : []),
        { label: "ATP", rawLabel: "ATP", amount: -result.atp_employee_contribution },
        { label: amBidragLabel, rawLabel: "AM-bidrag", amount: -result.am_bidrag },
        ...(isStandard
          ? [
              { label: "State tax", rawLabel: "State tax", amount: -result.state_tax_total },
              {
                label: municipalTaxLabel,
                rawLabel: "Municipal tax",
                amount: -result.municipal_tax,
              },
            ]
          : [
              {
                label: `${isFrikort ? "Income tax (tax-free)" : "A-skat"}${withheldRateLabel}`,
                rawLabel: "Withheld tax",
                amount: -result.state_tax_total,
              },
            ]),
        ...(result.is_church_member && result.church_tax
          ? [{ label: churchTaxLabel, rawLabel: "Church tax", amount: -result.church_tax }]
          : []),
        { label: "Total tax", rawLabel: "Total tax", amount: -result.total_tax },
        { label: "Net income", rawLabel: "Net income", amount: result.net_income },
      ];

  const bulletLines = level2Lines.filter((line) => !STAT_TILE_LABELS.has(line.rawLabel));

  // The reference app lays ATP / AM-bidrag / its income-tax line out in
  // three columns (st.columns(3)), then anything else (its "Other Tax"
  // line) as a plain line below. Our engine has more line items than
  // the old flat model did (fradrag, municipal tax, church tax, ...),
  // so the same three "primary" slots go in the 3-column row and
  // whatever's left goes below, stacked, the same way "Other Tax" did.
  const incomeTaxLine = bulletLines.find((l) =>
    /^(A-tax|withheld tax|State tax|Income tax)/i.test(l.rawLabel)
  );
  const primaryRawLabels = new Set(
    ["ATP", "AM-bidrag", incomeTaxLine?.rawLabel].filter((l): l is string => l != null)
  );
  const primaryLines = ["ATP", "AM-bidrag", incomeTaxLine?.rawLabel]
    .filter((l): l is string => l != null)
    .map((raw) => bulletLines.find((l) => l.rawLabel === raw))
    .filter((l): l is (typeof bulletLines)[number] => l != null);
  const secondaryLines = bulletLines.filter(
    (line) => !primaryRawLabels.has(line.rawLabel)
  );

  return (
    <div>
      {/* Salary Breakdown — one card: the three stat tiles, then a plain
          dash-bulleted list of the components (ATP, AM-bidrag, fradrag,
          tax), matching the reference app's own "Salary Breakdown"
          block instead of splitting it across two differently-styled
          cards. */}
      <Celebration />
      <div className="card">
        {/* st.subheader in the reference app: plain white, bold, normal
            letter-spacing. Deliberately not an <h1>, which carries the
            page title's blue color and 4px tracking. */}
        <h2 className="section-heading">💰 Salary Breakdown (in DKK)</h2>
        <div className="stat-grid">
          <div className="stat-tile">
            <div className="stat-label">Gross Earned</div>
            <div className="stat-value stat-blue">{formatDKKStat(result.gross_income)}</div>
          </div>
          <div className="stat-tile">
            <div className="stat-label">Total Tax Paid</div>
            <div className="stat-value stat-red">{formatDKKStat(result.total_tax)}</div>
          </div>
          <div className="stat-tile">
            <div className="stat-label">Net Earned</div>
            <div className="stat-value stat-green">{formatDKKStat(result.net_income)}</div>
          </div>
        </div>
        {isStandard && (
          <p className="hint" style={{ marginTop: 8 }}>
            This is an estimate, not an exact payslip, it does not use your personal
            SKAT-issued tax card.
          </p>
        )}
        {result.age_am_bidrag_exempt && (
          <p className="hint" style={{ marginTop: 8 }}>
            No AM-bidrag was applied, based on the age you entered.
          </p>
        )}
        <hr className="section-divider" />
        <div className="stat-grid">
          {primaryLines.map((line) => (
            <div key={line.label} className="breakdown-dash-line">
              – {line.label}: {formatDKKLine(Math.abs(line.amount))}
            </div>
          ))}
        </div>
        <div className="effective-rate">
          Effective tax rate: <strong>{(result.effective_tax_rate * 100).toFixed(1)}%</strong>
        </div>
      </div>

      {/* Holiday pay and currency, one click each, right on the main
          screen (matches the old Streamlit app's layout), not tucked
          inside the collapsed details section below. Each is separated
          by a horizontal rule, the same way the reference app does it. */}
      <div className="card">
        <hr className="section-divider" />
        <label className="checkbox-row">
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
        {showHoliday && <hr className="section-divider" />}
        {showHoliday && (
          <label className="checkbox-row">
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

        <hr className="section-divider" />
        <label className="checkbox-row">
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
          {secondaryLines.length > 0 && (
            <>
              <h3 style={{ fontSize: "0.95rem" }}>Calculation steps</h3>
              {secondaryLines.map((line) => (
                <div key={line.label} className="breakdown-line">
                  <span>{line.label}</span>
                  <span className={line.amount < 0 ? "amount-negative" : undefined}>
                    {line.amount < 0 ? "-" : ""}
                    {formatDKK(Math.abs(line.amount))}
                  </span>
                </div>
              ))}
            </>
          )}

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
                {result.tax_percentage_estimated ? " (estimated from your municipality and the 2026 rules)" : ""}.
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
        Estimated from your municipality and the 2026 rules. If you entered your
        monthly fradrag, deductions you have already registered with SKAT, such as
        commuting, are inside that number and are counted. What we estimate is your
        tax percentage, which SKAT sets from the income it expects you to earn across
        the whole year, so your real payslip can still differ.
      </div>
    </div>
  );
}
