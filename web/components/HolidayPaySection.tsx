"use client";

import type { HolidayPay } from "@/lib/api";

// Matches the reference app's plain st.write lines exactly: gross/net use
// two decimals, no thousands separator; the tax component lines are plain
// rounded integers, no thousands separator either.
function formatDKK2(amount: number): string {
  return amount.toFixed(2) + " DKK";
}

function formatDKK0(amount: number): string {
  return Math.round(amount).toString() + " DKK";
}

export default function HolidayPaySection({ holidayPay }: { holidayPay: HolidayPay }) {
  return (
    <div className="card">
      <h2 style={{ fontSize: "1.05rem", marginTop: 0 }}>🏖️ Holiday Pay Breakdown (in DKK)</h2>
      <p style={{ margin: "4px 0" }}>
        Gross Holiday Pay: <strong>{formatDKK2(holidayPay.gross)}</strong>
      </p>
      <p style={{ margin: "4px 0" }}>
        – AM-bidrag (8%): <strong>{formatDKK0(holidayPay.am_bidrag)}</strong>
      </p>
      <p style={{ margin: "4px 0" }}>
        – Income tax: <strong>{formatDKK0(holidayPay.income_tax)}</strong>
      </p>
      <p style={{ margin: "4px 0" }}>
        🚪 Net Holiday Pay: <strong>{formatDKK2(holidayPay.net)}</strong>
      </p>
    </div>
  );
}
