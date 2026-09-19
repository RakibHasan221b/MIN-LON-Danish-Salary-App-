"use client";

import type { TotalWithHoliday } from "@/lib/api";

// Same "1,050.00 DKK" format as the main stat tiles (comma thousands,
// two decimals), matching the reference app's colored_text() helper,
// which these three tiles reuse for its "Total Salary Including Holiday
// Pay" section too.
function formatDKK(amount: number): string {
  return (
    new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount) + " DKK"
  );
}

export default function TotalWithHolidaySection({ total }: { total: TotalWithHoliday }) {
  return (
    <div className="card">
      <h2 style={{ fontSize: "1.05rem", marginTop: 0 }}>🧾 Total Salary Including Holiday Pay</h2>
      <div className="stat-grid">
        <div className="stat-tile">
          <div className="stat-label">Gross + Holiday</div>
          <div className="stat-value stat-blue-alt">{formatDKK(total.gross)}</div>
        </div>
        <div className="stat-tile">
          <div className="stat-label">Total Tax Paid</div>
          <div className="stat-value stat-red-alt">{formatDKK(total.tax)}</div>
        </div>
        <div className="stat-tile">
          <div className="stat-label">Net + Holiday</div>
          <div className="stat-value stat-green-alt">{formatDKK(total.net)}</div>
        </div>
      </div>
    </div>
  );
}
