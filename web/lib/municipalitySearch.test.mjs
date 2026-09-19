import test from "node:test";
import assert from "node:assert/strict";
import {
  normalizeDanishText,
  matchesMunicipalityQuery,
} from "./municipalitySearch.js";

test("normalizeDanishText maps æ/ø/å to plain letters and lowercases", () => {
  assert.equal(normalizeDanishText("København"), "kobenhavn");
  assert.equal(normalizeDanishText("Ærø"), "aero");
  assert.equal(normalizeDanishText("Åbenrå"), "abenra");
  assert.equal(normalizeDanishText("Aalborg"), "aalborg");
});

test("typing without special characters still matches København", () => {
  assert.equal(matchesMunicipalityQuery("København", "kob"), true);
  assert.equal(matchesMunicipalityQuery("København", "kobenhavn"), true);
  assert.equal(matchesMunicipalityQuery("København", "KØBENHAVN"), true);
});

test("the copenhagen alias matches København", () => {
  assert.equal(matchesMunicipalityQuery("København", "copenhagen"), true);
  assert.equal(matchesMunicipalityQuery("Aarhus", "copenhagen"), false);
});

test("municipalities that already spell out æ/ø/å in roman letters still match", () => {
  assert.equal(matchesMunicipalityQuery("Aalborg", "aalborg"), true);
  assert.equal(matchesMunicipalityQuery("Aarhus", "aarhus"), true);
});

test("an empty query matches everything", () => {
  assert.equal(matchesMunicipalityQuery("Aarhus", ""), true);
  assert.equal(matchesMunicipalityQuery("Aarhus", "   "), true);
});

test("a non-matching query returns false", () => {
  assert.equal(matchesMunicipalityQuery("København", "randers"), false);
});
