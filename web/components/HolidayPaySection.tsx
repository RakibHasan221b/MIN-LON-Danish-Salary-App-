"use client";

import type { HolidayPay } from "@/lib/api";

function formatDKK(amount: number): string {
  return new Intl.NumberFormat("da-DK").format(Math.round(amount)) + " kr.";
}

export default function HolidayPaySection({ holidayPay }: { holidayPay: HolidayPay }) {
  return (
    <div className="card">
      <h2 style={{ fontSize: "1.05rem", marginTop: 0 }}>🏖️ Holiday Pay</h2>
      <p className="hint" style={{ marginTop: -8, marginBottom: 12 }}>
        Based on {holidayPay.rate_label}. Paid separately — never added to your
        ordinary monthly net salary automatically.
      </p>
      <div className="breakdown-line">
        <span>Gross Holiday Pay</span>
        <span>{formatDKK(holidayPay.gross)}</span>
      </div>
      <div className="breakdown-line">
        <span>AM-bidrag</span>
        <span className="amount-negative">-{formatDKK(holidayPay.am_bidrag)}</span>
      </div>
      <div className="breakdown-line">
        <span>Income tax</span>
        <span className="amount-negative">-{formatDKK(holidayPay.income_tax)}</span>
      </div>
      <div className="breakdown-line total">
        <span>Net Holiday Pay</span>
        <span>{formatDKK(holidayPay.net)}</span>
      </div>
    </div>
  );
}
