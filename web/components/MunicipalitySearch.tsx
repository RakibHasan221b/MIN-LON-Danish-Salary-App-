"use client";

import { useMemo, useState } from "react";
import type { Municipality } from "@/lib/api";

export default function MunicipalitySearch({
  municipalities,
  value,
  onChange,
}: {
  municipalities: Municipality[];
  value: string;
  onChange: (name: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return municipalities;
    return municipalities.filter((m) => m.name.toLowerCase().includes(q));
  }, [municipalities, query]);

  const selected = municipalities.find((m) => m.name === value);

  return (
    <div className="field">
      <label className="field-label" htmlFor="municipality-search">
        Municipality
      </label>
      <input
        id="municipality-search"
        type="text"
        placeholder="Search municipality..."
        value={open ? query : value}
        onFocus={() => {
          setOpen(true);
          setQuery("");
        }}
        onChange={(e) => setQuery(e.target.value)}
      />
      {open && (
        <div className="municipality-results">
          {filtered.map((m) => (
            <div
              key={m.name}
              className="municipality-option"
              onClick={() => {
                onChange(m.name);
                setOpen(false);
              }}
            >
              <span>{m.name}</span>
              <span style={{ color: "var(--text-muted)" }}>
                {(m.municipal_tax_rate * 100).toFixed(2)}%
              </span>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="municipality-option">No matches</div>
          )}
        </div>
      )}
      {!open && selected && (
        <div className="municipality-selected">
          Municipal tax {(selected.municipal_tax_rate * 100).toFixed(2)}% · Church
          tax {(selected.church_tax_rate * 100).toFixed(2)}%
        </div>
      )}
    </div>
  );
}
