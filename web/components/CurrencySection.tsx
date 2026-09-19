"use client";

import { useEffect, useState } from "react";
import {
  fetchExchangeRate,
  type CalculateResponse,
  type SupportedCurrency,
} from "@/lib/api";

const CURRENCIES: SupportedCurrency[] = ["EUR", "USD", "BDT"];

export default function CurrencySection({ result }: { result: CalculateResponse }) {
  const [enabled, setEnabled] = useState(false);
  const [currency, setCurrency] = useState<SupportedCurrency>("EUR");
  const [includeHoliday, setIncludeHoliday] = useState(false);
  const [liveRate, setLiveRate] = useState<number | null>(null);
  const [rateSource, setRateSource] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [manualRate, setManualRate] = useState("");
  const [useManual, setUseManual] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    setLoading(true);
    setUnavailable(false);
    fetchExchangeRate(currency).then((res) => {
      if (cancelled) return;
      setLoading(false);
      if (res) {
        setLiveRate(res.rate);
        setRateSource(res.source);
        setUnavailable(false);
      } else {
        setLiveRate(null);
        setUnavailable(true);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [enabled, currency]);

  const effectiveRate = useManual ? parseFloat(manualRate) || null : liveRate;

  const dkkGross = includeHoliday
    ? result.total_with_holiday.gross
    : result.gross_income;
  const dkkNet = includeHoliday ? result.total_with_holiday.net : result.net_income;
  const dkkTax = includeHoliday ? result.total_with_holiday.tax : result.total_tax;

  function formatConverted(amount: number): string {
    if (currency === "BDT") {
      return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(amount);
    }
    return amount.toFixed(2);
  }

  return (
    <div className="card">
      <div className="field">
        <label className="field-label" style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
          />
          Enable Currency Conversion
        </label>
      </div>

      {enabled && (
        <>
          <div className="field">
            <label className="field-label" htmlFor="currency-select">
              Currency
            </label>
            <select
              id="currency-select"
              value={currency}
              onChange={(e) => setCurrency(e.target.value as SupportedCurrency)}
            >
              {CURRENCIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 400 }}>
              <input
                type="checkbox"
                checked={includeHoliday}
                onChange={(e) => setIncludeHoliday(e.target.checked)}
              />
              Include Holiday Pay
            </label>
          </div>

          {loading && <p className="hint">Fetching exchange rate…</p>}

          {unavailable && !useManual && (
            <div className="error-box">
              Currency conversion temporarily unavailable. Your DKK results above are
              still accurate. Enter a rate manually below if you have one.
            </div>
          )}

          <div className="field">
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 400 }}>
              <input
                type="checkbox"
                checked={useManual}
                onChange={(e) => setUseManual(e.target.checked)}
              />
              Manual exchange rate
            </label>
            {useManual && (
              <input
                type="number"
                inputMode="decimal"
                min={0}
                step="0.0001"
                placeholder={`1 DKK = X.XXXX ${currency}`}
                value={manualRate}
                onChange={(e) => setManualRate(e.target.value)}
                style={{ marginTop: 8 }}
              />
            )}
          </div>

          {effectiveRate && (
            <>
              <p className="hint">
                Current Exchange Rate: 1 DKK = {effectiveRate.toFixed(4)} {currency}
                {!useManual && rateSource ? ` (${rateSource})` : ""}
              </p>
              <h2 className="section-heading">💵 Converted to {currency}</h2>
              <div className="breakdown-line">
                <span>Gross Income</span>
                <span>
                  {formatConverted(dkkGross * effectiveRate)} {currency}
                </span>
              </div>
              <div className="breakdown-line">
                <span>Net Income</span>
                <span>
                  {formatConverted(dkkNet * effectiveRate)} {currency}
                </span>
              </div>
              <div className="breakdown-line">
                <span>Total Tax Paid</span>
                <span>
                  {formatConverted(dkkTax * effectiveRate)} {currency}
                </span>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
