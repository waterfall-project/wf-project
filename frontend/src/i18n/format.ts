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
  return new Intl.NumberFormat(formatLocale(locale), {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
    signDisplay: "negative",
  }).format(exact);
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
  return new Intl.NumberFormat(formatLocale(locale), {
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
  return new Intl.NumberFormat(formatLocale(locale), { ...options, ...style }).format(
    decimal(value, MONEY),
  );
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
  const midnight = new Date(`${value}T00:00:00Z`);
  // A date that does not exist is refused: 30 February would roll over to 2 March, and
  // 13 months make no date at all — toISOString throws.
  if (!DATE.test(value) || !midnight.toISOString().startsWith(value)) {
    throw new RangeError(`Not a date of the contract: ${JSON.stringify(value)}`);
  }
  return new Intl.DateTimeFormat(formatLocale(locale), { dateStyle, timeZone: TIME_ZONE }).format(
    midnight,
  );
}

/**
 * Format a `Timestamp` in local time: in the time zone of the workstation when none is given,
 * which is why it runs in the browser (`LocalTime`); the server knows only its own zone.
 */
export function formatTimestamp(value: Timestamp, locale: Locale, timeZone?: string): string {
  const options: Intl.DateTimeFormatOptions = { dateStyle: "medium", timeStyle: "short" };
  return new Intl.DateTimeFormat(
    formatLocale(locale),
    timeZone === undefined ? options : { ...options, timeZone },
  ).format(new Date(value));
}
