// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { estimateReference } from "@/test/reference";

import {
  durationEntered,
  firstChoice,
  parseDuration,
  parsedEntry,
  shownEntry,
  startingText,
} from "./cell-values";
import type { DurationUnit } from "./columns";

const { categories = [], roles = [] } = estimateReference();

describe("a choice searched by what was typed", () => {
  it("is the first of the list whose name starts with it: « Mi » is the commissioning", () => {
    expect(firstChoice(categories, "Mi", "fr")?.id).toBe("01926f3a-7c00-7000-8000-000000000405");
    expect(firstChoice(categories, "Mise en service", "fr")?.label).toBe("Mise en service");
  });

  it("reads neither case nor accents, and skips a deactivated choice", () => {
    expect(firstChoice(roles, "ingenieur", "fr")?.label).toBe("Ingénieur électricien");
    expect(firstChoice(roles, "Auto", "fr")).toBeUndefined();
  });

  it("opens a list at the first choice the character typed starts, at the one made otherwise", () => {
    const kind = { type: "choice", choices: () => categories, nullable: false } as const;
    const made = "01926f3a-7c00-7000-8000-000000000402";
    // The categories come by code: « M » starts the electrical equipment first.
    expect(startingText(kind, made, "M", "fr")).toBe("01926f3a-7c00-7000-8000-000000000403");
    expect(startingText(kind, made, undefined, "fr")).toBe(made);
    expect(startingText(kind, made, "§", "fr")).toBe(made);
  });
});

/** The suffixes of the catalogue of a language, as the grid reads them (`enums.DurationUnit`). */
function suffixes(locale: Locale): (unit: DurationUnit) => string {
  return (unit) => CATALOGUES[locale].enums.DurationUnit[unit];
}

describe("a duration typed with the suffix of its unit", () => {
  it.each(["fr", "en"] as const)(
    "reads « 1 m » as a month and « 1 min » as a minute, in %s [WF-PLA-0160-A]",
    (locale) => {
      // « 1 m » est lu comme un mois et « 1 min » comme une minute, dans chacune des langues de
      // l'interface.
      expect(parseDuration("1 m", locale, suffixes(locale))).toBe("1 mo");
      expect(parseDuration("1 min", locale, suffixes(locale))).toBe("1 min");
      expect(parseDuration("1m", locale, suffixes(locale))).toBe("1 mo");
      expect(parseDuration("1 M", locale, suffixes(locale))).toBe("1 mo");
    },
  );

  it("reads the suffixes the requirement names in either language, and those of the language", () => {
    const fr = suffixes("fr");
    const en = suffixes("en");
    expect(parseDuration("2 j", "fr", fr)).toBe("2 d");
    expect(parseDuration("2 j", "en", en)).toBe("2 d");
    expect(parseDuration("2 d", "en", en)).toBe("2 d");
    expect(parseDuration("1 sem", "en", en)).toBe("1 w");
    expect(parseDuration("1 wk", "en", en)).toBe("1 w");
    expect(parseDuration("2,5 ej", "fr", fr)).toBe("2.5 ed");
    expect(parseDuration("1.5 emo", "en", en)).toBe("1.5 emo");
    expect(parseDuration("3 esem", "fr", fr)).toBe("3 ew");
    expect(parseDuration("4 eh", "fr", fr)).toBe("4 eh");
    expect(parseDuration("30 emin", "fr", fr)).toBe("30 emin");
    // The suffixes of the English catalogue the requirement does not name are not read in French.
    expect(parseDuration("2 d", "fr", fr)).toBeUndefined();
    expect(parseDuration("1 wk", "fr", fr)).toBeUndefined();
    expect(parseDuration("1 mo", "fr", fr)).toBeUndefined();
  });

  it.each(["fr", "en"] as const)(
    "reads every unit of the contract by the suffix the catalogue writes for it, in %s",
    (locale) => {
      // The catalogue names every unit of the contract, which `make catalogs` holds it to.
      for (const [unit, written] of Object.entries(CATALOGUES[locale].enums.DurationUnit)) {
        expect(parseDuration(`3 ${written}`, locale, suffixes(locale))).toBe(`3 ${unit}`);
      }
    },
  );

  it("reads a number alone in days, and refuses a negative duration, a suffix unknown or no number", () => {
    const fr = suffixes("fr");
    expect(parseDuration("5", "fr", fr)).toBe("5 d");
    expect(parseDuration("-1 j", "fr", fr)).toBeUndefined();
    expect(parseDuration("1 an", "fr", fr)).toBeUndefined();
    expect(parseDuration("j", "fr", fr)).toBeUndefined();
    expect(parseDuration("1.5 j", "fr", fr)).toBeUndefined();
  });

  it("starts from the duration with its suffix, and shows what was validated so", () => {
    const kind = {
      type: "duration",
      suffix: suffixes("fr"),
      written: (value: string, unit: DurationUnit) => `${value} ${suffixes("fr")(unit)}`,
    } as const;
    expect(startingText(kind, durationEntered({ value: "2.5", unit: "w" }), undefined, "fr")).toBe(
      "2,5 sem",
    );
    expect(parsedEntry(kind, "2,5 sem", "fr")).toEqual({ value: "2.5 w" });
    expect(parsedEntry(kind, "deux jours", "fr")).toEqual({ problem: "notADuration" });
    expect(shownEntry(kind, "1 mo", "fr")).toBe("1 m");
  });
});

describe("a date of planning typed", () => {
  it("is read in the short form of the language, as the cell starts from it, or in its ISO form", () => {
    const kind = { type: "date" } as const;
    expect(startingText(kind, "2027-01-04", undefined, "fr")).toBe("04/01/2027");
    expect(parsedEntry(kind, "04/01/2027", "fr")).toEqual({ value: "2027-01-04" });
    expect(parsedEntry(kind, "4/1/2027", "en")).toEqual({ value: "2027-01-04" });
    expect(parsedEntry(kind, "2027-01-04", "fr")).toEqual({ value: "2027-01-04" });
    expect(parsedEntry(kind, "30/02/2027", "fr")).toEqual({ problem: "notADate" });
    expect(parsedEntry(kind, "04/01/27", "fr")).toEqual({ problem: "notADate" });
    expect(parsedEntry(kind, "", "fr")).toEqual({ problem: "required" });
  });
});
