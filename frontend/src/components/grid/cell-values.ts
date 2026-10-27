// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What an entry of a cell reads and shows (WF-IHM-0040): the text it starts from, the value it
 * validates — a number in the format of the language, as the exact decimal of the contract, the
 * identifier of a choice, a duration with its unit, a date of planning —,
 * and what the cell shows of it until the server answers. Never through a float (WF-DAT-0100).
 */
import {
  editableDecimal,
  formatDecimal,
  formatMoney,
  formatPlanningDate,
  parseDecimal,
  parsePlanningDate,
} from "@/i18n/format";
import type { Locale } from "@/i18n/locale";

import type { CellValue, Choice, DurationUnit, EntryKind } from "./columns";
import type { PredecessorsProblem } from "./predecessors-entry";

/**
 * Why an entry is not validated: a cell that may not be emptied left blank, a text too long, no
 * number of the language, an amount with more than two decimals, no duration with a unit, no date,
 * no predecessors (`predecessors-entry.ts`).
 */
export type EntryProblem =
  | "required"
  | "tooLong"
  | "notANumber"
  | "twoDecimals"
  | "notADuration"
  | "notADate"
  | PredecessorsProblem;

/**
 * The suffix WF-PLA-0160 names for each unit of a duration, the same whatever the language of the
 * interface: « m » a month, « min » a minute, « j » a day, « sem » a week, and the same prefixed
 * by « e » for the time elapsed. Every unit of the contract, in its order: one it adds fails the
 * type check here (défaut n° 4).
 */
const REQUIRED_SUFFIXES = {
  min: "min",
  h: "h",
  d: "j",
  w: "sem",
  mo: "m",
  emin: "emin",
  eh: "eh",
  ed: "ej",
  ew: "esem",
  emo: "em",
} as const satisfies Record<DurationUnit, string>;

/** Whether a text is a unit of a duration of the contract. */
function isUnit(text: string): text is DurationUnit {
  return Object.hasOwn(REQUIRED_SUFFIXES, text);
}

/** Every unit of a duration, in the order of the contract. */
const UNITS: readonly DurationUnit[] = Object.keys(REQUIRED_SUFFIXES).filter(isUnit);

/** The unit a number typed without a suffix is read in: the day, as Microsoft Project reads it. */
const DEFAULT_UNIT: DurationUnit = "d";

/** A duration as an entry validates it, the value of the contract and its unit: `2.5 d`. */
function durationValue(value: string, unit: DurationUnit): string {
  return `${value} ${unit}`;
}

/**
 * A duration validated, read back as the contract writes it — its decimal and its unit —; none for a
 * value that is not one.
 */
export function durationOf(
  value: string,
): { readonly value: string; readonly unit: DurationUnit } | undefined {
  const [decimal, unit, ...rest] = value.split(" ");
  return decimal === undefined || unit === undefined || !isUnit(unit) || rest.length > 0
    ? undefined
    : { value: decimal, unit };
}

/** The value of a duration of the contract, as an entry validates it: `10 d`. */
export function durationEntered(
  duration: { readonly value: string; readonly unit: DurationUnit } | null | undefined,
): string | undefined {
  return duration === null || duration === undefined
    ? undefined
    : durationValue(duration.value, duration.unit);
}

/**
 * A duration typed in a language (WF-PLA-0160): a number of the language, never negative, and the
 * suffix of its unit after it, with or without a space, whatever its case — those the requirement
 * names, which hold in every language, and those the catalogue writes in the language of the entry
 * (`suffix`), no other: « 1 m » is a month and « 1 min » a minute in each, « 1 mo » a month in
 * English, but not in French. A number alone is read in days. Anything else is none: `undefined`.
 */
export function parseDuration(
  text: string,
  locale: Locale,
  suffix: (unit: DurationUnit) => string,
): string | undefined {
  const typed = /^(.*?)\s*(\p{L}*)$/u.exec(text.trim());
  const number = typed?.[1] ?? "";
  const written = (typed?.[2] ?? "").toLocaleLowerCase(locale);
  const units = new Map<string, DurationUnit>();
  for (const unit of UNITS) {
    units.set(REQUIRED_SUFFIXES[unit], unit);
    units.set(suffix(unit).toLocaleLowerCase(locale), unit);
  }
  const unit = written === "" ? DEFAULT_UNIT : units.get(written);
  const value = parseDecimal(number, locale);
  return unit === undefined || value === undefined || value.startsWith("-")
    ? undefined
    : durationValue(value, unit);
}

/**
 * The value an entry validates, as the contract writes it — a text as typed, a number as the
 * exact decimal of the contract, the identifier chosen, a duration and its unit, a date in its ISO
 * form, `null` for a cell emptied —, or why it is not.
 */
