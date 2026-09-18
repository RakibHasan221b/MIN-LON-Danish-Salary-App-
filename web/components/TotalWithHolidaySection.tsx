"use client";

import type { TotalWithHoliday } from "@/lib/api";

function formatDKK(amount: number): string {
  return new Intl.NumberFormat("da-DK").format(Math.round(amount)) + " kr.";
}

export default function TotalWithHolidaySection({ total }: { total: TotalWithHoliday }) {
  return (
    <div className="card">
      <h2 style={{ fontSize: "1.05rem", marginTop: 0 }}>🧾 Total Including Holiday Pay</h2>
      <div className="breakdown-line">
        <span>Gross + Holiday</span>
        <span>{formatDKK(total.gross)}</span>
      </div>
      <div className="breakdown-line">
        <span>Total Tax Paid</span>
        <span className="amount-negative">-{formatDKK(total.tax)}</span>
      </div>
      <div className="breakdown-line total">
        <span>Net + Holiday</span>
        <span>{formatDKK(total.net)}</span>
      </div>
    </div>
  );
}
