// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { createTranslator } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { example } from "@/test/fixtures";

import { CATALOGUES } from "./catalogues";
import {
  compareDecimals,
  editableDecimal,
  editablePercent,
  formatBytes,
  formatDecimal,
  formatLocale,
  formatMoney,
  formatPercent,
  formatMonth,
  formatPlanningDate,
  formatShare,
  formatTimestamp,
  localTimeOfDay,
  parseDecimal,
  percentRatio,
  ratioPercent,
} from "./format";
import type { Locale } from "./locale";

// French separates thousands with a narrow no-break space; the Vérif writes a plain space,
// which the projection of the document does not tell apart from a typographic one.
const NARROW = "\u202F";
const NO_BREAK = "\u00A0";

/**
 * Give the process back the time zone it had: none at all when it had none — an environment
 * variable set to `undefined` would be the string « undefined ».
 */
function restoreZone(original: string | undefined): void {
  if (original === undefined) {
    delete process.env.TZ;
  } else {
    process.env.TZ = original;
  }
}

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
    expect(formatMoney("-0.5", "en", "USD")).toBe("-US$0.50");
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

describe("a zero", () => {
  it("shows without a sign, whatever sign the API wrote", () => {
    expect(formatMoney("-0.00", "fr")).toBe("0,00");
    expect(formatMoney("-0", "en", "EUR")).toBe("€0.00");
    expect(formatDecimal("-0.000", "fr")).toBe("0,000");
    expect(formatDecimal("-0.001", "en")).toBe("-0.001");
    expect(formatMoney("-1234.5", "fr")).toBe(`-1${NARROW}234,50`);
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

describe("a number entered", () => {
  it("is written with a comma in French and a point in English, and travels as the exact decimal of the contract", () => {
    expect(parseDecimal("12,5", "fr")).toBe("12.5");
    expect(parseDecimal("12.5", "en")).toBe("12.5");
    // Thousands apart: a space the keyboard types, or the narrow one French writes; commas.
    expect(parseDecimal("1 234,5", "fr")).toBe("1234.5");
    expect(parseDecimal(`1${NARROW}234,5`, "fr")).toBe("1234.5");
    expect(parseDecimal(`1${NO_BREAK}234${NO_BREAK}567`, "fr")).toBe("1234567");
    expect(parseDecimal("1,234.5", "en")).toBe("1234.5");
    expect(parseDecimal(" -7 ", "en")).toBe("-7");
    // Every digit typed, where a float would lose some.
    expect(parseDecimal("0,1000000000000000055511151231257827", "fr")).toBe(
      "0.1000000000000000055511151231257827",
    );
  });

  it("is refused in any other form: the separator of the other language, thousands misplaced, a letter", () => {
    expect(parseDecimal("12.5", "fr")).toBeUndefined();
    expect(parseDecimal("12,5", "en")).toBeUndefined();
    expect(parseDecimal("1 23,5", "fr")).toBeUndefined();
    expect(parseDecimal("1,2,3", "en")).toBeUndefined();
    expect(parseDecimal("12a", "fr")).toBeUndefined();
    expect(parseDecimal("", "en")).toBeUndefined();
  });

  it("keeps two decimals at most for an amount", () => {
    expect(parseDecimal("1 234,56", "fr", "money")).toBe("1234.56");
    expect(parseDecimal("1,234.567", "en", "money")).toBeUndefined();
    expect(parseDecimal("1,234.567", "en")).toBe("1234.567");
  });

  it("starts from the value of the contract, with the decimal separator of the language and no thousands", () => {
    expect(editableDecimal("1234.5", "fr")).toBe("1234,5");
    expect(editableDecimal("1234.5", "en")).toBe("1234.5");
    expect(editableDecimal("7", "fr")).toBe("7");
    expect(() => editableDecimal("1,5", "fr")).toThrow(RangeError);
  });
});

describe("the locale of the formatters", () => {
  it("is British English for English, French for French", () => {
    expect(formatLocale("en")).toBe("en-GB");
    expect(formatLocale("fr")).toBe("fr");
    const list = new Intl.ListFormat(formatLocale("en"), { type: "conjunction" });
    expect(list.format(["a", "b", "c"])).toBe("a, b and c");
  });
});

describe("a size in bytes", () => {
  it("is said in the largest unit it fills, in words, as the installation gives it", () => {
    const { avatar_max_bytes: bound } = example(
      "installation",
    ) as components["schemas"]["Installation"];
    expect(plain(formatBytes(bound, "fr"))).toBe("2 mégaoctets");
    expect(formatBytes(bound, "en")).toBe("2 megabytes");
    expect(plain(formatBytes(512, "fr"))).toBe("512 octets");
    expect(formatBytes(1024, "en")).toBe("1 kilobyte");
  });

  it("keeps a tenth at most, cut, never saying more than the size given", () => {
    expect(plain(formatBytes(1_572_864, "fr"))).toBe("1,5 mégaoctet");
    // 2,097,151 bytes are a byte short of 2 megabytes: never said 2.
    expect(formatBytes(2_097_151, "en")).toBe("1.9 megabytes");
  });
});

describe("a percentage", () => {
  it("shows a ratio of the API as a percentage, with every digit it gave", () => {
    expect(formatPercent("0.25", "fr")).toBe(`25${NO_BREAK}%`);
    expect(formatPercent("0.125", "en")).toBe("12.5%");
    expect(formatPercent("0", "en")).toBe("0%");
    expect(formatPercent("1.5", "fr")).toBe(`150${NO_BREAK}%`);
    expect(formatPercent("-0.03", "en")).toBe("-3%");
    expect(formatPercent("-0.00", "fr")).toBe(`0${NO_BREAK}%`);
  });

  it("never passes through a float, which would add digits", () => {
    expect(String(Number("0.07") * 100)).toBe("7.000000000000001");
    expect(formatPercent("0.07", "en")).toBe("7%");
    const ratio = "0.1000000000000000055511151231257827";
    expect(formatPercent(ratio, "en")).toBe("10.00000000000000055511151231257827%");
  });

  it("refuses what is not a decimal of the contract", () => {
    expect(() => formatPercent("25%", "fr")).toThrow(RangeError);
  });
});

type Schemas = components["schemas"];

describe("a share", () => {
  /** A share in a language, its bounds said by the catalogue of the language. */
  const share = (value: string, locale: Locale) =>
    formatShare(
      value,
      locale,
      createTranslator({ locale, messages: CATALOGUES[locale], namespace: "share" }),
    );

  it.each([
    ["0", `0${NO_BREAK}%`],
    ["-0.00", `0${NO_BREAK}%`],
    ["0.0000", `0${NO_BREAK}%`],
    ["0.0000499999", `<${NO_BREAK}0,01${NO_BREAK}%`],
    ["0.00005", `0,01${NO_BREAK}%`],
    ["-0.0000499999", `>${NO_BREAK}-0,01${NO_BREAK}%`],
    ["-0.00005", `-0,01${NO_BREAK}%`],
    ["-0.0123", `-1,23${NO_BREAK}%`],
    // Near the whole, the ordinary rounding: only the side of zero is said (#626).
    ["0.9999499999", `99,99${NO_BREAK}%`],
    ["0.99995", `100,00${NO_BREAK}%`],
    ["1", `100${NO_BREAK}%`],
    ["1.0000499999", `100,00${NO_BREAK}%`],
  ])("shows %s, rounded to the hundredth, never nil when it is not", (value, shown) => {
    expect(share(value, "fr")).toBe(shown);
  });

  it("shows the share the API gives to its fourth place as formatPercent does, and rounds a longer one", () => {
    expect(share("0.0076", "fr")).toBe(formatPercent("0.0076", "fr"));
    expect(share("0.337", "en")).toBe("33.7%");
    expect(share("0.1300", "en")).toBe("13.00%");
    expect(share("0.1000000000000000055511151231257827", "en")).toBe("10.00%");
  });

  it("says the bound in the words and the format of each language", () => {
    expect(share("0.00003", "en")).toBe("<0.01%");
    expect(share("-0.00003", "en")).toBe(">-0.01%");
  });

  it("says below the smallest shown the share of the contract that rounds to nil while it is not", () => {
    // « Fourniture et montage des armoires » of the offer v1.0: 2 019,56 of 65 427 832,64, which the
    // contract gives to its first significant digit, never nil (EP-14/L42o, #694).
    const indicators = example("estimate_indicators_breakdown") as Schemas["EstimateIndicators"];
    const item = indicators.by_order_item?.[0];
    expect(item?.share?.value).toBe("0.00003");
    expect(share(item?.share?.value ?? "", "fr")).toBe(`<${NO_BREAK}0,01${NO_BREAK}%`);
  });

  it("refuses what is not a decimal of the contract", () => {
    expect(() => share("25%", "fr")).toThrow(RangeError);
  });
});

describe("a percentage entered", () => {
  it("offers a ratio of the API to entry as a percentage, every digit kept", () => {
    expect(editablePercent("0.03", "fr")).toBe("3");
    expect(editablePercent("0.035", "fr")).toBe("3,5");
    expect(editablePercent("0.4", "en")).toBe("40");
    expect(editablePercent("1", "en")).toBe("100");
    expect(editablePercent("0", "fr")).toBe("0");
    expect(editablePercent("-0.025", "en")).toBe("-2.5");
  });

  it("sends a percentage entered as the ratio of the contract, the point moved, never through a float", () => {
    expect(String(Number("0.07") * 100)).toBe("7.000000000000001");
    expect(percentRatio("7")).toBe("0.07");
    expect(percentRatio("3.5")).toBe("0.035");
    expect(percentRatio("40")).toBe("0.4");
    expect(percentRatio("100")).toBe("1");
    expect(percentRatio("0")).toBe("0");
    expect(percentRatio("-2.50")).toBe("-0.025");
    expect(percentRatio("-0")).toBe("0");
    expect(percentRatio("1234.5678")).toBe("12.345678");
    // Each of these would come out of a float with digits of its own.
    expect(String(Number("1.1") / 100)).not.toBe("0.011");
    expect(percentRatio("1.1")).toBe("0.011");
    expect(percentRatio("0.7")).toBe("0.007");
    expect(percentRatio("57")).toBe("0.57");
  });

  it("says a ratio of the contract as the percentage it stands for, as the contract writes a decimal", () => {
    // The bounds of the two rates of a project, which the server gives in ratios (EP-14/L42i).
    expect(ratioPercent("1")).toBe("100");
    expect(ratioPercent("0")).toBe("0");
    expect(ratioPercent("0.035")).toBe("3.5");
    expect(ratioPercent("2026-06-03")).toBeUndefined();
  });
});

describe("two decimals compared", () => {
  it("orders two decimals of the contract by their digits, never through a float", () => {
    expect(compareDecimals("0.1", "0.25")).toBeLessThan(0);
    expect(compareDecimals("0.3", "0.30")).toBe(0);
    expect(compareDecimals("10", "9.99")).toBeGreaterThan(0);
    expect(compareDecimals("-0.5", "0.1")).toBeLessThan(0);
    expect(compareDecimals("-2", "-10")).toBeGreaterThan(0);
    // A float would make the two equal: 2^53 + 1 has no double of its own.
    expect(Number("9007199254740993") === Number("9007199254740992")).toBe(true);
    expect(compareDecimals("9007199254740993", "9007199254740992")).toBeGreaterThan(0);
  });
});

describe("a planning date", () => {
  const original = process.env.TZ;

  afterEach(() => {
    restoreZone(original);
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
    expect(new Intl.DateTimeFormat().resolvedOptions().timeZone).toBe(zone);
    expect(formatPlanningDate("2026-06-30", "fr", "long")).toBe("30 juin 2026");
    expect(formatPlanningDate("2026-06-30", "en", "long")).toBe("30 June 2026");
    expect(formatPlanningDate("2026-06-30", "fr", "short")).toBe("30/06/2026");
    expect(formatPlanningDate("2026-06-30", "en")).toBe("30 Jun 2026");
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

describe("a month", () => {
  const original = process.env.TZ;

  afterEach(() => {
    restoreZone(original);
  });

  it("shows by its name and its year, the same month west of Greenwich [WF-DAT-0100-A]", () => {
    process.env.TZ = "Pacific/Pago_Pago";
    expect(formatMonth("2026-05", "fr")).toBe("mai 2026");
    expect(formatMonth("2026-05", "en")).toBe("May 2026");
  });

  it("refuses what is not a month of the contract", () => {
    expect(() => formatMonth("2026-13", "fr")).toThrow(RangeError);
    expect(() => formatMonth("2026-05-01", "fr")).toThrow(RangeError);
  });
});

describe("a timestamp", () => {
  const original = process.env.TZ;

  afterEach(() => {
    restoreZone(original);
  });

  it("shows in the local time of the workstation, English as British English", () => {
    const instant = "2026-06-30T23:30:00Z";
    process.env.TZ = "Europe/Paris";
    expect(formatTimestamp(instant, "fr")).toBe("1 juil. 2026, 01:30");
    process.env.TZ = "America/Los_Angeles";
    expect(formatTimestamp(instant, "fr")).toBe("30 juin 2026, 16:30");
    expect(formatTimestamp(instant, "en")).toBe("30 Jun 2026, 16:30");
  });

  it("shows in a given zone when one is named", () => {
    process.env.TZ = "America/Los_Angeles";
    expect(formatTimestamp("2026-06-30T23:30:00Z", "en", "Asia/Tokyo")).toBe("1 Jul 2026, 08:30");
  });
});

describe("the formatters of Intl", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("are built once for a language and options, then kept for every cell a grid formats (#398)", () => {
    // Built by an earlier call, or by the first of these: never once a cell.
    const numbers = vi.spyOn(Intl, "NumberFormat");
    const dates = vi.spyOn(Intl, "DateTimeFormat");
    const amounts = Array.from({ length: 200 }, (_, row) => formatMoney(`${String(row)}.50`, "fr"));
    const days = Array.from({ length: 200 }, () => formatPlanningDate("2026-06-30", "en"));
    expect(amounts[123]).toBe("123,50");
    expect(days[199]).toBe("30 Jun 2026");
    expect(numbers.mock.calls.length).toBeLessThanOrEqual(1);
    expect(dates.mock.calls.length).toBeLessThanOrEqual(1);
  });

  it("are kept apart for each language, each number of decimals and each currency", () => {
    expect(formatDecimal("1234.5", "fr")).toBe(`1${NARROW}234,5`);
    expect(formatDecimal("1234.5", "en")).toBe("1,234.5");
    expect(formatDecimal("1234.25", "fr")).toBe(`1${NARROW}234,25`);
    expect(formatDecimal("1234", "fr")).toBe(`1${NARROW}234`);
    expect(formatMoney("1234.5", "fr")).toBe(`1${NARROW}234,50`);
    expect(formatMoney("1234.5", "fr", "EUR")).toBe(`1${NARROW}234,50${NO_BREAK}€`);
    expect(formatMoney("1234.5", "en", "EUR")).toBe("€1,234.50");
    expect(formatPlanningDate("2026-06-30", "fr", "short")).toBe("30/06/2026");
    expect(formatPlanningDate("2026-06-30", "fr")).toBe("30 juin 2026");
  });

  it("of the zone of the workstation are built at each call, and follow a zone changed since", () => {
    const original = process.env.TZ;
    try {
      process.env.TZ = "Asia/Tokyo";
      expect(formatTimestamp("2026-06-30T23:30:00Z", "en")).toBe("1 Jul 2026, 08:30");
      process.env.TZ = "America/Los_Angeles";
      expect(formatTimestamp("2026-06-30T23:30:00Z", "en")).toBe("30 Jun 2026, 16:30");
    } finally {
      restoreZone(original);
    }
  });
});

describe("a time of day in universal time", () => {
  const original = process.env.TZ;

  afterEach(() => {
    restoreZone(original);
  });

  it("stands for the local time of the workstation on the day given, which summer time moves", () => {
    process.env.TZ = "Europe/Paris";
    expect(localTimeOfDay("01:00", new Date("2026-06-03T14:05:00Z"))).toEqual({
      time: "03:00",
      shift: 0,
    });
    expect(localTimeOfDay("01:00", new Date("2026-01-15T14:05:00Z"))).toEqual({
      time: "02:00",
      shift: 0,
    });
    expect(localTimeOfDay("23:30", new Date("2026-06-03T14:05:00Z"))).toEqual({
      time: "01:30",
      shift: 1,
    });
  });

  it("falls the day before west of Greenwich, or in the zone named", () => {
    process.env.TZ = "America/Los_Angeles";
    expect(localTimeOfDay("01:00", new Date("2026-06-03T14:05:00Z"))).toEqual({
      time: "18:00",
      shift: -1,
    });
    expect(localTimeOfDay("01:00", new Date("2026-06-03T14:05:00Z"), "Asia/Tokyo")).toEqual({
      time: "10:00",
      shift: 0,
    });
  });

  it("keeps the half hour of a zone that has one", () => {
    process.env.TZ = "Asia/Kolkata";
    expect(localTimeOfDay("01:00", new Date("2026-06-03T14:05:00Z"))).toEqual({
      time: "06:30",
      shift: 0,
    });
  });

  it("takes the offset of the very day summer time begins, on either side of the change", () => {
    // In Paris, on 29 March 2026, the clocks go from 02:00 to 03:00, at 01:00 in universal time.
    process.env.TZ = "Europe/Paris";
    const change = new Date("2026-03-29T12:00:00Z");
    expect(localTimeOfDay("00:30", change)).toEqual({ time: "01:30", shift: 0 });
    expect(localTimeOfDay("01:00", change)).toEqual({ time: "03:00", shift: 0 });
  });

  it("is none for what is no time of day of the contract", () => {
    const day = new Date("2026-06-03T14:05:00Z");
    expect(localTimeOfDay("", day)).toBeUndefined();
    expect(localTimeOfDay("24:00", day)).toBeUndefined();
    expect(localTimeOfDay("1:00", day)).toBeUndefined();
  });
});