export function parsedEntry(kind: EntryKind, text: string, locale: Locale): Parsed {
  if (kind.type === "text") {
    if (text.trim() === "") {
      return kind.nullable === true ? { value: null } : { problem: "required" };
    }
    return kind.maxLength !== undefined && text.length > kind.maxLength
      ? { problem: "tooLong" }
      : { value: text };
  }
  if (kind.type === "choice") {
    if (text === "") {
      return kind.nullable ? { value: null } : { problem: "required" };
    }
    return { value: text };
  }
  return parsedTyped(kind, text, locale);
}

/** What an entry of a number, a duration, a date or the links of a task validates, or why not. */
function parsedTyped(
  kind: Exclude<EntryKind, { readonly type: "text" | "choice" }>,
  text: string,
  locale: Locale,
): Parsed {
  if (kind.type === "predecessors") {
    // A blank text empties the predecessors: no link is a value like any other.
    return kind.parse(text, locale);
  }
  if (text.trim() === "") {
    return "nullable" in kind && kind.nullable ? { value: null } : { problem: "required" };
  }
  return kind.type === "duration" || kind.type === "date"
    ? parsedTime(kind, text, locale)
    : parsedNumber(kind.type, text, locale);
}

/**
 * What an entry validates, or why it does not; or the row numbers to ask the server first, which
 * the rows of the grid do not name (`EntryKind.ask`).
 */
type Parsed =
  | { readonly value: string | null }
  | { readonly problem: EntryProblem }
  | { readonly unresolved: readonly number[] };

/** A duration or a date typed, not blank, as the contract writes it, or why it is not one. */
function parsedTime(
  kind: Extract<EntryKind, { readonly type: "duration" | "date" }>,
  text: string,
  locale: Locale,
): Parsed {
  if (kind.type === "duration") {
    const value = parseDuration(text, locale, kind.suffix);
    return value === undefined ? { problem: "notADuration" } : { value };
  }
  const value = parsePlanningDate(text, locale);
  return value === undefined ? { problem: "notADate" } : { value };
}

/** A number typed, not blank, as the exact decimal of the contract, or why it is not one. */
function parsedNumber(type: "decimal" | "money" | "integer", text: string, locale: Locale): Parsed {
  if (type === "integer") {
    // Digits alone, as the contract takes a whole number: no sign, no separator, no fraction.
    // Nine digits at most keep the number exact.
    return /^\d{1,9}$/.test(text.trim())
      ? { value: text.trim().replace(/^0+(?=\d)/, "") }
      : { problem: "notANumber" };
  }
  const value = parseDecimal(text, locale, type);
  if (value !== undefined) {
    return { value };
  }
  // A number of the language all the same, but with more decimals than an amount keeps.
  return parseDecimal(text, locale) === undefined
    ? { problem: "notANumber" }
    : { problem: "twoDecimals" };
}

/** A duration validated as the cell writes it: its value formatted, and the suffix of its unit. */
function writtenDuration(
  kind: Extract<EntryKind, { readonly type: "duration" }>,
  value: string,
  locale: Locale,
): string {
  const duration = durationOf(value);
  return duration === undefined
    ? ""
    : kind.written(formatDecimal(duration.value, locale), duration.unit);
}

/** What a cell shows of a value validated, until the server answers. */
export function shownEntry(kind: EntryKind, value: string | null, locale: Locale): string {
  if (value === null) {
    return "";
  }
  switch (kind.type) {
    case "decimal":
    case "integer":
      return formatDecimal(value, locale);
    case "money":
      return formatMoney(value, locale);
    case "choice":
      return kind.choices().find((choice) => choice.id === value)?.label ?? "";
    case "duration":
      return writtenDuration(kind, value, locale);
    case "date":
      return formatPlanningDate(value, locale, "short");
    case "text":
      return value;
    case "predecessors":
      return kind.text(value, locale);
  }
}

/**
 * The first choice that may be chosen whose name starts with what was typed, whatever its case
 * and its accents, in the order of the list.
 */
export function firstChoice(
  choices: readonly Choice[],
  typed: string,
  locale: Locale,
): Choice | undefined {
  const collator = new Intl.Collator(locale, { sensitivity: "base" });
  return choices.find(
    (choice) => choice.active && collator.compare(choice.label.slice(0, typed.length), typed) === 0,
  );
}

/**
 * The text an entry starts from: the character typed, or the value of the cell as one types it —
 * a number with the decimal separator of the language, a duration with the suffix of its unit, a
 * date in the short form of the language. A list starts from the choice made, or from the first
 * whose name starts with the character typed.
 */
export function startingText(
  kind: EntryKind,
  value: CellValue,
  typed: string | undefined,
  locale: Locale,
): string {
  if (typed !== undefined && kind.type === "choice") {
    return firstChoice(kind.choices(), typed, locale)?.id ?? value ?? "";
  }
  if (typed !== undefined) {
    return typed;
  }
  if (value === null || value === undefined) {
    return "";
  }
  switch (kind.type) {
    case "decimal":
    case "money":
      return editableDecimal(value, locale);
    case "duration":
      return writtenDuration(kind, value, locale);
    case "date":
      return formatPlanningDate(value, locale, "short");
    case "predecessors":
      return kind.text(value, locale);
    default:
      return value;
  }
}
