// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import {
  browserLocale,
  isLanguagePreference,
  isLocale,
  LOCALES,
  PREFERENCES,
  resolveLocale,
} from "./locale";

describe("the offered languages", () => {
  it("are French, the reference, then English", () => {
    expect(LOCALES).toEqual(["fr", "en"]);
    expect(PREFERENCES).toEqual(["default", "fr", "en"]);
  });

  it("tell an offered language and a preference from anything else", () => {
    expect(isLocale("en")).toBe(true);
    expect(isLocale("default")).toBe(false);
    expect(isLocale("de")).toBe(false);
    expect(isLanguagePreference("default")).toBe(true);
    expect(isLanguagePreference("fr")).toBe(true);
    expect(isLanguagePreference("de")).toBe(false);
    expect(isLanguagePreference(undefined)).toBe(false);
  });
});

describe("the language a browser asks for", () => {
  it.each([
    ["en-US,en;q=0.9", "en"],
    ["en-GB", "en"],
    ["fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7", "fr"],
    ["fr-CA", "fr"],
  ])(
    "is English for an English browser and French for a French one: %s [WF-INTF-0160-A]",
    (header, locale) => {
      expect(browserLocale(header)).toBe(locale);
    },
  );

  it("is the first offered language, by weight rather than by position", () => {
    expect(browserLocale("de-DE,de;q=0.9,en;q=0.8,fr;q=0.7")).toBe("en");
    expect(browserLocale("fr;q=0.5, en;q=0.8")).toBe("en");
    expect(browserLocale("fr;q=0.8, en;q=0.8")).toBe("fr");
    expect(browserLocale("EN-us ; q=1.000")).toBe("en");
  });

  it("is none for a browser that asks only for languages not offered [WF-INTF-0160-A]", () => {
    expect(browserLocale("de-DE,de;q=0.9")).toBeUndefined();
    expect(browserLocale("es, it;q=0.5")).toBeUndefined();
  });

  it("is none for a browser that asks for nothing", () => {
    expect(browserLocale(null)).toBeUndefined();
    expect(browserLocale(undefined)).toBeUndefined();
    expect(browserLocale("")).toBeUndefined();
  });

  it("is left to the installation when any language will do before an offered one", () => {
    expect(browserLocale("de, *;q=0.5, en;q=0.3")).toBeUndefined();
    expect(browserLocale("en, *;q=0.5")).toBe("en");
  });

  it("ignores what the browser refuses, and what is malformed", () => {
    expect(browserLocale("en;q=0, fr;q=0.1")).toBe("fr");
    expect(browserLocale("en;q=2, fr;q=0.5")).toBe("fr");
    expect(browserLocale("en;q=abc, fr")).toBe("fr");
    expect(browserLocale("en_US, fr")).toBe("fr");
    expect(browserLocale("en;level=1")).toBeUndefined();
  });
});

describe("the language of a request", () => {
  it("is the one the account chose, whatever the browser asks for", () => {
    expect(resolveLocale("fr", "en-US,en;q=0.9")).toBe("fr");
    expect(resolveLocale("en", "fr-FR")).toBe("en");
    expect(resolveLocale("en", null)).toBe("en");
  });

  it("follows the browser when the account follows it [WF-INTF-0160-A]", () => {
    expect(resolveLocale("default", "en-US,en;q=0.9")).toBe("en");
    expect(resolveLocale("default", "fr-FR,fr;q=0.9")).toBe("fr");
    expect(resolveLocale(undefined, "en")).toBe("en");
  });

  it("is left to the installation when the browser asks for no offered language [WF-INTF-0160-A]", () => {
    expect(resolveLocale("default", "de-DE,de;q=0.9")).toBeUndefined();
    expect(resolveLocale(undefined, null)).toBeUndefined();
  });
});
