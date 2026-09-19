"use client";

import { useMemo, useState } from "react";
import type { Municipality } from "@/lib/api";
import { matchesMunicipalityQuery } from "@/lib/municipalitySearch";

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

  // Accent-insensitive, Danish-letter-tolerant: "kob"/"kobenhavn"/
  // "copenhagen" all suggest "København", no æ/ø/å keyboard needed.
  const filtered = useMemo(() => {
    return municipalities.filter((m) => matchesMunicipalityQuery(m.name, query));
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
        placeholder="Search municipality... (e.g. Copenhagen, kob, Aarhus)"
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
