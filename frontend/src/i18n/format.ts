// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The display formats of the interface, by language, with `Intl` (WF-INTF-0180): the values
 * stay the contract's, only their display changes.
 *
 * - A `Decimal`, `Money` or `Hours` is formatted from the exact string of the contract, never
 *   through a float (WF-DAT-0100): `Intl.NumberFormat` reads a decimal string as a decimal,
 *   and every digit the API gave is shown, no more, no fewer.
 * - A `PlanningDate` has no time and no time zone: it is shown as it is, the same day on
 *   every workstation.
 * - A `Timestamp` is an instant: it is shown in the time zone of the workstation.
 *
 * A zero shows without a sign, even written `-0.00`: `signDisplay: "negative"`.
 *
 * In French, `Intl` separates thousands with a narrow no-break space (U+202F), the French
 * typographic rule: « 1 234,56 » never breaks across two lines. English is formatted as
 * British English, as its catalogue is written: « 31 May 2026, 16:30 », and « 1,234.56 ».
 *
 * A formatter of `Intl` is built once for each language and each set of options, then kept:
 * building one costs some tens of microseconds, and a dense grid formats a cell at every render
 * (#398). Only the formatter is reused; the value, its digits and the text shown are the same.
 */
import type { components } from "@/api/generated/schema";

import type { Locale } from "./locale";

/**
 * The time zone next-intl formats in, the same on the server and in the browser, so that
 * both render the same text. It is never the workstation's: a `PlanningDate` has no zone, and
 * a `Timestamp` is written in the browser by `LocalTime`, not by the formatter of next-intl.
 */
export const TIME_ZONE = "UTC";

/**
 * The locale `Intl` formats each language of the interface in: English is British, the
 * English of the catalogue — the day before the month, the time on 24 hours.
 */
const FORMAT_LOCALE: Readonly<Record<Locale, string>> = { fr: "fr", en: "en-GB" };

/**
 * The locale to build any `Intl` formatter with for a language of the interface — a number,
 * a date, a list —, never the language itself: English is British everywhere it is written.
 */
export function formatLocale(locale: Locale): string {
  return FORMAT_LOCALE[locale];
}

/** The formatters built, by language and options: a few dozen at most, never let go. */
const numberFormats = new Map<string, Intl.NumberFormat>();
const dateFormats = new Map<string, Intl.DateTimeFormat>();

/** The formatter of `Intl` kept for a language and options, built at its first use. */
function kept<O extends object, F>(
  formats: Map<string, F>,
  build: (tag: string, options: O) => F,
  locale: Locale,
  options: O,
): F {
  const key = `${locale}|${JSON.stringify(options)}`;
  const known = formats.get(key);
  if (known !== undefined) {
    return known;
  }
  const built = build(formatLocale(locale), options);
  formats.set(key, built);
  return built;
}

/** The number formatter of a language with options, kept once built. */
function numberFormat(locale: Locale, options: Intl.NumberFormatOptions): Intl.NumberFormat {
  return kept(numberFormats, (tag, given) => new Intl.NumberFormat(tag, given), locale, options);
}

/**
 * The date formatter of a language with options, kept once built — options that name their time
 * zone only: one that does not takes the zone of the workstation as it is built, and a zone
 * changed afterwards would not move a formatter kept from before.
 */
function dateFormat(
  locale: Locale,
  options: Intl.DateTimeFormatOptions & { readonly timeZone: string },
): Intl.DateTimeFormat {
  return kept(dateFormats, (tag, given) => new Intl.DateTimeFormat(tag, given), locale, options);
}

type Decimal = components["schemas"]["Decimal"];
type Money = components["schemas"]["Money"];
type PlanningDate = components["schemas"]["PlanningDate"];
type Timestamp = components["schemas"]["Timestamp"];

// The patterns of `Decimal` and of `Money` in the contract: an amount has two decimals at
// most, so that showing two never rounds it.
const DECIMAL = /^-?\d+(\.\d+)?$/;
const MONEY = /^-?\d+(\.\d{1,2})?$/;
// The ISO form of `PlanningDate`.
const DATE = /^\d{4}-\d{2}-\d{2}$/;

/** A decimal string, which `Intl.NumberFormat` formats without a float. */
type DecimalString = `${number}`;

/** Whether a value matches a pattern of the contract, which makes it a decimal string. */
function isDecimal(value: string, pattern: RegExp): value is DecimalString {
  return pattern.test(value);
}

/**
 * Check that a value has the form the contract gives it, and hand it to `Intl` as the decimal
 * string it is; anything else is a defect of the API, never shown approximately.
 */
function decimal(value: Decimal, pattern = DECIMAL): DecimalString {
  if (!isDecimal(value, pattern)) {
    throw new RangeError(`Not a decimal of the contract: ${JSON.stringify(value)}`);
  }
  return value;
}

/** The number of digits after the point of a decimal string. */
function fractionDigits(value: DecimalString): number {
  return value.split(".")[1]?.length ?? 0;
}

/**
 * Format a `Decimal` — `Hours`, a quantity, a rate — in a language, with every digit the API
 * gave: `1234.5` is « 1 234,5 » in French, `1,234.5` in English.
 */
export function formatDecimal(value: Decimal, locale: Locale): string {
  const exact = decimal(value);
  const digits = fractionDigits(exact);
  return numberFormat(locale, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
    signDisplay: "negative",
  }).format(exact);
}

