"use client";

import type { TotalWithHoliday } from "@/lib/api";

function formatDKK(amount: number): string {
  return new Intl.NumberFormat("da-DK").format(Math.round(amount)) + " kr.";
}

export default function TotalWithHolidaySection({ total }: { total: TotalWithHoliday }) {
  return (
    <div className="card">
      <h2 style={{ fontSize: "1.05rem", marginTop: 0 }}>🧾 Total Including Holiday Pay</h2>
      <div className="stat-grid">
        <div className="stat-tile">
          <div className="stat-label">Gross + Holiday</div>
          <div className="stat-value stat-blue-alt">{formatDKK(total.gross)}</div>
        </div>
        <div className="stat-tile">
          <div className="stat-label">Total Tax Paid</div>
          <div className="stat-value stat-red-alt">-{formatDKK(total.tax)}</div>
        </div>
        <div className="stat-tile">
          <div className="stat-label">Net + Holiday</div>
          <div className="stat-value stat-green-alt">{formatDKK(total.net)}</div>
        </div>
      </div>
    </div>
  );
}
