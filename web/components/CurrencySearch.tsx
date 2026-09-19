"use client";

import { useMemo, useState } from "react";
import type { Currency } from "@/lib/api";

/** Search by code or name, case-insensitively: "kro" finds Swedish krona and
 *  Norwegian krone, "gbp" finds the British pound. Same interaction as the
 *  municipality picker so the two feel like one app. */
export function matchesCurrencyQuery(currency: Currency, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return (
    currency.code.toLowerCase().includes(q) ||
    currency.name.toLowerCase().includes(q)
  );
}

export default function CurrencySearch({
  currencies,
  value,
  onChange,
}: {
  currencies: Currency[];
  value: string | null;
  onChange: (code: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);

  const filtered = useMemo(
    () => currencies.filter((c) => matchesCurrencyQuery(c, query)),
    [currencies, query]
  );

  const selected = currencies.find((c) => c.code === value) ?? null;

  return (
    <div className="field">
      <label className="field-label" htmlFor="currency-search">
        Convert to which currency?
      </label>
      <input
        id="currency-search"
        type="text"
        placeholder="Search, e.g. euro, SEK, taka"
        value={open ? query : selected ? `${selected.name} (${selected.code})` : ""}
        onFocus={() => {
          setOpen(true);
          setQuery("");
        }}
        onChange={(e) => setQuery(e.target.value)}
      />
      {open && (
        <div className="municipality-results">
          {filtered.map((c) => (
            <div
              key={c.code}
              className="municipality-option"
              onClick={() => {
                onChange(c.code);
                setOpen(false);
              }}
            >
              <span>{c.name}</span>
              <span style={{ color: "var(--text-muted)" }}>{c.code}</span>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="municipality-option">No matches</div>
          )}
        </div>
      )}
    </div>
  );
}