/** The units a size is said in, each 1,024 times the one before. */
const BYTE_UNITS = ["byte", "kilobyte", "megabyte", "gigabyte"] as const;

/**
 * Format a size in bytes — an integer of the contract, `avatar_max_bytes` — in the largest
 * unit it fills, in words: `2097152` is « 2 mégaoctets » in French, `2 megabytes` in English.
 * A unit is 1,024 of the one before, a division by a power of two that a float makes exactly;
 * a tenth at most is kept, cut rather than rounded up, so that the size said is never more
 * than the size given.
 */
export function formatBytes(value: number, locale: Locale): string {
  let unit = 0;
  let size = value;
  while (size >= 1024 && unit < BYTE_UNITS.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return numberFormat(locale, {
    style: "unit",
    unit: BYTE_UNITS[unit],
    unitDisplay: "long",
    maximumFractionDigits: 1,
    roundingMode: "trunc",
  }).format(size);
}

/**
 * Format a ratio — a `Decimal` or a `Percent` of the contract, `0.25` for a quarter — as a
 * percentage, with every digit the API gave: `0.125` is « 12,5 % » in French and `12.5%` in
 * English. `Intl` moves the point of the decimal string itself: no float, no product.
 */
export function formatPercent(value: Decimal, locale: Locale): string {
  const exact = decimal(value);
  // The two digits the percentage moves before the point are no longer fraction digits.
  const digits = Math.max(0, fractionDigits(exact) - 2);
  return numberFormat(locale, {
    style: "percent",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
    signDisplay: "negative",
  }).format(exact);
}

/**
 * Format an amount, `Money` of the contract, with its two decimals: `1234.56` is
 * « 1 234,56 » in French and `1,234.56` in English. Given the currency of the installation,
 * which comes from the reference data, the amount carries its symbol: « 1 234,56 € ».
 */
export function formatMoney(value: Money, locale: Locale, currency?: string): string {
  const options: Intl.NumberFormatOptions = {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    signDisplay: "negative",
  };
  const style: Intl.NumberFormatOptions =
    currency === undefined ? {} : { style: "currency", currency };
  return numberFormat(locale, { ...options, ...style }).format(decimal(value, MONEY));
}

/** How a number is written in a language: its decimal separator, and that of its thousands. */
function separators(locale: Locale): { readonly point: string; readonly group: string } {
  const parts = numberFormat(locale, {}).formatToParts("1234.5");
  const part = (type: Intl.NumberFormatPartTypes) =>
    parts.find((candidate) => candidate.type === type)?.value ?? "";
  return { point: part("decimal"), group: part("group") };
}

/**
 * A `Decimal` of the contract as one enters it in a language: its digits as the API gave them,
 * the decimal separator of the language, no separator of thousands — `1234.5` is « 1234,5 » in
 * French, `1234.5` in English.
 */
export function editableDecimal(value: Decimal, locale: Locale): string {
  return decimal(value).replace(".", separators(locale).point);
}

/**
 * A decimal string with its point moved — to the right for `places` above zero —, its digits kept:
 * a hundredth is a matter of where the point stands, never of a product, which a float would round.
 * Leading zeros before the units and trailing zeros after the point go.
 */
function shiftPoint(value: Decimal, places: number): Decimal {
  const exact = decimal(value);
  const negative = exact.startsWith("-");
  const [whole = "", fraction = ""] = (negative ? exact.slice(1) : exact).split(".");
  const digits = whole + fraction;
  const point = whole.length + places;
  const padded =
    point < 1 ? "0".repeat(1 - point) + digits : digits.padEnd(Math.max(point, digits.length), "0");
  const at = Math.max(point, 1);
  const units = padded.slice(0, at).replace(/^0+(?=\d)/, "");
  const decimals = padded.slice(at).replace(/0+$/, "");
  const shifted = decimals === "" ? units : `${units}.${decimals}`;
  return negative && /[1-9]/.test(shifted) ? `-${shifted}` : shifted;
}

/**
 * A `Percent` of the contract — a ratio, `0.035` — as one enters it in a language, a percentage:
 * « 3,5 » in French, `3.5` in English.
 */
export function editablePercent(value: Decimal, locale: Locale): string {
  return editableDecimal(shiftPoint(value, 2), locale);
}

/**
 * The percentage a ratio of the contract stands for — `0.035` read, `3.5` said —, the point moved,
 * never through a float (WF-DAT-0100): a bound the server gives in ratios, said where one enters
 * percentages; `undefined` for a text that is no decimal of the contract.
 */
export function ratioPercent(value: string): Decimal | undefined {
  return isDecimal(value, DECIMAL) ? shiftPoint(value, 2) : undefined;
}

/**
 * The `Percent` of the contract a percentage entered stands for — `3.5` entered, `0.035` sent —, the
 * point moved, never through a float (WF-DAT-0100).
 */
export function percentRatio(entered: Decimal): Decimal {
  return shiftPoint(entered, -2);
}

/**
 * The order of two `Decimal`s of the contract — below zero when the first is the smaller, zero when
 * they are equal, above zero otherwise —, their digits compared as whole numbers once their decimals
 * are made as many, never through a float: `0.3` and `0.30` are equal, `0.1` is below `0.25`.
 */
export function compareDecimals(left: Decimal, right: Decimal): number {
  const [leftWhole = "", leftFraction = ""] = decimal(left).split(".");
  const [rightWhole = "", rightFraction = ""] = decimal(right).split(".");
  const places = Math.max(leftFraction.length, rightFraction.length);
  const difference =
    BigInt(leftWhole + leftFraction.padEnd(places, "0")) -
    BigInt(rightWhole + rightFraction.padEnd(places, "0"));
  return difference < 0n ? -1 : difference > 0n ? 1 : 0;
}

/** A text of a pattern, as a regular expression matches it literally. */
function literal(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * A number entered in a language, as the exact decimal of the contract, never through a float
 * (WF-DAT-0100, WF-INTF-0180): in French, the comma before the decimals and spaces between the
 * thousands — « 1 234,5 » —; in English, the point and commas — `1,234.5` —; both give
 * `1234.5`. An amount keeps two decimals at most (`money`). Anything else — a point in French,
 * a comma that parts no thousands in English, a letter — is not a number of the language:
 * `undefined`.
 */
export function parseDecimal(
  text: string,
  locale: Locale,
  kind: "decimal" | "money" = "decimal",
): Decimal | undefined {
  const { point, group } = separators(locale);
  // A space the keyboard types stands for the narrow one French writes between thousands.
  const typed = /\s/.test(group) ? text.trim().replace(/\s/g, group) : text.trim();
  const written = new RegExp(
    `^-?(\\d+|\\d{1,3}(${literal(group)}\\d{3})+)(${literal(point)}\\d+)?$`,
    "u",
  );
  if (!written.test(typed)) {
    return undefined;
  }
  const exact = typed.replaceAll(group, "").replace(point, ".");
  return kind === "money" && !MONEY.test(exact) ? undefined : exact;
}

/**
 * Whether a text is a `PlanningDate` of the contract: its ISO form, and a day of the calendar.
 * A date that does not exist is refused: 30 February would roll over to 2 March, and 13 months
 * make no date at all.
 */
export function isPlanningDate(value: string): value is PlanningDate {
  if (!DATE.test(value)) {
    return false;
  }
  const midnight = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(midnight.getTime()) && midnight.toISOString().startsWith(value);
}

/**
 * Format a `PlanningDate` as it is: the date of the API, whatever the time zone of the
 * workstation. It is read and written at midnight in UTC, so no zone ever moves it a day.
 */
export function formatPlanningDate(
  value: PlanningDate,
  locale: Locale,
  dateStyle: Intl.DateTimeFormatOptions["dateStyle"] = "medium",
): string {
  if (!isPlanningDate(value)) {
    throw new RangeError(`Not a date of the contract: ${JSON.stringify(value)}`);
  }
  const midnight = new Date(`${value}T00:00:00Z`);
  return dateFormat(locale, { dateStyle, timeZone: TIME_ZONE }).format(midnight);
}

// A month of the contract: `2026-04`, as `WorkloadPlan` and `CashOutMonth` give it.
const MONTH = /^\d{4}-(0[1-9]|1[0-2])$/;

/**
 * Format a month of the contract (`2026-04`) by its name and its year, in the language given: a
 * month has no time zone, and is written as its first day at midnight in UTC.
 */
export function formatMonth(value: string, locale: Locale): string {
  if (!MONTH.test(value)) {
    throw new RangeError(`Not a month of the contract: ${JSON.stringify(value)}`);
  }
  return dateFormat(locale, { month: "long", year: "numeric", timeZone: TIME_ZONE }).format(
    new Date(`${value}-01T00:00:00Z`),
  );
}

/**
 * Format a `Timestamp` in local time: in the time zone of the workstation when none is given,
 * which is why it runs in the browser (`LocalTime`); the server knows only its own zone. The
 * formatter of the workstation's zone is built at each call, never kept (`dateFormat`).
 */
export function formatTimestamp(value: Timestamp, locale: Locale, timeZone?: string): string {
  const options: Intl.DateTimeFormatOptions = { dateStyle: "medium", timeStyle: "short" };
  const format =
    timeZone === undefined
      ? new Intl.DateTimeFormat(formatLocale(locale), options)
      : dateFormat(locale, { ...options, timeZone });
  return format.format(new Date(value));
}

// A time of day of the contract, on 24 hours: `BackupSchedule.at_time`.
const TIME_OF_DAY = /^([01]\d|2[0-3]):[0-5]\d$/;

/** The local time a time of day in universal time stands for, and the day it falls on. */
export interface LocalTimeOfDay {
  /** The time of day in the zone, `HH:MM` on 24 hours, as both languages write it. */
  readonly time: string;
  /** How many days the local date lies from the universal one: -1, 0 or 1. */
  readonly shift: number;
}

/**
 * The time of day of the zone of the workstation — or of the zone named — that a time of day in
 * universal time stands for, on the universal date of a given day: `01:00` UTC is `03:00` in Paris in
 * June, `02:00` in January — a time of day alone has no offset, which only a day gives it, and a
 * change of summer time moves it. The day it falls on matters only where the universal day does — the
 * day of a weekly schedule, which the local day then names. `undefined` for what is no time of day.
 * It runs in the browser, which alone knows its zone; nothing is ever sent from it.
 */
export function localTimeOfDay(
  time: string,
  day: Date,
  timeZone?: string,
): LocalTimeOfDay | undefined {
  if (!TIME_OF_DAY.test(time)) {
    return undefined;
  }
  const date = day.toISOString().slice(0, 10);
  const options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    ...(timeZone === undefined ? {} : { timeZone }),
  };
  const parts = new Intl.DateTimeFormat("en-GB", options).formatToParts(
    new Date(`${date}T${time}:00Z`),
  );
  const part = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((candidate) => candidate.type === type)?.value ?? "";
  const local = Date.UTC(Number(part("year")), Number(part("month")) - 1, Number(part("day")));
  return {
    time: `${part("hour")}:${part("minute")}`,
    shift: Math.round((local - Date.parse(`${date}T00:00:00Z`)) / 86_400_000),
  };
}
