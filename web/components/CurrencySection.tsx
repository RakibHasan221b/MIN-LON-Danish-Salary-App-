"use client";

import { useEffect, useState } from "react";
import CurrencySearch from "@/components/CurrencySearch";
import {
  fetchCurrencies,
  fetchExchangeRate,
  type CalculateResponse,
  type Currency,
} from "@/lib/api";

export default function CurrencySection({ result }: { result: CalculateResponse }) {
  // This component used to render its own "Enable Currency Conversion"
  // checkbox on top of the identical one in ResultBreakdown, so the user had
  // to tick two boxes that looked the same before anything happened. The
  // parent's checkbox is the only one now.
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [currency, setCurrency] = useState<string | null>(null);
  const [includeHoliday, setIncludeHoliday] = useState(false);
  const [liveRate, setLiveRate] = useState<number | null>(null);
  const [rateSource, setRateSource] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [manualRate, setManualRate] = useState("");
  const [useManual, setUseManual] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchCurrencies().then(setCurrencies).catch(() => setCurrencies([]));
  }, []);

  useEffect(() => {
    if (!currency) return;
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
  }, [currency]);

  const effectiveRate = useManual ? parseFloat(manualRate) || null : liveRate;

  const dkkGross = includeHoliday
    ? result.total_with_holiday.gross
    : result.gross_income;
  const dkkNet = includeHoliday ? result.total_with_holiday.net : result.net_income;
  const dkkTax = includeHoliday ? result.total_with_holiday.tax : result.total_tax;

  function formatConverted(amount: number): string {
    // BDT keeps the lakh/crore grouping the original app used for it.
    const locale = currency === "BDT" ? "en-IN" : "en-US";
    return new Intl.NumberFormat(locale, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  }

  return (
    <div className="card" style={{ marginTop: 20 }}>
      <CurrencySearch
        currencies={currencies}
        value={currency}
        onChange={setCurrency}
      />

      {currency && (
        <>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={includeHoliday}
              onChange={(e) => setIncludeHoliday(e.target.checked)}
            />
            Include holiday pay in the conversion
          </label>

          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={useManual}
              onChange={(e) => setUseManual(e.target.checked)}
            />
            Enter the exchange rate myself
          </label>
          {useManual && (
            <div className="field">
              <input
                type="number"
                inputMode="decimal"
                min={0}
                step="0.0001"
                placeholder={`1 DKK = ? ${currency}`}
                value={manualRate}
                onChange={(e) => setManualRate(e.target.value)}
              />
            </div>
          )}

          {loading && <p className="breakdown-dash-line">Fetching exchange rate...</p>}

          {unavailable && !useManual && (
            <div className="error-box">
              Exchange rates are unavailable right now. Your DKK figures above are
              unaffected. Tick the box above to enter a rate yourself.
            </div>
          )}

          {effectiveRate && (
            <>
              <p className="breakdown-dash-line">
                <strong>Current exchange rate:</strong> 1 DKK ={" "}
                {effectiveRate.toFixed(4)} {currency}
                {!useManual && rateSource ? ` (${rateSource})` : ""}
              </p>
              <h2 className="section-heading" style={{ marginTop: 20 }}>
                💵 Converted to {currency}
              </h2>
              <p className="breakdown-dash-line">
                Gross Income:{" "}
                <strong>
                  {formatConverted(dkkGross * effectiveRate)} {currency}
                </strong>
              </p>
              <p className="breakdown-dash-line">
                Net Income:{" "}
                <strong>
                  {formatConverted(dkkNet * effectiveRate)} {currency}
                </strong>
              </p>
              <p className="breakdown-dash-line">
                Total Tax Paid:{" "}
                <strong>
                  {formatConverted(dkkTax * effectiveRate)} {currency}
                </strong>
              </p>
            </>
          )}
        </>
      )}
    </div>
  );
}
