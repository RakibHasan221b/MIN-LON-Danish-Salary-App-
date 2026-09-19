/**
 * Accent-insensitive, Danish-letter-tolerant matching for the
 * municipality search box. Pure functions, no React/Next dependency, so
 * they can be exercised by a plain Node test without a test framework.
 *
 * Users without a Danish keyboard shouldn't need to type æ/ø/å: "kob" or
 * "kobenhavn" should still suggest "København". A small alias table also
 * covers common English names ("copenhagen" -> "København").
 */

/** @type {Record<string, string>} */
const DANISH_LETTER_MAP = {
  "æ": "ae",
  "ø": "o",
  "å": "a",
};

/**
 * Lowercases and replaces æ/ø/å with their plain-letter equivalents, so
 * "København" and "kobenhavn" normalize to the same string.
 * @param {string} value
 * @returns {string}
 */
export function normalizeDanishText(value) {
  return value
    .toLowerCase()
    .split("")
    .map((ch) => DANISH_LETTER_MAP[ch] ?? ch)
    .join("")
    .trim();
}

/**
 * Common alternate/English names for municipalities that aren't obvious
 * once Danish letters are stripped to their plain-letter form. Keys are
 * already normalized; values are the normalized municipality name they
 * should match against.
 * @type {Record<string, string>}
 */
export const MUNICIPALITY_ALIASES = {
  copenhagen: "kobenhavn",
};

/**
 * True if `municipalityName` should show up in the results for `query`,
 * ignoring case, Danish special characters, and (for a handful of
 * well-known aliases) the exact Danish spelling.
 * @param {string} municipalityName
 * @param {string} query
 * @returns {boolean}
 */
export function matchesMunicipalityQuery(municipalityName, query) {
  const normalizedQuery = normalizeDanishText(query);
  if (!normalizedQuery) return true;

  const normalizedName = normalizeDanishText(municipalityName);
  if (normalizedName.includes(normalizedQuery)) return true;

  const aliasTarget = MUNICIPALITY_ALIASES[normalizedQuery];
  if (aliasTarget && normalizedName.includes(aliasTarget)) return true;

  return false;
}
