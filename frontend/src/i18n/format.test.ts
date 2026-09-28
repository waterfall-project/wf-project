// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { afterEach, describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { example } from "@/test/fixtures";

import { formatDecimal, formatMoney, formatPlanningDate, formatTimestamp } from "./format";

// French separates thousands with a narrow no-break space; the Vérif writes a plain space,
// which the projection of the document does not tell apart from a typographic one.
const NARROW = "\u202F";
const NO_BREAK = "\u00A0";

/** A display with its typographic spaces made plain, as the document compares its texts. */
function plain(text: string): string {
  return text.replaceAll(/[\u202F\u00A0]/g, " ");
}

/** The decimal a display shows, read back digit by digit — never through a float. */
function readBack(text: string, decimalSeparator: "," | "."): string {
  const kept = text.replaceAll(decimalSeparator === "," ? /[^\d,]/g : /[^\d.]/g, "");
  return kept.replace(decimalSeparator, ".");
}

describe("an amount", () => {
  it("shows 1 234,56 in French and 1,234.56 in English [WF-INTF-0180-A]", () => {
    expect(formatMoney("1234.56", "fr")).toBe(`1${NARROW}234,56`);
    expect(plain(formatMoney("1234.56", "fr"))).toBe("1 234,56");
    expect(formatMoney("1234.56", "en")).toBe("1,234.56");
  });

  it("shows the same total of the project in both languages [WF-INTF-0180-A]", () => {
    const nodes = example("nodes") as { totals: components["schemas"]["NodeTotals"] };
    const total = nodes.totals.budgeted_amount;
    const french = formatMoney(total, "fr");
    const english = formatMoney(total, "en");
    expect(plain(french)).toBe("100 000,00");
    expect(english).toBe("100,000.00");
    expect(readBack(french, ",")).toBe(total);
    expect(readBack(english, ".")).toBe(total);
  });

  it("carries the currency of the installation when given one", () => {
    expect(formatMoney("1234.56", "fr", "EUR")).toBe(`1${NARROW}234,56${NO_BREAK}€`);
    expect(formatMoney("1234.56", "en", "EUR")).toBe("€1,234.56");
    expect(formatMoney("-0.5", "en", "USD")).toBe("-$0.50");
  });

  it("keeps every digit, where a float would lose them", () => {
    const large = "12345678901234567.89";
    expect(String(Number(large))).not.toContain("67.89");
    expect(formatMoney(large, "en")).toBe("12,345,678,901,234,567.89");
  });

  it("shows two decimals, and refuses what the contract would not send rather than round it", () => {
    expect(formatMoney("1234", "fr")).toBe(`1${NARROW}234,00`);
    expect(() => formatMoney("1.234", "en")).toThrow(RangeError);
    expect(() => formatMoney("1e3", "en")).toThrow(RangeError);
    expect(() => formatMoney("1,5", "fr")).toThrow(RangeError);
  });
});

describe("a decimal", () => {
  it("shows every digit the API gave, no more, no fewer", () => {
    expect(formatDecimal("37.5", "fr")).toBe("37,5");
    expect(formatDecimal("1234.50", "en")).toBe("1,234.50");
    expect(formatDecimal("7", "en")).toBe("7");
    expect(formatDecimal("-0.000125", "fr")).toBe("-0,000125");
    expect(formatDecimal("0.1000000000000000055511151231257827", "en")).toBe(
      "0.1000000000000000055511151231257827",
    );
  });

  it("refuses what is not a decimal of the contract", () => {
    expect(() => formatDecimal("NaN", "fr")).toThrow(RangeError);
    expect(() => formatDecimal(" 1", "fr")).toThrow(RangeError);
    expect(() => formatDecimal("", "fr")).toThrow(RangeError);
  });
});

describe("a planning date", () => {
  const original = process.env.TZ;

  afterEach(() => {
    process.env.TZ = original;
  });

  // From fourteen hours ahead of UTC to eleven behind: a date read as midnight in the zone
  // of the workstation would fall on the 29th west of Greenwich.
  it.each([
    "Pacific/Kiritimati",
    "Europe/Paris",
    "UTC",
    "America/Los_Angeles",
    "Pacific/Pago_Pago",
  ])("shows a task planned on 30 June on 30 June, in the zone %s [WF-DAT-0100-A]", (zone) => {
    process.env.TZ = zone;
    expect(new Date("2026-06-30T00:00:00").getTimezoneOffset()).toBe(
      new Date("2026-06-30T12:00:00").getTimezoneOffset(),
    );
    expect(formatPlanningDate("2026-06-30", "fr", "long")).toBe("30 juin 2026");
    expect(formatPlanningDate("2026-06-30", "en", "long")).toBe("June 30, 2026");
    expect(formatPlanningDate("2026-06-30", "fr", "short")).toBe("30/06/2026");
    expect(formatPlanningDate("2026-06-30", "en")).toBe("Jun 30, 2026");
  });

  it("is the zone a naive reading would get wrong", () => {
    process.env.TZ = "America/Los_Angeles";
    expect(new Date("2026-06-30").getDate()).toBe(29);
  });

  it("refuses what is not a date of the contract", () => {
    expect(() => formatPlanningDate("30/06/2026", "fr")).toThrow(RangeError);
    expect(() => formatPlanningDate("2026-06-30T00:00:00Z", "fr")).toThrow(RangeError);
    expect(() => formatPlanningDate("2026-02-30", "fr")).toThrow(RangeError);
    expect(() => formatPlanningDate("2026-13-01", "fr")).toThrow(RangeError);
  });
});

describe("a timestamp", () => {
  const original = process.env.TZ;

  afterEach(() => {
    process.env.TZ = original;
  });

  it("shows in the local time of the workstation", () => {
    const instant = "2026-06-30T23:30:00Z";
    process.env.TZ = "Europe/Paris";
    expect(formatTimestamp(instant, "fr")).toBe("1 juil. 2026, 01:30");
    process.env.TZ = "America/Los_Angeles";
    expect(formatTimestamp(instant, "fr")).toBe("30 juin 2026, 16:30");
    expect(plain(formatTimestamp(instant, "en"))).toBe("Jun 30, 2026, 4:30 PM");
  });

  it("shows in a given zone when one is named", () => {
    process.env.TZ = "America/Los_Angeles";
    expect(plain(formatTimestamp("2026-06-30T23:30:00Z", "en", "Asia/Tokyo"))).toBe(
      "Jul 1, 2026, 8:30 AM",
    );
  });
});
